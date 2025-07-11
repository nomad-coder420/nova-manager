from typing import Optional, List, Dict, Any
from uuid import UUID as UUIDType
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import and_

from nova_manager.components.feature_flags.models import (
    FeatureFlags,
    FeatureVariants,
    IndividualTargeting,
    TargetingRules,
)
from nova_manager.components.user_feature_variant.models import UserFeatureVariants
from nova_manager.core.base_crud import BaseCRUD


class FeatureFlagsCRUD(BaseCRUD):
    """CRUD operations for FeatureFlags"""

    def __init__(self, db: Session):
        super().__init__(FeatureFlags, db)

    def get_by_name(
        self, name: str, organisation_id: str, app_id: str
    ) -> Optional[FeatureFlags]:
        """Get feature flag by name within organization/app scope"""
        return (
            self.db.query(FeatureFlags)
            .filter(
                and_(
                    FeatureFlags.name == name,
                    FeatureFlags.organisation_id == organisation_id,
                    FeatureFlags.app_id == app_id,
                )
            )
            .first()
        )

    def get_active_flags(self, organisation_id: str, app_id: str) -> List[FeatureFlags]:
        """Get all active feature flags for an organization/app"""
        return (
            self.db.query(FeatureFlags)
            .filter(
                and_(
                    FeatureFlags.is_active == True,
                    FeatureFlags.organisation_id == organisation_id,
                    FeatureFlags.app_id == app_id,
                )
            )
            .all()
        )

    def get_with_variants(self, pid: UUIDType) -> Optional[FeatureFlags]:
        """Get feature flag with all variants loaded"""
        return (
            self.db.query(FeatureFlags)
            .options(
                selectinload(FeatureFlags.variants),
                joinedload(FeatureFlags.default_variant),
            )
            .filter(FeatureFlags.pid == pid)
            .first()
        )

    def get_with_all_relations(self, pid: UUIDType) -> Optional[FeatureFlags]:
        """Get feature flag with all related data loaded"""
        return (
            self.db.query(FeatureFlags)
            .options(
                selectinload(FeatureFlags.variants),
                joinedload(FeatureFlags.default_variant),
                selectinload(FeatureFlags.targeting_rules),
                selectinload(FeatureFlags.individual_targeting),
                selectinload(FeatureFlags.user_feature_variants),
            )
            .filter(FeatureFlags.pid == pid)
            .first()
        )

    def create_with_default_variant(
        self,
        flag_data: Dict[str, Any],
        default_variant_data: Optional[Dict[str, Any]] = None,
    ) -> FeatureFlags:
        """Create feature flag with a default variant"""
        # Create feature flag first
        flag = FeatureFlags(**flag_data)
        self.db.add(flag)
        self.db.flush()  # Get the PID without committing

        # Create default variant
        if not default_variant_data:
            default_variant_data = {"name": "default"}

        default_variant = FeatureVariants(feature_id=flag.pid, **default_variant_data)
        self.db.add(default_variant)
        self.db.flush()

        # Set default variant reference
        flag.default_variant_id = default_variant.pid
        self.db.commit()
        self.db.refresh(flag)
        return flag

    def set_default_variant(
        self, flag_pid: UUIDType, variant_pid: UUIDType
    ) -> Optional[FeatureFlags]:
        """Set default variant for a feature flag"""
        flag = self.get_by_pid(flag_pid)
        if flag:
            # Verify variant belongs to this flag
            variant = (
                self.db.query(FeatureVariants)
                .filter(
                    and_(
                        FeatureVariants.pid == variant_pid,
                        FeatureVariants.feature_id == flag_pid,
                    )
                )
                .first()
            )

            if variant:
                flag.default_variant_id = variant_pid
                self.db.commit()
                self.db.refresh(flag)
        return flag

    def toggle_active(self, pid: UUIDType) -> Optional[FeatureFlags]:
        """Toggle active status of feature flag"""
        flag = self.get_by_pid(pid)
        if flag:
            flag.is_active = not flag.is_active
            self.db.commit()
            self.db.refresh(flag)
        return flag


class FeatureVariantsCRUD(BaseCRUD):
    """CRUD operations for FeatureVariants"""

    def __init__(self, db: Session):
        super().__init__(FeatureVariants, db)

    def get_by_name(
        self, name: str, feature_pid: UUIDType
    ) -> Optional[FeatureVariants]:
        """Get variant by name within a feature"""
        return (
            self.db.query(FeatureVariants)
            .filter(
                and_(
                    FeatureVariants.name == name,
                    FeatureVariants.feature_id == feature_pid,
                )
            )
            .first()
        )

    def get_feature_variants(self, feature_pid: UUIDType) -> List[FeatureVariants]:
        """Get all variants for a feature"""
        return (
            self.db.query(FeatureVariants)
            .filter(FeatureVariants.feature_id == feature_pid)
            .all()
        )

    def get_with_assignments(self, pid: UUIDType) -> Optional[FeatureVariants]:
        """Get variant with all user assignments"""
        return (
            self.db.query(FeatureVariants)
            .options(
                selectinload(FeatureVariants.user_feature_variants).selectinload(
                    UserFeatureVariants.user
                ),
                joinedload(FeatureVariants.feature_flag),
            )
            .filter(FeatureVariants.pid == pid)
            .first()
        )

    def create_variant(
        self, feature_pid: UUIDType, variant_data: Dict[str, Any]
    ) -> FeatureVariants:
        """Create a new variant for a feature"""
        variant = FeatureVariants(feature_id=feature_pid, **variant_data)
        self.db.add(variant)
        self.db.commit()
        self.db.refresh(variant)
        return variant

    def update_config(
        self, pid: UUIDType, config: Dict[str, Any]
    ) -> Optional[FeatureVariants]:
        """Update variant configuration"""
        variant = self.get_by_pid(pid)
        if variant:
            variant.config = config
            self.db.commit()
            self.db.refresh(variant)
        return variant

    def get_variant_usage_stats(self, pid: UUIDType) -> Dict[str, Any]:
        """Get usage statistics for a variant"""
        variant = self.get_with_assignments(pid=pid)
        if not variant:
            return {}

        total_assignments = len(variant.user_feature_variants)

        # Check if this is the default variant for its feature
        is_default = variant.feature_flag.default_variant_id == pid

        return {
            "variant_name": variant.name,
            "feature_name": variant.feature_flag.name,
            "total_explicit_assignments": total_assignments,
            "is_default_variant": is_default,
            "config": variant.config,
        }

    def clone_variant(
        self,
        source_pid: UUIDType,
        new_name: str,
        new_config: Optional[Dict[str, Any]] = None,
    ) -> Optional[FeatureVariants]:
        """Clone an existing variant with a new name"""
        source = self.get_by_pid(source_pid)
        if not source:
            return None

        cloned_variant = FeatureVariants(
            feature_id=source.feature_id,
            name=new_name,
            config=new_config if new_config is not None else source.config.copy(),
        )
        self.db.add(cloned_variant)
        self.db.commit()
        self.db.refresh(cloned_variant)
        return cloned_variant


class TargetingRulesCRUD(BaseCRUD):
    """CRUD operations for TargetingRules"""

    def __init__(self, db: Session):
        super().__init__(TargetingRules, db)

    def get_feature_rules(
        self, feature_pid: UUIDType, ordered: bool = True
    ) -> List[TargetingRules]:
        """Get all targeting rules for a feature, optionally ordered by priority"""
        query = self.db.query(TargetingRules).filter(
            TargetingRules.feature_id == feature_pid
        )

        if ordered:
            query = query.order_by(TargetingRules.priority)

        return query.all()

    def get_with_feature(self, pid: UUIDType) -> Optional[TargetingRules]:
        """Get targeting rule with feature flag loaded"""
        return (
            self.db.query(TargetingRules)
            .options(joinedload(TargetingRules.feature_flag))
            .filter(TargetingRules.pid == pid)
            .first()
        )

    def create_rule(
        self,
        feature_pid: UUIDType,
        rule_config: Dict[str, Any],
        priority: Optional[int] = None,
    ) -> TargetingRules:
        """Create a new targeting rule for a feature"""
        # Auto-assign priority if not provided
        if priority is None:
            max_priority = (
                self.db.query(TargetingRules)
                .filter(TargetingRules.feature_id == feature_pid)
                .order_by(TargetingRules.priority.desc())
                .first()
            )
            priority = (max_priority.priority + 1) if max_priority else 1

        rule = TargetingRules(
            feature_id=feature_pid, rule_config=rule_config, priority=priority
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def update_priority(
        self, pid: UUIDType, new_priority: int
    ) -> Optional[TargetingRules]:
        """Update rule priority"""
        rule = self.get_by_pid(pid)
        if rule:
            rule.priority = new_priority
            self.db.commit()
            self.db.refresh(rule)
        return rule

    def update_config(
        self, pid: UUIDType, rule_config: Dict[str, Any]
    ) -> Optional[TargetingRules]:
        """Update rule configuration"""
        rule = self.get_by_pid(pid)
        if rule:
            rule.rule_config = rule_config
            self.db.commit()
            self.db.refresh(rule)
        return rule

    def reorder_rules(
        self,
        feature_pid: UUIDType,
        rule_priorities: List[Dict[str, Any]],  # [{"pid": uuid, "priority": int}, ...]
    ) -> List[TargetingRules]:
        """Reorder multiple rules by updating their priorities"""
        updated_rules = []

        for rule_priority in rule_priorities:
            rule = self.get_by_pid(rule_priority["pid"])
            if rule and rule.feature_id == feature_pid:
                rule.priority = rule_priority["priority"]
                updated_rules.append(rule)

        self.db.commit()
        for rule in updated_rules:
            self.db.refresh(rule)

        return updated_rules

    def get_rules_by_priority_range(
        self,
        feature_pid: UUIDType,
        min_priority: int,
        max_priority: int,
    ) -> List[TargetingRules]:
        """Get rules within a priority range"""
        return (
            self.db.query(TargetingRules)
            .filter(
                and_(
                    TargetingRules.feature_id == feature_pid,
                    TargetingRules.priority >= min_priority,
                    TargetingRules.priority <= max_priority,
                )
            )
            .order_by(TargetingRules.priority)
            .all()
        )

    def duplicate_rule(
        self, source_pid: UUIDType, new_priority: Optional[int] = None
    ) -> Optional[TargetingRules]:
        """Duplicate an existing targeting rule"""
        source = self.get_by_pid(source_pid)
        if not source:
            return None

        if new_priority is None:
            # Get next priority for the feature
            max_priority = (
                self.db.query(TargetingRules)
                .filter(TargetingRules.feature_id == source.feature_id)
                .order_by(TargetingRules.priority.desc())
                .first()
            )
            new_priority = (max_priority.priority + 1) if max_priority else 1

        duplicated_rule = TargetingRules(
            feature_id=source.feature_id,
            rule_config=source.rule_config.copy(),
            priority=new_priority,
        )
        self.db.add(duplicated_rule)
        self.db.commit()
        self.db.refresh(duplicated_rule)
        return duplicated_rule


class IndividualTargetingCRUD(BaseCRUD):
    """CRUD operations for IndividualTargeting"""

    def __init__(self, db: Session):
        super().__init__(IndividualTargeting, db)

    def get_feature_individual_targeting(
        self, feature_pid: UUIDType
    ) -> List[IndividualTargeting]:
        """Get all individual targeting rules for a feature"""
        return (
            self.db.query(IndividualTargeting)
            .filter(IndividualTargeting.feature_id == feature_pid)
            .all()
        )

    def get_with_feature(self, pid: UUIDType) -> Optional[IndividualTargeting]:
        """Get individual targeting with feature flag loaded"""
        return (
            self.db.query(IndividualTargeting)
            .options(joinedload(IndividualTargeting.feature_flag))
            .filter(IndividualTargeting.pid == pid)
            .first()
        )

    def create_individual_targeting(
        self, feature_pid: UUIDType, rule_config: Dict[str, Any]
    ) -> IndividualTargeting:
        """Create a new individual targeting rule"""
        targeting = IndividualTargeting(feature_id=feature_pid, rule_config=rule_config)
        self.db.add(targeting)
        self.db.commit()
        self.db.refresh(targeting)
        return targeting

    def update_config(
        self, pid: UUIDType, rule_config: Dict[str, Any]
    ) -> Optional[IndividualTargeting]:
        """Update individual targeting configuration"""
        targeting = self.get_by_pid(pid)
        if targeting:
            targeting.rule_config = rule_config
            self.db.commit()
            self.db.refresh(targeting)
        return targeting

    def get_targeting_for_user(
        self,
        feature_pid: UUIDType,
        user_identifier: str,  # Could be user_id or any identifier in rule_config
    ) -> List[IndividualTargeting]:
        """Get individual targeting rules that might apply to a specific user"""
        # This is a placeholder - actual implementation depends on your rule_config structure
        # You might search within JSON fields or have specific user targeting patterns
        return (
            self.db.query(IndividualTargeting)
            .filter(
                and_(
                    IndividualTargeting.feature_id == feature_pid,
                    IndividualTargeting.rule_config.op("?")(
                        user_identifier
                    ),  # JSON search
                )
            )
            .all()
        )

    def bulk_create_individual_targeting(
        self, feature_pid: UUIDType, rule_configs: List[Dict[str, Any]]
    ) -> List[IndividualTargeting]:
        """Create multiple individual targeting rules at once"""
        targetings = []

        for rule_config in rule_configs:
            targeting = IndividualTargeting(
                feature_id=feature_pid, rule_config=rule_config
            )
            targetings.append(targeting)

        self.db.add_all(targetings)
        self.db.commit()

        for targeting in targetings:
            self.db.refresh(targeting)

        return targetings

    def get_targeting_stats(self, feature_pid: UUIDType) -> Dict[str, Any]:
        """Get statistics for individual targeting rules of a feature"""
        targetings = self.get_feature_individual_targeting(
            self.db, feature_pid=feature_pid
        )

        # Analyze rule configs (this is a basic example)
        config_keys = set()
        for targeting in targetings:
            config_keys.update(targeting.rule_config.keys())

        return {
            "total_individual_targeting_rules": len(targetings),
            "unique_config_keys": list(config_keys),
            "average_config_complexity": (
                sum(len(t.rule_config) for t in targetings) / len(targetings)
                if targetings
                else 0
            ),
        }

    def clone_targeting(
        self,
        source_pid: UUIDType,
        target_feature_pid: Optional[UUIDType] = None,
    ) -> Optional[IndividualTargeting]:
        """Clone individual targeting rule to same or different feature"""
        source = self.get_by_pid(source_pid)
        if not source:
            return None

        cloned_targeting = IndividualTargeting(
            feature_id=target_feature_pid or source.feature_id,
            rule_config=source.rule_config.copy(),
        )
        self.db.add(cloned_targeting)
        self.db.commit()
        self.db.refresh(cloned_targeting)
        return cloned_targeting
