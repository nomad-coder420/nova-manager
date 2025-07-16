from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from nova_manager.components.feature_flags.crud import (
    FeatureFlagsCRUD,
    FeatureVariantsCRUD,
)
from nova_manager.components.experiences.crud import ExperiencesCRUD
from nova_manager.components.segments.crud import SegmentsCRUD
from nova_manager.components.rule_evaluator.controller import RuleEvaluator
from nova_manager.components.users.crud import UsersCRUD
from nova_manager.components.user_experience.crud import UserFeatureVariantsCRUD


class ObjectVariantAssignment(BaseModel):
    feature_id: UUID
    feature_name: str
    variant_name: str
    variant_config: Dict[str, Any]
    experience_id: Optional[UUID] = None
    experience_name: Optional[str] = None
    evaluation_reason: str  # "cached_valid", "experience_evaluation", "default"


class GetUserFeatureVariantFlow:
    def __init__(self, db: Session):
        self.db = db
        self.rule_evaluator = RuleEvaluator()
        self.users_crud = UsersCRUD(db)
        self.feature_flags_crud = FeatureFlagsCRUD(db)
        self.user_feature_variants_crud = UserFeatureVariantsCRUD(db)
        self.feature_variants_crud = FeatureVariantsCRUD(db)
        self.experiences_crud = ExperiencesCRUD(db)
        self.segments_crud = SegmentsCRUD(db)

    def get_variants_for_objects(
        self,
        user_id: str,
        organisation_id: str,
        app_id: str,
        payload: Dict[str, Any],
        feature_names: Optional[List[str]] = None,
    ) -> List[ObjectVariantAssignment]:
        """
        Get variants for specified objects or all objects for a user.

        Logic:
        1. Check in UserFeatureVariants for valid entries (variant assigned > experience last updated)
        2. If entry found, return that
        3. Check for experiences for those objects and evaluate them (evaluate using segments)
        4. Find correct variants for objects & user experiences and update in db and return
        """

        # Get or create user
        user = self._get_or_create_user(user_id, organisation_id, app_id, payload)

        # Get feature flags (objects) to evaluate
        if feature_names:
            feature_flags = []
            for feature_name in feature_names:
                try:
                    feature_flag = self.feature_flags_crud.get_by_name(feature_name, organisation_id, app_id)
                    if feature_flag:
                        feature_flags.append(feature_flag)
                except ValueError:
                    continue
        else:
            # Get all active feature flags for the org/app
            feature_flags = self.feature_flags_crud.get_active_flags(
                organisation_id=organisation_id, app_id=app_id
            )

        if not feature_flags:
            return []

        feature_pids = [flag.pid for flag in feature_flags]

        # Step 1: Check existing UserFeatureVariants for valid entries
        existing_assignments = (
            self.user_feature_variants_crud.get_user_assignments_for_objects(
                user_pid=user.pid, feature_pids=feature_pids
            )
        )

        # Group assignments by feature_id for easy lookup
        assignments_by_feature = {
            assignment.feature_id: assignment for assignment in existing_assignments
        }

        results = []
        features_to_evaluate = []

        for feature_flag in feature_flags:
            assignment = assignments_by_feature.get(feature_flag.pid)

            if assignment:
                # Check if assignment is valid (assigned after experience last updated)
                if assignment.experience_id:
                    experience = self.experiences_crud.get_by_pid(
                        assignment.experience_id
                    )
                    if experience and self.user_feature_variants_crud.is_variant_valid(
                        assignment, experience.last_updated_at
                    ):
                        # Valid cached assignment
                        results.append(
                            ObjectVariantAssignment(
                                feature_id=feature_flag.pid,
                                feature_name=feature_flag.name,
                                variant_name=assignment.variant_name,
                                variant_config=assignment.variant_config,
                                experience_id=assignment.experience_id,
                                experience_name=experience.name,
                                evaluation_reason="cached_valid",
                            )
                        )
                        continue
                else:
                    # No experience associated, keep the assignment
                    results.append(
                        ObjectVariantAssignment(
                            feature_id=feature_flag.pid,
                            feature_name=feature_flag.name,
                            variant_name="default",
                            variant_config=feature_flag.default_variant,
                            experience_id=None,
                            experience_name=None,
                            evaluation_reason="cached_valid",
                        )
                    )
                    continue

            # Need to evaluate this feature
            features_to_evaluate.append(feature_flag)

        # Step 2: Evaluate experiences for remaining features
        for feature_flag in features_to_evaluate:
            variant_assignment = self._evaluate_feature_experiences(
                feature_flag, user, payload, organisation_id, app_id
            )
            results.append(variant_assignment)

        return results

    def _evaluate_feature_experiences(
        self,
        feature_flag,
        user,
        payload: Dict[str, Any],
        organisation_id: str,
        app_id: str,
    ) -> ObjectVariantAssignment:
        """Evaluate experiences for a feature flag and return the appropriate variant"""

        # Get all experiences that have variants for this feature, ordered by priority
        experiences_with_variants = self.experiences_crud.get_multi_by_org(
            organisation_id=organisation_id,
            app_id=app_id,
            status="active",
            order_by="priority",
            order_direction="asc",
        )

        # Filter experiences that have variants for this feature
        relevant_experiences = []
        for experience in experiences_with_variants:
            # Check if this experience has a variant for our feature
            feature_variants = self.feature_variants_crud.get_feature_variants(
                feature_flag.pid
            )
            for variant in feature_variants:
                if variant.experience_id == experience.pid:
                    relevant_experiences.append((experience, variant))
                    break

        # Evaluate experiences in priority order
        for experience, variant in relevant_experiences:
            if self._user_matches_experience(experience, user, payload):
                # User matches this experience, assign the variant
                self.user_feature_variants_crud.assign_user_variant(
                    user_pid=user.pid,
                    feature_pid=feature_flag.pid,
                    variant_name=variant.name,
                    variant_config=variant.config,
                    organisation_id=organisation_id,
                    app_id=app_id,
                    experience_id=experience.pid,
                )

                return ObjectVariantAssignment(
                    feature_id=feature_flag.pid,
                    feature_name=feature_flag.name,
                    variant_name=variant.name,
                    variant_config=variant.config,
                    experience_id=experience.pid,
                    experience_name=experience.name,
                    evaluation_reason="experience_evaluation",
                )

        # No matching experience, return default variant
        variant_name = "default"
        variant_config = feature_flag.default_variant

        # Save default assignment
        self.user_feature_variants_crud.assign_user_variant(
            user_pid=user.pid,
            feature_pid=feature_flag.pid,
            variant_name=variant_name,
            variant_config=variant_config,
            organisation_id=organisation_id,
            app_id=app_id,
            experience_id=None,
        )

        return ObjectVariantAssignment(
            feature_id=feature_flag.pid,
            feature_name=feature_flag.name,
            variant_name=variant_name,
            variant_config=variant_config,
            experience_id=None,
            experience_name=None,
            evaluation_reason="default",
        )

    def _user_matches_experience(
        self, experience, user, payload: Dict[str, Any]
    ) -> bool:
        """Check if user matches the experience based on its segments"""

        # Get experience segments
        experience_segments = self.experiences_crud.get_with_segments(experience.pid)
        if not experience_segments or not experience_segments.experience_segments:
            # No segments defined, experience matches all users
            return True

        # Check if user matches any of the experience segments
        for exp_segment in experience_segments.experience_segments:
            segment = exp_segment.segment
            if segment and self.rule_evaluator.evaluate_segment(
                segment.rule_config, payload
            ):
                # User matches this segment
                return True

        return False

    def _get_or_create_user(
        self, user_id: str, organisation_id: str, app_id: str, payload: Dict[str, Any]
    ):
        """Get existing user or create new one"""
        user = self.users_crud.get_by_user_id(
            user_id=user_id, organisation_id=organisation_id, app_id=app_id
        )

        if not user:
            # Create new user with payload as profile
            user_data = {
                "user_id": user_id,
                "organisation_id": organisation_id,
                "app_id": app_id,
                "user_profile": payload,
            }
            user = self.users_crud.create(obj_in=user_data)
        else:
            # Update user profile with new payload data
            updated_profile = {**user.user_profile, **payload}
            self.users_crud.update(
                db_obj=user, obj_in={"user_profile": updated_profile}
            )

        return user

    # Legacy method for backward compatibility
    def get_user_feature_variant(
        self,
        user_id: str,
        feature_name: str,
        organisation_id: str,
        app_id: str,
        payload: Dict[str, Any],
    ) -> ObjectVariantAssignment:
        """
        Legacy method for single feature evaluation
        """
        results = self.get_variants_for_objects(
            user_id=user_id,
            organisation_id=organisation_id,
            app_id=app_id,
            payload=payload,
            feature_names=[feature_name],
        )

        if results:
            return results[0]
        else:
            raise HTTPException(
                status_code=404, detail=f"Feature '{feature_name}' not found"
            )
