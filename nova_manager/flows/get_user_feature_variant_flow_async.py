import asyncio
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from fastapi import HTTPException
from nova_manager.components.experiences.models import (
    ExperienceSegmentPersonalisations,
    ExperienceSegments,
    Personalisations,
)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from nova_manager.components.users.models import Users
from nova_manager.components.segments.models import Segments
from nova_manager.components.feature_flags.models import FeatureFlags

from nova_manager.components.users.crud_async import UsersAsyncCRUD
from nova_manager.components.feature_flags.crud_async import FeatureFlagsAsyncCRUD
from nova_manager.components.user_experience.crud_async import (
    UserExperiencePersonalisationAsyncCRUD,
    PersonalisationAssignment,
)

from nova_manager.components.rule_evaluator.controller import RuleEvaluator


class ObjectVariantAssignment(BaseModel):
    feature_id: UUID | None
    feature_name: str
    variant_id: UUID | None
    variant_name: str
    variant_config: Dict[str, Any]
    experience_id: UUID | None
    experience_name: str | None
    personalisation_id: UUID | None
    personalisation_name: str | None
    segment_id: UUID | None
    segment_name: str | None
    evaluation_reason: str


class ExperiencePersonalisationCache:
    """Cache data structure for experience segment personalisation"""

    def __init__(
        self,
        personalisation: Personalisations | None,
        segment_id: UUID | None,
        segment_name: str | None,
        experience_segment_id: UUID | None,
        experience_segment_personalisation_id: UUID | None,
    ):
        self.personalisation = personalisation
        self.segment_id = segment_id
        self.segment_name = segment_name
        self.experience_segment_id = experience_segment_id
        self.experience_segment_personalisation_id = (
            experience_segment_personalisation_id
        )


class GetUserFeatureVariantFlowAsync:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rule_evaluator = RuleEvaluator()
        self.users_crud = UsersAsyncCRUD(db)
        self.feature_flags_crud = FeatureFlagsAsyncCRUD(db)
        self.user_experience_personalisation_crud = (
            UserExperiencePersonalisationAsyncCRUD(db)
        )

        # Cache fields
        self.experience_personalisation_map: Dict[
            UUID, ExperiencePersonalisationCache
        ] = {}
        self.segment_results_map = {}

    async def get_variants_for_objects(
        self,
        user_id: str,
        organisation_id: str,
        app_id: str,
        payload: Dict[str, Any],
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, ObjectVariantAssignment]:
        # Step 1: Check if user exists, if yes update user payload, if no create user
        user = await self._update_or_create_user(
            user_id, organisation_id, app_id, payload
        )

        if not user:
            raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

        # Step 2: Fetch features with experiences and related data in single query
        features = await self.feature_flags_crud.get_flags_with_full_experience_data(
            organisation_id, app_id, feature_names
        )

        feature_name_map = {feature.name: feature for feature in features}

        # Step 3: Load existing user experience personalisation cache
        await self._load_experience_personalisation_cache(
            user=user,
            organisation_id=organisation_id,
            app_id=app_id,
            features=features,
        )

        # Process each feature
        results = {}

        # Collect user experience personalisation assignments for bulk upsert
        personalisation_assignments: List[PersonalisationAssignment] = []

        for feature_name in feature_name_map:
            feature = feature_name_map.get(feature_name)

            if not feature:
                unknown_assignment = ObjectVariantAssignment(
                    feature_id=None,
                    feature_name="unknown_feature",
                    variant_id=None,
                    variant_name="default",
                    variant_config={},
                    experience_id=None,
                    experience_name=None,
                    personalisation_id=None,
                    personalisation_name=None,
                    segment_id=None,
                    segment_name=None,
                    evaluation_reason="unknown_feature",
                )
                results[feature_name] = unknown_assignment
                continue

            if feature.name in results:
                continue

            feature_variant = None

            if feature.experience_id and feature.experience:
                experience_id = feature.experience_id
                experience_name = feature.experience.name
                experience_segments = feature.experience.experience_segments

                cache_data, from_cache = self._get_experience_segment_personalisation(
                    user, experience_id, experience_segments
                )

                selected_personalisation = cache_data.personalisation
                segment_id = cache_data.segment_id
                segment_name = cache_data.segment_name
                experience_segment_id = cache_data.experience_segment_id
                experience_segment_personalisation_id = (
                    cache_data.experience_segment_personalisation_id
                )

                if selected_personalisation and segment_id:
                    evaluation_reason = "segment_match_personalisation"

                    if not from_cache:
                        personalisation_assignments.append(
                            PersonalisationAssignment(
                                experience_id=experience_id,
                                personalisation_id=selected_personalisation.pid,
                                segment_id=segment_id,
                                segment_name=segment_name,
                                experience_segment_id=experience_segment_id,
                                experience_segment_personalisation_id=experience_segment_personalisation_id,
                                evaluation_reason=evaluation_reason,
                            )
                        )

                    for pfv in selected_personalisation.feature_variants:
                        pfv_feature_flag = pfv.feature_variant.feature_flag

                        pfv_feature_id = pfv_feature_flag.pid
                        pfv_feature_name = pfv_feature_flag.name

                        pfv_feature_variant = ObjectVariantAssignment(
                            feature_id=pfv.feature_variant.feature_id,
                            feature_name=pfv_feature_name,
                            variant_id=pfv.feature_variant.pid,
                            variant_name=pfv.feature_variant.name,
                            variant_config=pfv.feature_variant.config,
                            experience_id=experience_id,
                            experience_name=experience_name,
                            personalisation_id=selected_personalisation.pid,
                            personalisation_name=selected_personalisation.name,
                            segment_id=segment_id,
                            segment_name=segment_name,
                            evaluation_reason=f"{evaluation_reason}{'_cache' if from_cache else ''}",
                        )

                        results[pfv_feature_name] = pfv_feature_variant

                        if pfv_feature_id == feature.pid:
                            feature_variant = pfv_feature_variant

                elif not segment_id:
                    evaluation_reason = "no_segment_match"

                    if not from_cache:
                        personalisation_assignments.append(
                            PersonalisationAssignment(
                                experience_id=experience_id,
                                personalisation_id=None,
                                segment_id=None,
                                segment_name=None,
                                experience_segment_id=None,
                                experience_segment_personalisation_id=None,
                                evaluation_reason=evaluation_reason,
                            )
                        )

                    feature_variant = self._find_default_variant(
                        feature,
                        f"{evaluation_reason}{'_cache' if from_cache else ''}",
                        experience_id=experience_id,
                        experience_name=experience_name,
                    )

                elif not selected_personalisation:
                    feature_variant = self._find_default_variant(
                        feature,
                        "no_valid_assignment_error",
                        experience_id=experience_id,
                        experience_name=experience_name,
                    )

            else:
                # No experience, return default variant
                feature_variant = self._find_default_variant(
                    feature, "no_experience_defined"
                )

            if not feature_variant:
                feature_variant = ObjectVariantAssignment(
                    feature_id=feature.pid,
                    feature_name=feature.name,
                    variant_id=None,  # No specific variant
                    variant_name="default",
                    variant_config=feature.default_variant,
                    experience_id=None,
                    experience_name=None,
                    personalisation_id=None,
                    personalisation_name=None,
                    segment_id=None,
                    segment_name=None,
                    evaluation_reason="no_variant_assigned_error",
                )

            results[feature.name] = feature_variant

        # Bulk upsert user experience personalisation assignments
        if personalisation_assignments:
            await self.user_experience_personalisation_crud.bulk_create_user_experience_personalisations(
                user_id=user.pid,
                organisation_id=organisation_id,
                app_id=app_id,
                personalisation_assignments=personalisation_assignments,
            )

        return results

    async def _update_or_create_user(
        self, user_id: str, organisation_id: str, app_id: str, payload: Dict[str, Any]
    ):
        existing_user = await self.users_crud.get_by_user_id(
            user_id=user_id, organisation_id=organisation_id, app_id=app_id
        )

        if existing_user:
            # User exists, update user profile with new payload
            user = await self.users_crud.update_user_profile(existing_user, payload)
        else:
            # User doesn't exist, create new user with user profile
            user = await self.users_crud.create_user(
                user_id, organisation_id, app_id, payload
            )

        return user

    def _find_default_variant(
        self,
        feature: FeatureFlags,
        reason: str,
        experience_id: UUID | None = None,
        experience_name: str | None = None,
    ) -> ObjectVariantAssignment:
        """
        Find the default variant for a feature flag.
        Looks for a variant named 'default' in the feature's variants.
        """
        # Look for variant named 'default'
        for variant in feature.variants:
            if variant.name.lower() == "default":
                return ObjectVariantAssignment(
                    feature_id=feature.pid,
                    feature_name=feature.name,
                    variant_id=variant.pid,
                    variant_name=variant.name,
                    variant_config=variant.config,
                    experience_id=experience_id,
                    experience_name=experience_name,
                    personalisation_id=None,
                    personalisation_name=None,
                    segment_id=None,
                    segment_name=None,
                    evaluation_reason=reason,
                )

        return ObjectVariantAssignment(
            feature_id=feature.pid,
            feature_name=feature.name,
            variant_id=None,
            variant_name="default",
            variant_config=feature.default_variant,
            experience_id=experience_id,
            experience_name=experience_name,
            personalisation_id=None,
            personalisation_name=None,
            segment_id=None,
            segment_name=None,
            evaluation_reason=f"{reason}_no_default_error",
        )

    async def _load_experience_personalisation_cache(
        self,
        user: Users,
        organisation_id: str,
        app_id: str,
        features: List[FeatureFlags],
    ):
        # Extract unique experience IDs from features (single pass)
        experience_ids = list(
            {
                feature.experience_id
                for feature in features
                if feature.experience_id is not None
            }
        )

        if experience_ids:
            # Load existing assignments from DB (single query with relationships)
            existing_assignments = await self.user_experience_personalisation_crud.get_user_experiences_personalisations(
                user_id=user.pid,
                organisation_id=organisation_id,
                app_id=app_id,
                experience_ids=experience_ids,
            )

            # Populate cache (single loop)
            for assignment in existing_assignments:
                cache_data = ExperiencePersonalisationCache(
                    personalisation=assignment.personalisation,
                    segment_id=assignment.segment_id,
                    segment_name=assignment.segment_name,
                    experience_segment_id=assignment.experience_segment_id,
                    experience_segment_personalisation_id=assignment.experience_segment_personalisation_id,
                )
                self.experience_personalisation_map[assignment.experience_id] = (
                    cache_data
                )

    def _get_experience_segment_personalisation(
        self,
        user: Users,
        experience_id: UUID,
        experience_segments: List[ExperienceSegments],
    ) -> Tuple[ExperiencePersonalisationCache, bool]:
        if experience_id in self.experience_personalisation_map:
            cached_data = self.experience_personalisation_map[experience_id]
            return cached_data, True

        else:
            experience_segment = self._evaluate_experience_segments(
                user, experience_id, experience_segments
            )

            if experience_segment:
                segment = experience_segment.segment

                selected_segment_personalisation = (
                    self._evaluate_segment_personalisations(
                        user,
                        experience_id,
                        segment,
                        experience_segment.personalisations,
                    )
                )

                if selected_segment_personalisation:
                    personalisation = selected_segment_personalisation.personalisation

                    cache_data = ExperiencePersonalisationCache(
                        personalisation=personalisation,
                        segment_id=segment.pid,
                        segment_name=segment.name,
                        experience_segment_id=experience_segment.pid,
                        experience_segment_personalisation_id=selected_segment_personalisation.pid,
                    )
                    self.experience_personalisation_map[experience_id] = cache_data

                    return cache_data, False

        null_assignment = ExperiencePersonalisationCache(
            personalisation=None,
            segment_id=None,
            segment_name=None,
            experience_segment_id=None,
            experience_segment_personalisation_id=None,
        )

        return null_assignment, False

    def _evaluate_experience_segments(
        self,
        user: Users,
        experience_id: UUID,
        experience_segments: List[ExperienceSegments],
    ) -> ExperienceSegments | None:
        if experience_segments:
            experience_segments.sort(key=lambda x: x.priority)

            for experience_segment in experience_segments:
                segment = experience_segment.segment

                if segment.pid in self.segment_results_map:
                    segment_result = self.segment_results_map[segment.pid]
                else:
                    segment_result = self.rule_evaluator.evaluate_rule(
                        segment.rule_config, user.user_profile
                    )

                    self.segment_results_map[segment.pid] = segment_result

                if segment_result:
                    # User matches the segment rule, now check target percentage
                    context_id = f"{experience_id}:{segment.pid}"

                    segment_target_result = (
                        self.rule_evaluator.evaluate_target_percentage(
                            str(user.pid),
                            experience_segment.target_percentage,
                            context_id,
                        )
                    )

                    # Check if user falls within this experience segment's target percentage
                    if segment_target_result:
                        return experience_segment

        return None

    def _evaluate_segment_personalisations(
        self,
        user: Users,
        experience_id: UUID,
        segment: Segments,
        segment_personalisations: List[ExperienceSegmentPersonalisations],
    ) -> ExperienceSegmentPersonalisations | None:
        # Evaluate each personalisation's target percentage
        for segment_personalisation in segment_personalisations:
            context_id = f"{experience_id}:{segment.pid}:{segment_personalisation.personalisation_id}"

            # Check if user falls within this personalisation's target percentage
            if self.rule_evaluator.evaluate_target_percentage(
                str(user.pid), segment_personalisation.target_percentage, context_id
            ):
                # If we found a matching personalisation, stop looking for more personalisations
                return segment_personalisation

        # No matching personalisation found. Error!
        return None

    async def get_user_feature_variant(
        self,
        user_id: str,
        feature_name: str,
        organisation_id: str,
        app_id: str,
        payload: Dict[str, Any],
    ) -> ObjectVariantAssignment:
        results = await self.get_variants_for_objects(
            user_id=user_id,
            organisation_id=organisation_id,
            app_id=app_id,
            payload=payload,
            feature_names=[feature_name],
        )

        if feature_name in results:
            return results[feature_name]
        else:
            raise HTTPException(
                status_code=404, detail=f"Feature '{feature_name}' not found"
            )
