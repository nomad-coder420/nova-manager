from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import HTTPException

from nova_manager.core.log import logger
from nova_manager.components.experiences.models import ExperienceVariants, Experiences
from nova_manager.components.user_experience.schemas import (
    ExperienceFeatureAssignment,
    UserExperienceAssignment,
)
from nova_manager.components.users.models import Users
from sqlalchemy.ext.asyncio import AsyncSession

from nova_manager.components.personalisations.models import (
    PersonalisationExperienceVariants,
)

from nova_manager.components.users.crud_async import UsersAsyncCRUD
from nova_manager.components.experiences.crud_async import ExperiencesAsyncCRUD
from nova_manager.components.user_experience.crud_async import (
    UserExperienceAsyncCRUD,
)

from nova_manager.components.rule_evaluator.controller import RuleEvaluator


class GetUserExperienceVariantFlowAsync:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rule_evaluator = RuleEvaluator()
        self.users_crud = UsersAsyncCRUD(db)
        self.experiences_crud = ExperiencesAsyncCRUD(db)
        self.user_experience_personalisation_crud = UserExperienceAsyncCRUD(db)

        # Cache fields
        self.experience_personalisation_map: Dict[UUID, UserExperienceAssignment] = {}
        self.segment_results_map = {}

    async def get_user_experience_variant(
        self,
        user_id: str,
        experience_name: str,
        organisation_id: str,
        app_id: str,
        payload: Dict[str, Any],
    ) -> UserExperienceAssignment:
        results = await self.get_user_experience_variants(
            user_id=user_id,
            organisation_id=organisation_id,
            app_id=app_id,
            payload=payload,
            experience_names=[experience_name],
        )

        if experience_name in results:
            return results[experience_name]
        else:
            raise HTTPException(
                status_code=404, detail=f"Experience '{experience_name}' not found"
            )

    async def get_user_experience_variants(
        self,
        user_id: str,
        organisation_id: str,
        app_id: str,
        payload: Dict[str, Any],
        experience_names: Optional[List[str]] = None,
    ) -> Dict[str, UserExperienceAssignment]:
        # Step 1: Check if user exists, if yes update user payload, if no create user
        user = await self._update_or_create_user(
            user_id, organisation_id, app_id, payload
        )

        if not user:
            raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

        # Step 2: Fetch experiences with personalisations and related data in single query
        experiences = await self.experiences_crud.get_experiences_by_names(
            organisation_id, app_id, experience_names
        )

        experience_ids = [experience.pid for experience in experiences]

        # Step 3: Load existing user experience personalisation cache
        await self._load_experience_personalisation_cache(
            user=user,
            organisation_id=organisation_id,
            app_id=app_id,
            experience_ids=experience_ids,
        )

        # Process each experience
        results = {}

        # Collect user experience personalisation assignments for bulk upsert
        new_assignments: List[UserExperienceAssignment] = []

        for experience in experiences:
            experience_id = experience.pid
            experience_name = experience.name

            # Determine if we have a cached assignment
            cache_hit = experience_id in self.experience_personalisation_map
            user_experience = (
                self.experience_personalisation_map.get(experience_id)
                if cache_hit
                else None
            )

            experience_variant_assignment = None

            personalisations = experience.personalisations

            if not personalisations:
                if cache_hit:
                    experience_variant_assignment = user_experience
                else:
                    features = self._get_experience_default_features(experience)

                    experience_variant_assignment = UserExperienceAssignment(
                        experience_id=experience_id,
                        personalisation_id=None,
                        personalisation_name=None,
                        experience_variant_id=None,
                        features=features,
                        evaluation_reason="default_experience",
                    )

                results[experience_name] = experience_variant_assignment

                # Only add to new_assignments if this is a new assignment (not from cache)
                if not (cache_hit and experience_variant_assignment is user_experience):
                    new_assignments.append(experience_variant_assignment)

                # Always update the in-memory cache
                self.experience_personalisation_map[experience_id] = (
                    experience_variant_assignment
                )
                continue

            # Flag to track if we found an applicable personalisation
            found_applicable = False

            # Check if the cached user experience is from an active personalisation
            if cache_hit:
                for personalisation in personalisations:
                    if personalisation.pid == user_experience.personalisation_id:
                        if not personalisation.is_active:
                            cache_hit = False  # Invalidate cache hit
                            user_experience = None
                        break

            for personalisation in personalisations:
                # skip disabled personalisations
                if not getattr(personalisation, "is_active", True):
                    logger.info(
                        f"Skipping disabled personalisation {personalisation.pid} for experience {experience_id}"
                    )
                    continue

                # Early gating: if we have a cache hit and personalisation doesn't have reassign=True, skip evaluation
                if cache_hit and not getattr(personalisation, "reassign", False):
                    continue

                if cache_hit:
                    user_experience = self.experience_personalisation_map.get(
                        experience_id
                    )
                    user_experience_assignment_time = (
                        user_experience.assigned_at if user_experience else None
                    )
                    personalisation_modified_time = getattr(
                        personalisation, "modified_at", None
                    )
                    # If the cached assignment is newer than the personalisation's last modification,skip reassignment to avoid unnecessary updates.
                    if (
                        user_experience_assignment_time
                        and personalisation_modified_time
                        and user_experience.personalisation_id == personalisation.pid
                    ):
                        if (
                            user_experience_assignment_time
                            > personalisation_modified_time
                        ):
                            # The cached user experience is newer
                            continue

                rollout_percentage = personalisation.rollout_percentage

                context_id = f"{experience_id}:{personalisation.pid}"
                if not self.rule_evaluator.evaluate_target_percentage(
                    str(user.pid), rollout_percentage, context_id
                ):
                    continue

                rule_config = personalisation.rule_config

                if not self.rule_evaluator.evaluate_rule(
                    rule_config, user.user_profile
                ):
                    continue

                experience_variants = personalisation.experience_variants

                # Select experience variant based on target percentage
                selected_experience_variant = (
                    self._select_experience_variant_by_target_percentage(
                        user=user,
                        experience_id=experience_id,
                        personalisation_id=personalisation.pid,
                        experience_variants=experience_variants,
                    )
                )

                # If no variant found, skip this personalisation
                if not selected_experience_variant:
                    continue

                selected_experience_variant_features_map = {
                    feature_variant.experience_feature_id: feature_variant
                    for feature_variant in selected_experience_variant.feature_variants
                }
                experience_features = experience.features

                experience_feature_variants = {}

                for feature in experience_features:
                    experience_feature_id = feature.pid
                    feature_flag = feature.feature_flag

                    feature_id = feature_flag.pid
                    feature_name = feature_flag.name

                    feature_variant = selected_experience_variant_features_map.get(
                        experience_feature_id
                    )

                    if feature_variant:
                        experience_feature_variants[feature_name] = (
                            ExperienceFeatureAssignment(
                                feature_id=str(feature_id),
                                feature_name=feature_name,
                                variant_id=str(feature_variant.pid),
                                variant_name=feature_variant.name,
                                config=feature_variant.config,
                            )
                        )
                    else:
                        experience_feature_variants[feature_name] = (
                            ExperienceFeatureAssignment(
                                feature_id=str(feature_id),
                                feature_name=feature_name,
                                variant_id=None,
                                variant_name="default",
                                config=feature_flag.default_variant,
                            )
                        )

                experience_variant_assignment = UserExperienceAssignment(
                    experience_id=experience_id,
                    personalisation_id=personalisation.pid,
                    personalisation_name=personalisation.name,
                    experience_variant_id=selected_experience_variant.pid,
                    features=experience_feature_variants,
                    evaluation_reason="personalisation_match",
                )

                # Apply the assignment based on reassign flag and cache status
                if personalisation.reassign or not cache_hit:
                    found_applicable = True
                    break
                else:
                    # Continue to next personalisation to look for one with reassign=True
                    continue

            # After evaluating all personalisations
            if not found_applicable:
                if cache_hit:
                    # Use the cached assignment
                    experience_variant_assignment = user_experience
                else:
                    # Fall back to default
                    features = self._get_experience_default_features(experience)

                    experience_variant_assignment = UserExperienceAssignment(
                        experience_id=experience_id,
                        personalisation_id=None,
                        personalisation_name=None,
                        experience_variant_id=None,
                        features=features,
                        evaluation_reason="no_experience_assignment_error",
                    )

            # Add to results
            results[experience_name] = experience_variant_assignment

            # Only add to new_assignments if this is a new assignment (not from cache)
            if not (cache_hit and experience_variant_assignment is user_experience):
                new_assignments.append(experience_variant_assignment)

            # Always update the in-memory cache
            self.experience_personalisation_map[experience_id] = (
                experience_variant_assignment
            )

        # TODO: Add this in task in queue
        # Bulk upsert user experience personalisation assignments
        if new_assignments:
            try:
                await self.user_experience_personalisation_crud.bulk_create_user_experience_personalisations(
                    user_id=user.pid,
                    organisation_id=organisation_id,
                    app_id=app_id,
                    personalisation_assignments=new_assignments,
                )
            except Exception as e:
                logger.error(
                    f"Error bulk creating user experience personalisations: {e}"
                )

        return results

    async def _update_or_create_user(
        self, user_id: str, organisation_id: str, app_id: str, payload: Dict[str, Any]
    ):
        existing_user = await self.users_crud.get_by_pid(
            pid=user_id, organisation_id=organisation_id, app_id=app_id
        )

        if existing_user:
            # User exists, update user profile with new payload
            user = await self.users_crud.update_user_profile(existing_user, payload)
        else:
            # User doesn't exist, create new user with user profile
            # user = await self.users_crud.create_user(
            #     user_id, organisation_id, app_id, payload
            # )
            raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

        return user

    def _select_experience_variant_by_target_percentage(
        self,
        user: Users,
        experience_id: UUID,
        personalisation_id: UUID,
        experience_variants: List[PersonalisationExperienceVariants],
    ) -> ExperienceVariants | None:
        """
        Select an experience variant based on target percentage evaluation.

        Args:
            user: User object
            experience_id: Experience ID for context
            personalisation_id: Personalisation ID for context
            experience_variants: List of PersonalisationExperienceVariants

        Returns:
            Selected ExperienceVariant or None if no match found
        """
        if not experience_variants:
            return None

        # Find the first experience variant that matches target percentage
        for experience_variant in experience_variants:
            target_percentage = experience_variant.target_percentage

            # Validate target percentage
            if target_percentage < 0 or target_percentage > 100:
                continue  # Skip invalid percentages

            # Create context ID for consistent hashing
            context_id = f"{experience_id}:{personalisation_id}:{experience_variant.experience_variant_id}"

            # Check if user falls within this variant's target percentage
            if self.rule_evaluator.evaluate_target_percentage(
                str(user.pid), target_percentage, context_id
            ):
                return experience_variant.experience_variant

        return experience_variants[0].experience_variant

    async def _load_experience_personalisation_cache(
        self,
        user: Users,
        organisation_id: str,
        app_id: str,
        experience_ids: List[UUID] | None = None,
    ):
        # Load existing assignments from DB (single query with relationships)
        existing_assignments = await self.user_experience_personalisation_crud.get_user_experiences_personalisations(
            user_id=user.pid,
            organisation_id=organisation_id,
            app_id=app_id,
            experience_ids=experience_ids,
        )

        # Define evaluation reasons that should be invalidated when personalisations are re-enabled
        # These are the reasons assigned when no personalisation match was found
        invalid_evaluation_reasons = [
            "default_experience",
            "no_personalisation_match_error",
            "no_experience_assignment_error",
        ]

        # Populate cache (single loop)
        for assignment in existing_assignments:
            # Skip cache entries with invalidation reasons - these should be re-evaluated
            # when personalisations are re-enabled
            if assignment.evaluation_reason in invalid_evaluation_reasons:
                continue

            cache_data = UserExperienceAssignment(
                experience_id=assignment.experience_id,
                personalisation_id=assignment.personalisation_id,
                personalisation_name=assignment.personalisation_name,
                experience_variant_id=assignment.experience_variant_id,
                features=assignment.features,
                evaluation_reason=assignment.evaluation_reason,
                assigned_at=assignment.assigned_at,  # Include the assigned_at timestamp
            )
            self.experience_personalisation_map[assignment.experience_id] = cache_data

    def _get_experience_default_features(
        self, experience: Experiences
    ) -> Dict[str, Any]:
        default_features = {}

        for feature in experience.features:
            feature_flag = feature.feature_flag

            default_features[feature_flag.name] = ExperienceFeatureAssignment(
                feature_id=str(feature.pid),
                feature_name=feature_flag.name,
                variant_id=None,
                variant_name="default",
                config=feature_flag.default_variant,
            )

        return default_features
