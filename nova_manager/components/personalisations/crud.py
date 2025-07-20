from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID as UUIDType
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, asc, desc

from nova_manager.core.base_crud import BaseCRUD
from nova_manager.components.experiences.models import Experiences
from nova_manager.components.personalisations.models import (
    ExperienceVariants,
    PersonalisationExperienceVariants,
    Personalisations,
)


class PersonalisationsCRUD(BaseCRUD):
    """CRUD operations for Personalisations"""

    def __init__(self, db: Session):
        super().__init__(Personalisations, db)

    def create_personalisation(
        self,
        experience_id: UUIDType,
        organisation_id: str,
        app_id: str,
        name: str,
        description: str,
        priority: int,
        rule_config: dict,
        rollout_percentage: int,
    ) -> Personalisations:
        personalisation = Personalisations(
            experience_id=experience_id,
            organisation_id=organisation_id,
            app_id=app_id,
            name=name,
            description=description,
            priority=priority,
            rule_config=rule_config,
            rollout_percentage=rollout_percentage,
        )

        self.db.add(personalisation)
        self.db.flush()
        self.db.refresh(personalisation)

        return personalisation

    def get_by_name(
        self, name: str, experience_id: UUIDType
    ) -> Optional[Personalisations]:
        """Get personalisation by name within an experience"""
        return (
            self.db.query(Personalisations)
            .filter(
                and_(
                    Personalisations.name == name,
                    Personalisations.experience_id == experience_id,
                )
            )
            .first()
        )

    def search_personalisations(
        self,
        organisation_id: str,
        app_id: Optional[str] = None,
        experience_id: Optional[UUIDType] = None,
        search_term: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Personalisations]:
        """Search personalisations with filters"""
        query = (
            self.db.query(Personalisations)
            .options(selectinload(Personalisations.experience))
            .filter(Personalisations.organisation_id == organisation_id)
        )

        if app_id:
            query = query.filter(Personalisations.app_id == app_id)

        if experience_id:
            query = query.filter(Personalisations.experience_id == experience_id)

        if search_term:
            search_pattern = f"%{search_term}%"
            query = query.filter(
                Personalisations.name.ilike(search_pattern)
                | Personalisations.description.ilike(search_pattern)
            )

        return query.offset(offset).limit(limit).all()

    def get_multi_by_org(
        self,
        organisation_id: str,
        app_id: str,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> List[Personalisations]:
        """Get multiple personalisations by organisation and optionally app"""
        query = (
            self.db.query(Personalisations)
            .options(selectinload(Personalisations.experience))
            .filter(
                Personalisations.organisation_id == organisation_id,
                Personalisations.app_id == app_id,
            )
        )

        # Apply ordering
        order_column = getattr(Personalisations, order_by, Personalisations.created_at)
        if order_direction.lower() == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))

        return query.offset(skip).limit(limit).all()

    def get_experience_personalisations(
        self, experience_id: UUIDType
    ) -> List[Personalisations]:
        """Get all personalisations for an experience"""
        return (
            self.db.query(Personalisations)
            .options(
                selectinload(Personalisations.experience_variants).selectinload(
                    PersonalisationExperienceVariants.experience_variant
                )
            )
            .filter(Personalisations.experience_id == experience_id)
            .all()
        )

    def get_experience_max_priority_personalisation(
        self, experience_id: UUIDType
    ) -> List[Personalisations]:
        """Get the max priority personalisation for an experience"""
        return (
            self.db.query(Personalisations)
            .filter(Personalisations.experience_id == experience_id)
            .order_by(desc(Personalisations.priority))
            .first()
        )


class PersonalisationExperienceVariantsCRUD(BaseCRUD):
    def __init__(self, db: Session):
        super().__init__(PersonalisationExperienceVariants, db)


class ExperienceVariantsCRUD(BaseCRUD):
    """CRUD operations for Personalisations"""

    def __init__(self, db: Session):
        super().__init__(ExperienceVariants, db)

    def get_by_name(
        self, name: str, experience_id: UUIDType
    ) -> Optional[ExperienceVariants]:
        """Get experience variant by name within an experience"""
        return (
            self.db.query(ExperienceVariants)
            .filter(
                and_(
                    ExperienceVariants.name == name,
                    ExperienceVariants.experience_id == experience_id,
                )
            )
            .first()
        )

    def get_default_for_ids(
        self, variant_ids: List[UUIDType]
    ) -> List[ExperienceVariants]:
        """Get Experience Variants by IDs that are marked as default"""
        return (
            self.db.query(ExperienceVariants)
            .filter(
                and_(
                    ExperienceVariants.pid.in_(variant_ids),
                    ExperienceVariants.is_default == True,
                )
            )
            .all()
        )

    def create_experience_variant(
        self,
        experience_id: UUIDType,
        name: str,
        description: str,
        is_default: bool = False,
    ) -> ExperienceVariants:
        """Create an Experience Variant"""

        variant = ExperienceVariants(
            name=name,
            description=description or "",
            experience_id=experience_id or "",
            last_updated_at=datetime.now(timezone.utc),
            is_default=is_default,
        )

        self.db.add(variant)
        self.db.flush()
        self.db.refresh(variant)

        return variant

    def create_default_variant(self, experience_id: UUIDType) -> ExperienceVariants:
        """Create a default variant with all default variants for an experience"""
        # Get experience to find its feature flags
        experience = (
            self.db.query(Experiences).filter(Experiences.pid == experience_id).first()
        )
        if not experience:
            raise ValueError("Experience not found")

        # Generate unique name
        # Get all existing variant names in this experience
        existing_names = set()
        existing_variants = (
            self.db.query(ExperienceVariants)
            .filter(ExperienceVariants.experience_id == experience_id)
            .all()
        )

        for variant in existing_variants:
            existing_names.add(variant.name.lower())

        # Find the next available default personalisation number
        counter = 1
        while True:
            candidate_name = f"Default Experience {counter}"
            if candidate_name.lower() not in existing_names:
                name = candidate_name
                break
            counter += 1

        # Generate description
        description = "Auto-generated default experience"

        # Create variant
        self.create_experience_variant(
            experience_id=experience_id,
            name=name,
            description=description,
            is_default=True,
        )

        return variant
