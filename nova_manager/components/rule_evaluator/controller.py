from typing import Any, Dict


class RuleEvaluator:
    def _evaluate_targeting_rule(
        self, rule_config: Dict[str, Any], payload: Dict[str, Any]
    ) -> bool:
        """Evaluate targeting rule with conditions"""
        # Example rule format:
        # {
        #   "conditions": [
        #     {"field": "country", "operator": "equals", "value": "US", "type": "text"},
        #     {"field": "age", "operator": "greater_than", "value": 18, "type": "number"},
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
