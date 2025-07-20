from typing import Optional, List, Dict, Any
from uuid import UUID as UUIDType
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, desc, asc

from nova_manager.components.experiences.models import ExperienceFeatures, Experiences
from nova_manager.core.base_crud import BaseCRUD
from nova_manager.components.personalisations.models import (
    ExperienceFeatureVariants,
    ExperienceVariants,
)


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
            .options(
                selectinload(Experiences.features),
                selectinload(Experiences.variants),
            )
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
            .options(
                selectinload(Experiences.features),
                selectinload(Experiences.variants),
            )
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

    def get_with_features(self, pid: UUIDType) -> Optional[Experiences]:
        """Get experience with all experience features loaded"""
        return (
            self.db.query(Experiences)
            .options(selectinload(Experiences.features))
            .filter(Experiences.pid == pid)
            .first()
        )

    def get_with_full_details(self, pid: UUIDType) -> Optional[Experiences]:
        """Get experience with all related data loaded"""
        return (
            self.db.query(Experiences)
            .options(
                # Load feature flags with their variants
                selectinload(Experiences.features).selectinload(
                    ExperienceFeatures.feature_flag
                ),
                # Load feature flags with their variants
                selectinload(Experiences.variants).selectinload(
                    ExperienceVariants.feature_variants
                ),
            )
            .filter(Experiences.pid == pid)
            .first()
        )


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
