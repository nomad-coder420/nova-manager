from datetime import datetime, timezone
from nova_manager.components.personalisations.models import (
    ExperienceFeatureVariants,
    Personalisations,
    TargetingRulePersonalisations,
    TargetingRuleSegments,
    TargetingRules,
)
from typing import Optional, List, Dict, Any
from uuid import UUID as UUIDType
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, desc, asc

from nova_manager.components.experiences.models import ExperienceFeatures, Experiences
from nova_manager.components.feature_flags.models import FeatureFlags
from nova_manager.core.base_crud import BaseCRUD


class ExperiencesCRUD(BaseCRUD):
    """CRUD operations for Experiences"""

    def __init__(self, db: Session):
        super().__init__(Experiences, db)

    def get_by_name(
        self, name: str, organisation_id: str, app_id: str
    ) -> Optional[Experiences]:
        """Get experience by name within an organization and app"""
        return (
            self.db.query(Experiences)
            .filter(
                and_(
                    Experiences.name == name,
                    Experiences.organisation_id == organisation_id,
                    Experiences.app_id == app_id,
                )
            )
            .first()
        )

    def get_multi_by_org(
        self,
        organisation_id: str,
        app_id: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> List[Experiences]:
        """Get experiences for organization/app with pagination and filtering"""
        query = (
            self.db.query(Experiences)
            .options(selectinload(Experiences.features))
            .filter(
                and_(
                    Experiences.organisation_id == organisation_id,
                    Experiences.app_id == app_id,
                )
            )
        )

        # Filter by status if provided
        if status:
            query = query.filter(Experiences.status == status)

        # Apply ordering
        order_column = getattr(Experiences, order_by, Experiences.created_at)
        if order_direction.lower() == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))

        return query.offset(skip).limit(limit).all()

    def get_with_features(self, pid: UUIDType) -> Optional[Experiences]:
        """Get experience with all experience features loaded"""
        return (
            self.db.query(Experiences)
            .options(selectinload(Experiences.features))
            .filter(Experiences.pid == pid)
            .first()
        )

    def get_with_feature_flag_variants(self, pid: UUIDType) -> Optional[Experiences]:
        """Get experience with all related data loaded"""
        return (
            self.db.query(Experiences)
            .options(
                # Load feature flags with their variants
                selectinload(Experiences.features).selectinload(
                    ExperienceFeatures.feature_flag
                ),
                # Load feature flags with their variants
                selectinload(Experiences.features).selectinload(
                    ExperienceFeatures.variants
                ),
            )
            .filter(Experiences.pid == pid)
            .first()
        )

    def get_with_personalisations_data(self, pid: UUIDType) -> Optional[Experiences]:
        """Get experience with all personalisations loaded"""
        return (
            self.db.query(Experiences)
            .options(
                selectinload(Experiences.personalisations)
                .selectinload(Personalisations.variants)
                .selectinload(ExperienceFeatureVariants.experience_feature)
                .selectinload(ExperienceFeatures.feature_flag),
                selectinload(Experiences.targeting_rules)
                .selectinload(TargetingRules.personalisations)
                .selectinload(TargetingRulePersonalisations.personalisation),
                selectinload(Experiences.targeting_rules)
                .selectinload(TargetingRules.segments)
                .selectinload(TargetingRuleSegments.segment),
            )
            .filter(Experiences.pid == pid)
            .first()
        )

    def update_status(self, pid: UUIDType, status: str) -> Optional[Experiences]:
        """Update experience status"""
        experience = self.get_by_pid(pid)

        if experience:
            experience.status = status
            self.db.flush()
            self.db.refresh(experience)

        return experience

    def search_experiences(
        self,
        organisation_id: str,
        app_id: str,
        search_term: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Experiences]:
        """Search experiences by name or description"""
        search_pattern = f"%{search_term}%"

        return (
            self.db.query(Experiences)
            .filter(
                and_(
                    Experiences.organisation_id == organisation_id,
                    Experiences.app_id == app_id,
                    or_(
                        Experiences.name.ilike(search_pattern),
                        Experiences.description.ilike(search_pattern),
                    ),
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def clone_experience(
        self,
        source_pid: UUIDType,
        new_name: str,
        new_description: Optional[str] = None,
    ) -> Optional[Experiences]:
        """Clone an existing experience"""
        source = self.get_with_full_details(source_pid)
        if not source:
            return None

        # Create cloned experience
        cloned_experience = Experiences(
            name=new_name,
            description=new_description or f"Copy of {source.description}",
            status="draft",  # New cloned experiences start as draft
            organisation_id=source.organisation_id,
            app_id=source.app_id,
        )
        self.db.add(cloned_experience)
        self.db.flush()
        self.db.refresh(cloned_experience)

        # TODO: Clone experience segments, personalisations, etc.

        self.db.flush()
        return cloned_experience

    def delete_by_pid(self, pid: UUIDType) -> bool:
        """Delete experience and all related data"""
        experience = self.get_by_pid(pid)
        if not experience:
            return False

        self.db.delete(experience)
        self.db.flush()
        return True


class ExperienceFeaturesCRUD(BaseCRUD):
    def __init__(self, db: Session):
        super().__init__(ExperienceFeatures, db)

    def get_experience_features(self, experience_id: UUIDType):
        return (
            self.db.query(ExperienceFeatures)
            .options(selectinload(ExperienceFeatures.feature_flag))
            .filter(ExperienceFeatures.experience_id == experience_id)
            .all()
        )

    def get_by_experience_and_feature(
        self, experience_id: UUIDType, feature_id: UUIDType
    ) -> Optional[ExperienceFeatures]:
        """Get ExperienceFeature by experience_id and feature_id"""
        return (
            self.db.query(ExperienceFeatures)
            .filter(
                ExperienceFeatures.experience_id == experience_id,
                ExperienceFeatures.feature_id == feature_id,
            )
            .first()
        )


class ExperienceFeatureVariantsCRUD(BaseCRUD):
    def __init__(self, db: Session):
        super().__init__(ExperienceFeatureVariants, db)


class TargetingRulesCRUD(BaseCRUD):
    def __init__(self, db: Session):
        super().__init__(TargetingRules, db)

    def get_experience_targeting_rules(
        self, experience_id: UUIDType
    ) -> List[TargetingRules]:
        """Get all experience segments for an experience"""
        return (
            self.db.query(TargetingRules)
            .filter(TargetingRules.experience_id == experience_id)
            .order_by(TargetingRules.priority)
            .all()
        )

    def create_targeting_rule(
        self,
        experience_id: UUIDType,
        priority: int,
        rule_config: dict,
        rollout_percentage: int,
    ) -> TargetingRules:
        """Create a new experience targeting rule"""
        targeting_rule = TargetingRules(
            experience_id=experience_id,
            priority=priority,
            rule_config=rule_config,
            rollout_percentage=rollout_percentage,
        )

        self.db.add(targeting_rule)
        self.db.flush()
        self.db.refresh(targeting_rule)

        return targeting_rule

    def create_targeting_rule_personalisation(
        self,
        targeting_rule_id: UUIDType,
        personalisation_id: UUIDType,
        target_percentage: int,
    ) -> TargetingRulePersonalisations:
        targeting_rule_personalisation = TargetingRulePersonalisations(
            targeting_rule_id=targeting_rule_id,
            personalisation_id=personalisation_id,
            target_percentage=target_percentage,
        )

        self.db.add(targeting_rule_personalisation)
        self.db.flush()
        self.db.refresh(targeting_rule_personalisation)

        return targeting_rule_personalisation

    def create_targeting_rule_segment(
        self,
        targeting_rule_id: UUIDType,
        segment_id: UUIDType,
        rule_config: dict,
    ) -> TargetingRuleSegments:
        targeting_rule_segment = TargetingRuleSegments(
            targeting_rule_id=targeting_rule_id,
            segment_id=segment_id,
            rule_config=rule_config,
        )

        self.db.add(targeting_rule_segment)
        self.db.flush()
        self.db.refresh(targeting_rule_segment)

        return targeting_rule_segment
