from typing import Optional, List, Dict, Any
from uuid import UUID as UUIDType
from nova_manager.components.experiences.models import (
    Experiences,
    ExperienceSegments,
    Personalisations,
    PersonalisationFeatureVariants,
)
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_

from nova_manager.components.feature_flags.models import FeatureFlags, FeatureVariants
from nova_manager.core.base_crud import BaseCRUD


class FeatureFlagsCRUD(BaseCRUD):
    """CRUD operations for FeatureFlags"""

    def __init__(self, db: Session):
        super().__init__(FeatureFlags, db)

    def get_by_name(
        self, name: str, organisation_id: str, app_id: str
    ) -> Optional[FeatureFlags]:
        """Get feature flag by name within an organization and app"""
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

    def get_flags_by_names(
        self, feature_names: List[str], organisation_id: str, app_id: str
    ) -> List[FeatureFlags]:
        """Get feature flags by names in a single query"""
        return (
            self.db.query(FeatureFlags)
            .filter(
                and_(
                    FeatureFlags.name.in_(feature_names),
                    FeatureFlags.organisation_id == organisation_id,
                    FeatureFlags.app_id == app_id,
                )
            )
            .all()
        )

    def get_flags_by_pids(self, feature_pids: List[UUIDType]) -> List[FeatureFlags]:
        """Get feature flags by names in a single query"""
        return (
            self.db.query(FeatureFlags)
            .filter(
                FeatureFlags.pid.in_(feature_pids),
            )
            .all()
        )

    def get_with_variants(self, pid: UUIDType) -> Optional[FeatureFlags]:
        """Get feature flag with all variants loaded"""
        return (
            self.db.query(FeatureFlags)
            .options(
                selectinload(FeatureFlags.variants),
            )
            .filter(FeatureFlags.pid == pid)
            .first()
        )

    def toggle_active(self, pid: UUIDType) -> Optional[FeatureFlags]:
        """Toggle active status of feature flag"""
        flag = self.get_by_pid(pid)
        if flag:
            flag.is_active = not flag.is_active
            self.db.flush()
            self.db.refresh(flag)
        return flag

    def bulk_assign_experience(
        self, experience_id: UUIDType, feature_flags: List
    ) -> None:
        """Bulk assign feature flags to an experience"""
        for flag in feature_flags:
            flag.experience_id = experience_id

        self.db.flush()

    def get_with_full_details(self, pid: UUIDType) -> Optional[FeatureFlags]:
        """Get feature flag with all details including experience usage"""
        return (
            self.db.query(FeatureFlags)
            # .options(
            #     # Load variants and their experiences with campaigns
            #     selectinload(FeatureFlags.variants)
            #     .selectinload(FeatureVariants.experience)
            #     .selectinload(Experiences.experience_campaigns)
            #     .selectinload(ExperienceCampaigns.campaign),
            #     # Load variants and their experiences with segments
            #     selectinload(FeatureFlags.variants)
            #     .selectinload(FeatureVariants.experience)
            #     .selectinload(Experiences.experience_segments)
            #     .selectinload(ExperienceSegments.segment),
            #     # Load variants and their experiences with feature variants
            #     selectinload(FeatureFlags.variants)
            #     .selectinload(FeatureVariants.experience)
            #     .selectinload(Experiences.feature_variants),
            # )
            .filter(FeatureFlags.pid == pid).first()
        )

    def get_available_flags(
        self, organisation_id: str, app_id: str
    ) -> List[FeatureFlags]:
        """Get feature flags that are not assigned to any experience"""
        return (
            self.db.query(FeatureFlags)
            .filter(
                and_(
                    FeatureFlags.organisation_id == organisation_id,
                    FeatureFlags.app_id == app_id,
                    FeatureFlags.experience_id.is_(None),
                )
            )
            .all()
        )

    def get_feature_flags_count(self, experience_id: UUIDType) -> int:
        """Get count of feature flags assigned to an experience"""
        return (
            self.db.query(FeatureFlags)
            .filter(FeatureFlags.experience_id == experience_id)
            .count()
        )

    def get_flags_with_full_experience_data(
        self,
        organisation_id: str,
        app_id: str,
        feature_names: Optional[List[str]] = None,
    ) -> List[FeatureFlags]:
        """
        Get feature flags with all related experience data loaded in a single query.
        Loads complete evaluation chain:
        - FeatureFlags.variants (for feature flag variants)
        - FeatureFlags.experience (experience details)
        - Experience.experience_segments + ExperienceSegments.segment (segments with rules)
        - ExperienceSegments.personalisations -> ExperienceSegmentPersonalisations.personalisation (segment assignments)
        - Personalisations.feature_variants -> PersonalisationFeatureVariants.feature_variant (personalisation variants)
        - Experience.personalisations (direct personalisation access for evaluation)
        """
        query = self.db.query(FeatureFlags).filter(
            and_(
                FeatureFlags.organisation_id == organisation_id,
                FeatureFlags.app_id == app_id,
                FeatureFlags.is_active == True,
            )
        )

        # Filter by feature names if provided
        if feature_names:
            query = query.filter(FeatureFlags.name.in_(feature_names))

        # Load all related data in a single query
        query = query.options(
            # Load feature variants directly on the feature flag
            selectinload(FeatureFlags.variants),
            # Load experience
            selectinload(FeatureFlags.experience),
            # Load experience segments with their segments (ordered by priority)
            selectinload(FeatureFlags.experience)
            .selectinload(Experiences.experience_segments)
            .selectinload(ExperienceSegments.segment),
            # Load experience segment personalisations
            selectinload(FeatureFlags.experience)
            .selectinload(Experiences.experience_segments)
            .selectinload(ExperienceSegments.personalisations),
            # Also load personalisations directly from experience
            selectinload(FeatureFlags.experience)
            .selectinload(Experiences.personalisations)
            .selectinload(Personalisations.feature_variants)
            .selectinload(PersonalisationFeatureVariants.feature_variant)
            .selectinload(FeatureVariants.feature_flag),
        )

        return query.all()


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

    def create_variant(
        self, feature_pid: UUIDType, variant_data: Dict[str, Any]
    ) -> FeatureVariants:
        """Create a new variant for a feature"""
        variant = FeatureVariants(feature_id=feature_pid, **variant_data)
        self.db.add(variant)
        self.db.flush()
        self.db.refresh(variant)
        return variant

    def update_config(
        self, pid: UUIDType, config: Dict[str, Any]
    ) -> Optional[FeatureVariants]:
        """Update variant configuration"""
        variant = self.get_by_pid(pid)
        if variant:
            variant.config = config
            self.db.flush()
            self.db.refresh(variant)
        return variant

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
        self.db.flush()
        self.db.refresh(cloned_variant)
        return cloned_variant
