from typing import Optional, List, Dict, Any
from uuid import UUID as UUIDType
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, asc, desc
from nova_manager.api.personalisations.request_response import PersonalisationUpdate

from nova_manager.components.experiences.models import ExperienceVariants
from nova_manager.core.base_crud import BaseCRUD
from nova_manager.components.personalisations.models import (
    PersonalisationExperienceVariants,
    Personalisations,
)
from nova_manager.components.metrics.models import PersonalisationMetrics
from nova_manager.components.metrics.crud import PersonalisationMetricsCRUD
from nova_manager.components.experiences.crud import (
    ExperienceVariantsCRUD,
    ExperienceFeatureVariantsCRUD,
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
                selectinload(Personalisations.experience_variants)
                .selectinload(PersonalisationExperienceVariants.experience_variant)
                .selectinload(ExperienceVariants.feature_variants),
                selectinload(Personalisations.metrics)
                .selectinload(PersonalisationMetrics.metric)
        
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

    def update_personalisation(
        self,
        pid: UUIDType,
        update_dto: PersonalisationUpdate,
    ) -> Personalisations:
        """
        Update an existing personalisation (only new users see changes).
        Does not purge existing user_experience assignments.
        """
        # Fetch and validate
        personalisation = self.get_by_pid(pid)
        if not personalisation:
            raise ValueError(f"Personalisation {pid} not found")

        # Update scalar fields if provided
        for field in ("name", "description", "rule_config", "rollout_percentage"): 
            value = getattr(update_dto, field)
            if value is not None:
                setattr(personalisation, field, value)

        # If variants are provided, create new variants while preserving personalisation link
        if update_dto.experience_variants is not None:
            experience_variants_crud = ExperienceVariantsCRUD(self.db)
            experience_feature_variants_crud = ExperienceFeatureVariantsCRUD(self.db)
            personalisation_experience_variants_crud = PersonalisationExperienceVariantsCRUD(self.db)
            
            # Get experience_id from personalisation
            experience_id = personalisation.experience_id
            
            # Delete old variant links but not the variants themselves
            self.db.query(PersonalisationExperienceVariants).filter(
                PersonalisationExperienceVariants.personalisation_id == pid
            ).delete()
            
            # Process each variant like create flow
            for variant_item in update_dto.experience_variants:
                target_percentage = variant_item.target_percentage
                experience_variant = variant_item.experience_variant
                
                # Create the variant object
                if experience_variant.is_default:
                    experience_variant_obj = experience_variants_crud.create_default_variant(
                        experience_id=experience_id,
                    )
                else:
                    experience_variant_obj = experience_variants_crud.create_experience_variant(
                        experience_id=experience_id,
                        name=experience_variant.name,
                        description=experience_variant.description,
                    )
                    
                    # Create feature variants if specified
                    if experience_variant.feature_variants:
                        for feature_variant in experience_variant.feature_variants:
                            experience_feature_variants_crud.create({
                                "experience_variant_id": experience_variant_obj.pid,
                                "experience_feature_id": feature_variant.experience_feature_id,
                                "name": feature_variant.name,
                                "config": feature_variant.config,
                            })
                
                # Link the new variant to the personalisation
                personalisation_experience_variants_crud.create({
                    "personalisation_id": pid,
                    "experience_variant_id": experience_variant_obj.pid,
                    "target_percentage": target_percentage,
                })

        # Metrics update if provided
        if update_dto.selected_metrics is not None:
            
            metrics_crud = PersonalisationMetricsCRUD(self.db)
            # remove old
            metrics_crud.delete_personalisation_metrics(pid)
            # add new
            for m_id in update_dto.selected_metrics:
                metrics_crud.create_personalisation_metric(pid, m_id)

        self.db.flush()
        self.db.refresh(personalisation)
        return personalisation
    
    def get_detailed_personalisation(
    self, pid: UUIDType
    ) -> Optional[Personalisations]:
        """Get a personalisation by ID with all its relationships loaded"""
        return (
            self.db.query(Personalisations)
            .options(
                selectinload(Personalisations.experience),
                selectinload(Personalisations.experience_variants)
                .selectinload(PersonalisationExperienceVariants.experience_variant)
                .selectinload(ExperienceVariants.feature_variants),
                selectinload(Personalisations.metrics)
                .selectinload(PersonalisationMetrics.metric)
            )
            .filter(Personalisations.pid == pid)
            .first()
    )


class PersonalisationExperienceVariantsCRUD(BaseCRUD):
    def __init__(self, db: Session):
        super().__init__(PersonalisationExperienceVariants, db)

