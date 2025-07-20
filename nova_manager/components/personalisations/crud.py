from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID as UUIDType
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, desc, asc

from nova_manager.core.base_crud import BaseCRUD
from nova_manager.components.experiences.models import Experiences
from nova_manager.components.personalisations.models import (
    ExperienceFeatureVariants,
    Personalisations,
)


class PersonalisationsCRUD(BaseCRUD):
    """CRUD operations for Personalisations"""

    def __init__(self, db: Session):
        super().__init__(Personalisations, db)

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

    def get_by_experience(
        self, experience_id: UUIDType, skip: int = 0, limit: int = 100
    ) -> List[Personalisations]:
        """Get personalisations for a specific experience"""
        return (
            self.db.query(Personalisations)
            .filter(Personalisations.experience_id == experience_id)
            .options(
                selectinload(Personalisations.variants).selectinload(
                    ExperienceFeatureVariants.personalisation
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_with_variants(self, pid: UUIDType) -> Optional[Personalisations]:
        """Get personalisation with all its variants"""
        return (
            self.db.query(Personalisations)
            .options(
                selectinload(Personalisations.variants).selectinload(
                    ExperienceFeatureVariants.personalisation
                )
            )
            .filter(Personalisations.pid == pid)
            .first()
        )

    def get_default_personalisations_by_ids(
        self, personalisation_ids: List[UUIDType]
    ) -> List[Personalisations]:
        """Get personalisations by IDs that are marked as default"""
        return (
            self.db.query(Personalisations)
            .filter(
                and_(
                    Personalisations.pid.in_(personalisation_ids),
                    Personalisations.is_default == True,
                )
            )
            .all()
        )

    def create_personalisation(
        self,
        experience_id: UUIDType,
        organisation_id: str,
        app_id: str,
        name: str,
        description: str,
        is_default: bool = False,
    ) -> Personalisations:
        """Create a personalisation with its variants"""
        # Create personalisation
        personalisation = Personalisations(
            name=name,
            description=description or "",
            experience_id=experience_id or "",
            last_updated_at=datetime.now(timezone.utc),
            organisation_id=organisation_id,
            app_id=app_id,
            is_default=is_default,
        )

        self.db.add(personalisation)
        self.db.flush()
        self.db.refresh(personalisation)

        return personalisation

    def get_multi_by_org(
        self,
        organisation_id: str,
        app_id: str,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> List[Personalisations]:
        """Get personalisations for organization/app with pagination and filtering"""
        query = (
            self.db.query(Personalisations)
            .options(selectinload(Personalisations.experience))
            .filter(
                and_(
                    Personalisations.organisation_id == organisation_id,
                    Personalisations.app_id == app_id,
                )
            )
        )

        # Apply ordering
        order_column = getattr(Personalisations, order_by, Personalisations.created_at)

        if order_direction.lower() == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))

        return query.offset(skip).limit(limit).all()

    def search_personalisations(
        self,
        organisation_id: str,
        app_id: str,
        search_term: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Personalisations]:
        """Search personalisations by name or description"""
        search_pattern = f"%{search_term}%"

        return (
            self.db.query(Personalisations)
            .filter(
                and_(
                    Personalisations.organisation_id == organisation_id,
                    Personalisations.app_id == app_id,
                    or_(
                        Personalisations.name.ilike(search_pattern),
                        Personalisations.description.ilike(search_pattern),
                    ),
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def delete_personalisation_with_variants(self, pid: UUIDType) -> bool:
        """Delete a personalisation and all its variants"""
        personalisation = self.get_by_pid(pid)
        if not personalisation:
            return False

        # Delete junction table entries first
        self.db.query(ExperienceFeatureVariants).filter(
            ExperienceFeatureVariants.personalisation_id == pid
        ).delete()

        # Delete personalisation
        self.db.delete(personalisation)
        self.db.flush()
        return True

    def create_default_personalisation(
        self, experience_id: UUIDType
    ) -> Personalisations:
        """Create a default personalisation with all default variants for an experience"""
        # Get experience to find its feature flags
        experience = (
            self.db.query(Experiences).filter(Experiences.pid == experience_id).first()
        )
        if not experience:
            raise ValueError("Experience not found")

        # Generate unique name
        # Get all existing personalisation names in this experience
        existing_names = set()
        existing_personalisations = (
            self.db.query(Personalisations)
            .filter(Personalisations.experience_id == experience_id)
            .all()
        )

        for personalisation in existing_personalisations:
            existing_names.add(personalisation.name.lower())

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

        # Create personalisation
        self.create_personalisation(
            experience_id=experience_id,
            organisation_id=experience.organisation_id,
            app_id=experience.app_id,
            name=name,
            description=description,
            is_default=True,
        )

        return personalisation

    def count_by_experience(self, experience_id: UUIDType) -> int:
        """Count personalisations for a specific experience"""
        return (
            self.db.query(Personalisations)
            .filter(Personalisations.experience_id == experience_id)
            .count()
        )
