from typing import Any, Dict
from uuid import UUID
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from nova_manager.components.feature_flags.crud import (
    FeatureFlagsCRUD,
    FeatureVariantsCRUD,
    IndividualTargetingCRUD,
    TargetingRulesCRUD,
)
from nova_manager.components.user_feature_variant.crud import UserFeatureVariantsCRUD
from nova_manager.components.users.crud import UsersCRUD


class UserFeatureVariantAssignment(BaseModel):
    user_id: str
    feature_id: UUID
    feature_name: str
    variant_name: str
    variant_config: Dict[str, Any]
    evaluation_reason: str  # "explicit_assignment", "targeting_rule", "individual_targeting", "default"


class GetUserFeatureVariantFlow:
    def __init__(self, db: Session):
        self.db = db
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
            default_variant = feature_flag.default_variant
            if not default_variant:
                raise HTTPException(
                    status_code=404, detail="Feature has no default variant"
                )

            # Save result
            self._save_evaluation_result(
                user.pid, feature_flag.pid, default_variant.pid, "inactive_feature"
            )

            return UserFeatureVariantAssignment(
                user_id=user_id,
                feature_id=feature_flag.pid,
                feature_name=feature_flag.name,
                variant_name=default_variant.name,
                variant_config=default_variant.config,
                evaluation_reason="inactive_feature",
            )

        # 1. Check explicit user assignment
        explicit_assignment = self.user_feature_variants_crud.get_user_assignment(
            user_pid=user.pid, feature_pid=feature_flag.pid
        )
        if explicit_assignment:
            variant = explicit_assignment.variant
            self._save_evaluation_result(
                user.pid, feature_flag.pid, variant.pid, "explicit_assignment"
            )

            return UserFeatureVariantAssignment(
                user_id=user_id,
                feature_id=feature_flag.pid,
                feature_name=feature_flag.name,
                variant_name=variant.name,
                variant_config=variant.config,
                evaluation_reason="explicit_assignment",
            )

        # 2. Check individual targeting rules

        individual_rules = (
            self.individual_targeting_crud.get_feature_individual_targeting(
                feature_pid=feature_flag.pid
            )
        )

        for rule in individual_rules:
            if self._evaluate_individual_rule(rule.rule_config, user_id, payload):
                variant = self._get_variant_from_rule(
                    feature_flag.pid, rule.rule_config
                )
                if variant:
                    self._save_evaluation_result(
                        user.pid, feature_flag.pid, variant.pid, "individual_targeting"
                    )

                    return UserFeatureVariantAssignment(
                        user_id=user_id,
                        feature_id=feature_flag.pid,
                        feature_name=feature_flag.name,
                        variant_name=variant.name,
                        variant_config=variant.config,
                        evaluation_reason="individual_targeting",
                    )

        # 3. Check targeting rules (by priority)

        targeting_rules = self.targeting_rules_crud.get_feature_rules(
            feature_pid=feature_flag.pid, ordered=True
        )

        for rule in targeting_rules:
            if self._evaluate_targeting_rule(rule.rule_config, user_id, payload):
                variant = self._get_variant_from_rule(
                    feature_flag.pid, rule.rule_config
                )
                if variant:
                    self._save_evaluation_result(
                        user.pid, feature_flag.pid, variant.pid, "targeting_rule"
                    )

                    return UserFeatureVariantAssignment(
                        user_id=user_id,
                        feature_id=feature_flag.pid,
                        feature_name=feature_flag.name,
                        variant_name=variant.name,
                        variant_config=variant.config,
                        evaluation_reason="targeting_rule",
                    )

        # 4. Return default variant
        default_variant = feature_flag.default_variant
        if not default_variant:
            raise HTTPException(
                status_code=404, detail="Feature has no default variant"
            )

        self._save_evaluation_result(
            user.pid, feature_flag.pid, default_variant.pid, "default"
        )

        return UserFeatureVariantAssignment(
            user_id=user_id,
            feature_id=feature_flag.pid,
            feature_name=feature_flag.name,
            variant_name=default_variant.name,
            variant_config=default_variant.config,
            evaluation_reason="default",
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

    def _evaluate_individual_rule(
        self, rule_config: Dict[str, Any], user_id: str, payload: Dict[str, Any]
    ) -> bool:
        """Evaluate individual targeting rule"""
        # Example rule format:
        # {
        #   "user_ids": ["user1", "user2"],
        #   "user_attributes": {"country": "US", "plan": "premium"}
        # }

        # Check user IDs
        if "user_ids" in rule_config:
            if user_id in rule_config["user_ids"]:
                return True

        # Check user attributes from payload
        if "user_attributes" in rule_config:
            for key, expected_value in rule_config["user_attributes"].items():
                if payload.get(key) != expected_value:
                    return False
            return True

        return False

    def _evaluate_targeting_rule(
        self, rule_config: Dict[str, Any], user_id: str, payload: Dict[str, Any]
    ) -> bool:
        """Evaluate targeting rule with conditions"""
        # Example rule format:
        # {
        #   "conditions": [
        #     {"field": "country", "operator": "equals", "value": "US"},
        #     {"field": "age", "operator": "greater_than", "value": 18}
        #   ]
        # }

        if "conditions" not in rule_config:
            return False

        for condition in rule_config["conditions"]:
            field = condition.get("field")
            operator = condition.get("operator")
            expected_value = condition.get("value")

            actual_value = payload.get(field)

            if not self._evaluate_condition(actual_value, operator, expected_value):
                return False

        return True

    def _evaluate_condition(
        self, actual_value: Any, operator: str, expected_value: Any
    ) -> bool:
        """Evaluate a single condition"""
        if operator == "equals":
            return actual_value == expected_value
        elif operator == "not_equals":
            return actual_value != expected_value
        elif operator == "greater_than":
            return actual_value > expected_value
        elif operator == "less_than":
            return actual_value < expected_value
        elif operator == "greater_than_or_equal":
            return actual_value >= expected_value
        elif operator == "less_than_or_equal":
            return actual_value <= expected_value
        elif operator == "in":
            return actual_value in expected_value
        elif operator == "not_in":
            return actual_value not in expected_value
        elif operator == "contains":
            return expected_value in str(actual_value)
        elif operator == "starts_with":
            return str(actual_value).startswith(str(expected_value))
        elif operator == "ends_with":
            return str(actual_value).endswith(str(expected_value))
        else:
            return False

    def _get_variant_from_rule(self, feature_pid: str, rule_config: Dict[str, Any]):
        """Extract variant from rule configuration"""
        variant_name = rule_config.get("variant")
        if variant_name:
            return self.feature_variants_crud.get_by_name(
                name=variant_name, feature_pid=feature_pid
            )
        return None

    def _save_evaluation_result(
        self, user_pid: str, feature_pid: str, variant_pid: str, reason: str
    ):
        """Save or update user's variant assignment based on evaluation"""

        # Get user and feature for org/app info
        user = self.users_crud.get_by_pid(user_pid)
        if user:
            self.user_feature_variants_crud.assign_user_variant(
                user_pid=user_pid,
                feature_pid=feature_pid,
                variant_pid=variant_pid,
                organisation_id=user.organisation_id,
                app_id=user.app_id,
            )
