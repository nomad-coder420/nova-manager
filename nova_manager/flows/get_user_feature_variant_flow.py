from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import HTTPException
from nova_manager.components.experiences.models import (
    ExperienceSegmentPersonalisations,
    ExperienceSegments,
)
from nova_manager.components.segments.models import Segments
from nova_manager.components.users.models import Users
from pydantic import BaseModel
from sqlalchemy.orm import Session

from nova_manager.components.rule_evaluator.controller import RuleEvaluator
from nova_manager.components.users.crud import UsersCRUD
from nova_manager.components.feature_flags.crud import FeatureFlagsCRUD
from nova_manager.components.feature_flags.models import FeatureFlags, FeatureVariants


class ObjectVariantAssignment(BaseModel):
    feature_id: UUID
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


class GetUserFeatureVariantFlow:
    def __init__(self, db: Session):
        self.db = db
        self.rule_evaluator = RuleEvaluator()
        self.users_crud = UsersCRUD(db)
        self.feature_flags_crud = FeatureFlagsCRUD(db)

        # Cache fields
        self.experience_personalisation_map = {}
        self.segment_results_map = {}

    def get_variants_for_objects(
        self,
        user_id: str,
        organisation_id: str,
        app_id: str,
        payload: Dict[str, Any],
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, ObjectVariantAssignment]:
        # Step 1: Check if user exists, if yes update user payload, if no create user
        user = self._update_or_create_user(user_id, organisation_id, app_id, payload)

        if not user:
            raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

        # Step 2: Fetch features with experiences and related data in single query
        features = self.feature_flags_crud.get_flags_with_full_experience_data(
            organisation_id, app_id, feature_names
        )

        # Process each feature
        results = {}

        for feature in features:
            if feature.name in results:
                continue

            feature_variant = None

            if feature.experience_id and feature.experience:
                experience_id = feature.experience_id
                experience_name = feature.experience.name
                experience_segments = feature.experience.experience_segments

                selected_personalisation, segment = (
                    self._get_experience_segment_personalisation(
                        user, experience_id, experience_segments
                    )
                )

                if selected_personalisation and segment:
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
                            segment_id=segment.pid,
                            segment_name=segment.name,
                            evaluation_reason="segment_match_personalisation",
                        )

                        results[pfv_feature_name] = pfv_feature_variant

                        if pfv_feature_id == feature.pid:
                            feature_variant = pfv_feature_variant

                elif not segment:
                    feature_variant = self._find_default_variant(
                        feature,
                        "no_segment_match",
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
            print("\n\n\n\n\n\n############\n\n\n\n\n\n")

        return results

    def _update_or_create_user(
        self, user_id: str, organisation_id: str, app_id: str, payload: Dict[str, Any]
    ):
        user = self.users_crud.get_by_user_id(
            user_id=user_id, organisation_id=organisation_id, app_id=app_id
        )

        if user:
            # User exists, update user profile with new payload
            self.users_crud.update(db_obj=user, obj_in={"user_profile": payload})
        else:
            # User doesn't exist, create new user with user profile
            user = self.users_crud.create(
                {
                    "user_id": user_id,
                    "organisation_id": organisation_id,
                    "app_id": app_id,
                    "user_profile": payload,
                }
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
        if not feature.variants:
            return ObjectVariantAssignment(
                feature_id=feature.pid,
                feature_name=feature.name,
                variant_id=None,  # No specific variant
                variant_name="default",
                variant_config=feature.default_variant,
                experience_id=experience_id,
                experience_name=experience_name,
                personalisation_id=None,
                personalisation_name=None,
                segment_id=None,
                segment_name=None,
                evaluation_reason=f"{reason}_no_variant_assigned_error",
            )

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

    def _get_experience_segment_personalisation(
        self,
        user: Users,
        experience_id: UUID,
        experience_segments: List[ExperienceSegments],
    ):
        selected_personalisation, segment = None, None

        if experience_id in self.experience_personalisation_map:
            selected_personalisation, segment = self.experience_personalisation_map[
                experience_id
            ]

        else:
            experience_segment = self._evaluate_experience_segments(
                user, experience_id, experience_segments
            )

            print("experience_segment", experience_segment)

            if experience_segment:
                segment = experience_segment.segment

                selected_personalisation = self._evaluate_segment_personalisations(
                    user,
                    experience_id,
                    segment,
                    experience_segment.personalisations,
                )

                self.experience_personalisation_map[experience_id] = (
                    selected_personalisation,
                    segment,
                )

        return selected_personalisation, segment

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

                print("segment_result", segment_result)
                if segment_result:
                    # User matches the segment rule, now check target percentage
                    context_id = f"{experience_id}:{segment.pid}"

                    segment_target_result = (
                        self.rule_evaluator.evaluate_target_percentage(
                            user.user_id,
                            experience_segment.target_percentage,
                            context_id,
                        )
                    )

                    print("segment_target_result", segment_target_result)

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
    ):
        # Evaluate each personalisation's target percentage
        for segment_personalisation in segment_personalisations:
            context_id = f"{experience_id}:{segment.pid}:{segment_personalisation.personalisation_id}"

            # Check if user falls within this personalisation's target percentage
            if self.rule_evaluator.evaluate_target_percentage(
                user.user_id, segment_personalisation.target_percentage, context_id
            ):
                # User matches this personalisation, find the variant for this feature
                selected_personalisation = segment_personalisation.personalisation

                # If we found a matching personalisation, stop looking for more personalisations
                return selected_personalisation

        # No matching personalisation found. Error!
        return None

    def get_user_feature_variant(
        self,
        user_id: str,
        feature_name: str,
        organisation_id: str,
        app_id: str,
        payload: Dict[str, Any],
    ) -> ObjectVariantAssignment:
        results = self.get_variants_for_objects(
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
