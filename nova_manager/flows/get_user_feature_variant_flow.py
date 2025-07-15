from typing import Any, Dict
from uuid import UUID
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from nova_manager.components.feature_flags.crud import (
    FeatureFlagsCRUD,
    FeatureVariantsCRUD,
)
from nova_manager.components.rule_evaluator.controller import RuleEvaluator
from nova_manager.components.users.crud import UsersCRUD


class UserFeatureVariantAssignment(BaseModel):
    feature_id: UUID
    feature_name: str
    variant_name: str
    variant_config: Dict[str, Any]
    evaluation_reason: str  # "explicit_assignment", "targeting_rule", "individual_targeting", "default"


class GetUserFeatureVariantFlow:
    def __init__(self, db: Session):
        self.db = db
        self.rule_evaluator = RuleEvaluator()
        self.users_crud = UsersCRUD(db)
        self.feature_flags_crud = FeatureFlagsCRUD(db)
        self.user_feature_variants_crud = UserFeatureVariantsCRUD(db)
        self.feature_variants_crud = FeatureVariantsCRUD(db)
        self.individual_targeting_crud = IndividualTargetingCRUD(db)
        self.targeting_rules_crud = TargetingRulesCRUD(db)

    def get_user_feature_variant(
        self,
        user_id: str,
        feature_name: str,
        organisation_id: str,
        app_id: str,
        payload: Dict[str, Any],
    ) -> UserFeatureVariantAssignment:
        """
        Evaluate feature flag for user with payload context

        Evaluation order:
        1. Check explicit user assignment
        2. Check individual targeting rules
        3. Check targeting rules (by priority)
        4. Return default variant
        """

        # Get or create user
        user = self._get_or_create_user(user_id, organisation_id, app_id, payload)

        # Get feature flag (try by name first, then by UUID if it fails)
        feature_flag = self._get_feature_flag(feature_name, organisation_id, app_id)
        if not feature_flag:
            raise HTTPException(
                status_code=404, detail=f"Feature '{feature_name}' not found"
            )

        # Check if feature is active
        if not feature_flag.is_active:
            # Return default variant for inactive features
            variant_name = "default"
            variant_config = feature_flag.default_variant
            evaluation_reason = "inactive_feature"

            # Save result
            self._save_evaluation_result(
                user.pid,
                feature_flag.pid,
                variant_name,
                variant_config,
                evaluation_reason,
            )

            return UserFeatureVariantAssignment(
                feature_id=feature_flag.pid,
                feature_name=feature_flag.name,
                variant_name=variant_name,
                variant_config=variant_config,
                evaluation_reason=evaluation_reason,
            )

        # 1. Check explicit user assignment
        explicit_assignment = self.user_feature_variants_crud.get_user_assignment(
            user_pid=user.pid, feature_pid=feature_flag.pid
        )
        if explicit_assignment:
            variant_name = explicit_assignment.variant_name
            variant_config = explicit_assignment.variant_config
            evaluation_reason = "explicit_assignment"

            self._save_evaluation_result(
                user.pid,
                feature_flag.pid,
                variant_name,
                variant_config,
                evaluation_reason,
            )

            return UserFeatureVariantAssignment(
                user_id=user_id,
                feature_id=feature_flag.pid,
                feature_name=feature_flag.name,
                variant_name=variant_name,
                variant_config=variant_config,
                evaluation_reason=evaluation_reason,
            )

        # 2. Check individual targeting rules

        individual_rules = (
            self.individual_targeting_crud.get_feature_individual_targeting(
                feature_pid=feature_flag.pid
            )
        )

        for rule in individual_rules:
            if self.rule_evaluator._evaluate_individual_rule(
                rule.rule_config, user_id, payload
            ):
                variant = self._get_variant_from_rule(
                    feature_flag.pid, rule.rule_config
                )
                if variant:
                    variant_name = variant.name
                    variant_config = variant.config
                    evaluation_reason = "individual_targeting"

                    self._save_evaluation_result(
                        user.pid,
                        feature_flag.pid,
                        variant_name,
                        variant_config,
                        evaluation_reason,
                    )

                    return UserFeatureVariantAssignment(
                        user_id=user_id,
                        feature_id=feature_flag.pid,
                        feature_name=feature_flag.name,
                        variant_name=variant_name,
                        variant_config=variant_config,
                        evaluation_reason=evaluation_reason,
                    )

        # 3. Check targeting rules (by priority)

        targeting_rules = self.targeting_rules_crud.get_feature_rules(
            feature_pid=feature_flag.pid, ordered=True
        )

        for rule in targeting_rules:
            if self.rule_evaluator._evaluate_targeting_rule(rule.rule_config, payload):
                variant = self._get_variant_from_rule(
                    feature_flag.pid, rule.rule_config
                )
                if variant:
                    variant_name = variant.name
                    variant_config = variant.config
                    evaluation_reason = "targeting_rule"

                    self._save_evaluation_result(
                        user.pid,
                        feature_flag.pid,
                        variant_name,
                        variant_config,
                        evaluation_reason,
                    )

                    return UserFeatureVariantAssignment(
                        user_id=user_id,
                        feature_id=feature_flag.pid,
                        feature_name=feature_flag.name,
                        variant_name=variant.name,
                        variant_config=variant.config,
                        evaluation_reason=evaluation_reason,
                    )

        # 4. Return default variant
        variant_name = "default"
        variant_config = feature_flag.default_variant
        evaluation_reason = "default"

        self._save_evaluation_result(
            user.pid, feature_flag.pid, variant_name, variant_config, evaluation_reason
        )

        return UserFeatureVariantAssignment(
            user_id=user_id,
            feature_id=feature_flag.pid,
            feature_name=feature_flag.name,
            variant_name=variant_name,
            variant_config=variant_config,
            evaluation_reason=evaluation_reason,
        )

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

    def _get_feature_flag(self, feature_name: str, organisation_id: str, app_id: str):
        """Get feature flag by name or UUID"""
        feature_flag = self.feature_flags_crud.get_by_name(
            name=feature_name, organisation_id=organisation_id, app_id=app_id
        )

        return feature_flag

    def _get_variant_from_rule(self, feature_pid: str, rule_config: Dict[str, Any]):
        """Extract variant from rule configuration"""
        variant_name = rule_config.get("variant")
        if variant_name:
            return self.feature_variants_crud.get_by_name(
                name=variant_name, feature_pid=feature_pid
            )
        return None

    def _save_evaluation_result(
        self,
        user_pid: str,
        feature_pid: str,
        variant_name: str,
        variant_config: dict,
        reason: str,
    ):
        """Save or update user's variant assignment based on evaluation"""

        # Get user and feature for org/app info
        user = self.users_crud.get_by_pid(user_pid)
        if user:
            self.user_feature_variants_crud.assign_user_variant(
                user_pid=user_pid,
                feature_pid=feature_pid,
                variant_name=variant_name,
                variant_config=variant_config,
                organisation_id=user.organisation_id,
                app_id=user.app_id,
            )
