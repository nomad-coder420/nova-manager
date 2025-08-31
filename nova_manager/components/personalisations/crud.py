from typing import Optional, List, Dict, Any
from uuid import UUID as UUIDType
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, asc, desc
from nova_manager.api.personalisations.request_response import PersonalisationUpdate
from datetime import datetime, timezone

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
            is_active=True,  # new personalisations enabled by default
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
        Update an existing personalisation.
        Handles updating, adding, or removing experience variants.
        """
        # Fetch personalisation with related data
        personalisation = self.get_detailed_personalisation(pid)
        if not personalisation:
            return None
            
        # Update basic fields if provided
        if update_dto.name is not None:
            personalisation.name = update_dto.name
        if update_dto.description is not None:
            personalisation.description = update_dto.description
        if update_dto.rule_config is not None:
            personalisation.rule_config = update_dto.rule_config
        if update_dto.rollout_percentage is not None:
            personalisation.rollout_percentage = update_dto.rollout_percentage
        
        # Handle experience variants if provided
        if update_dto.experience_variants is not None:
            # Create dependencies
            experience_variants_crud = ExperienceVariantsCRUD(self.db)
            experience_feature_variants_crud = ExperienceFeatureVariantsCRUD(self.db)
            personalisation_experience_variants_crud = PersonalisationExperienceVariantsCRUD(self.db)
            
            # Get existing variants
            existing_variants = {
                pev.experience_variant.name: pev 
                for pev in personalisation.experience_variants
            }
            
            # Create/update new variants
            for variant_data in update_dto.experience_variants:
                variant_name = variant_data.experience_variant.name
                
                # Check if this variant already exists by name
                existing_variant = experience_variants_crud.get_by_name(
                    name=variant_name,
                    experience_id=personalisation.experience_id
                )
                
                if existing_variant:
                    # Update existing variant
                    existing_variant.description = variant_data.experience_variant.description
                    existing_variant.is_default = variant_data.experience_variant.is_default
                    
                    # Update the personalisation-variant association
                    existing_association = next(
                        (pev for pev in personalisation.experience_variants 
                        if pev.experience_variant.name == variant_name),
                        None
                    )
                    
                    if existing_association:
                        existing_association.target_percentage = variant_data.target_percentage
                    else:
                        # Create new association for existing variant
                        personalisation_experience_variants_crud.create({
                            "personalisation_id": personalisation.pid,
                            "experience_variant_id": existing_variant.pid,
                            "target_percentage": variant_data.target_percentage
                        })
                        
                    # Handle feature variants
                    if variant_data.experience_variant.feature_variants:
                        # Remove existing feature variants
                        experience_feature_variants_crud.delete_all_for_variant(existing_variant.pid)
                        
                        # Create new feature variants
                        for fv in variant_data.experience_variant.feature_variants:
                            experience_feature_variants_crud.create({
                                "experience_variant_id": existing_variant.pid,
                                "experience_feature_id": fv.experience_feature_id,
                                "name": fv.name,
                                "config": fv.config
                            })
                else:
                    # Create new variant and association
                    new_variant = experience_variants_crud.create({
                        "name": variant_name,
                        "description": variant_data.experience_variant.description,
                        "experience_id": personalisation.experience_id,
                        "is_default": variant_data.experience_variant.is_default
                    })

                    personalisation_experience_variants_crud.create({
                        "personalisation_id": personalisation.pid,
                        "experience_variant_id": new_variant.pid,
                        "target_percentage": variant_data.target_percentage
                    })

                    # Create feature variants
                    if variant_data.experience_variant.feature_variants:
                        for fv in variant_data.experience_variant.feature_variants:
                            experience_feature_variants_crud.create({
                                "experience_variant_id": new_variant.pid,
                                "experience_feature_id": fv.experience_feature_id,
                                "name": fv.name,
                                "config": fv.config
                            })

            # Remove variants that are no longer included
            new_variant_names = {v.experience_variant.name for v in update_dto.experience_variants}
            for name, association in existing_variants.items():
                if name not in new_variant_names:
                    self.db.delete(association)
        
    # Handle metrics if provided
        if update_dto.selected_metrics is not None:
            metrics_crud = PersonalisationMetricsCRUD(self.db)
            
            # Remove existing metrics
            metrics_crud.delete_personalisation_metrics(personalisation.pid)

            # Add new metrics
            for metric_id in update_dto.selected_metrics:
                metrics_crud.create({
                    "personalisation_id": personalisation.pid,
                    "metric_id": metric_id
                })
        # If requested, mark existing assignments to be re-evaluated
        if getattr(update_dto, 'apply_to_existing', False):
            personalisation.reassign = True

        # bump last_updated_at when variants or metrics changed
        personalisation.last_updated_at = datetime.now(timezone.utc)

        # Persist updates
        self.db.add(personalisation)
        self.db.commit()
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

