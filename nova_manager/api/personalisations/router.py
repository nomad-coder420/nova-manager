from nova_manager.components.personalisations.crud import PersonalisationsCRUD
from nova_manager.database.session import get_db
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID as UUIDType
from fastapi import APIRouter, Depends, HTTPException, Query

from nova_manager.api.personalisations.request_response import (
    PersonalisationCreate,
    PersonalisationListResponse,
)
from nova_manager.components.experiences.crud import (
    ExperienceFeatureVariantsCRUD,
    ExperiencesCRUD,
)


router = APIRouter()


# Personalisation endpoints
@router.post("/")
async def create_personalisation(
    personalisation_data: PersonalisationCreate,
    db: Session = Depends(get_db),
):
    """Create a new personalisation for an experience"""
    experiences_crud = ExperiencesCRUD(db)
    personalisations_crud = PersonalisationsCRUD(db)
    experience_feature_variants_crud = ExperienceFeatureVariantsCRUD(db)

    experience_pid = personalisation_data.experience_pid

    # Validate experience exists
    experience = experiences_crud.get_with_features(experience_pid)
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    # Check if personalisation name already exists in this experience
    existing = personalisations_crud.get_by_name(
        name=personalisation_data.name,
        experience_id=experience_pid,
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Personalisation '{personalisation_data.name}' already exists in this experience",
        )

    # Validate that all feature flags exist and belong to this experience
    experience_features = [exp_feature.pid for exp_feature in experience.features]

    for experience_feature_id in personalisation_data.variants:
        if experience_feature_id not in experience_features:
            raise HTTPException(
                status_code=400,
                detail=f"Feature flag not found: {experience_feature_id}",
            )

    # Create personalisation with variants
    personalisation = personalisations_crud.create_personalisation(
        experience_id=experience_pid,
        organisation_id=experience.organisation_id,
        app_id=experience.app_id,
        name=personalisation_data.name,
        description=personalisation_data.description,
    )

    for experience_feature_id in personalisation_data.variants:
        experience_feature_variants_crud.create(
            {
                "personalisation_id": personalisation.pid,
                "experience_feature_id": experience_feature_id,
                "name": personalisation_data.variants[experience_feature_id].name,
                "config": personalisation_data.variants[experience_feature_id].config,
            }
        )

    return {"success": True, "message": "Personalisation created successfully!"}


@router.get("/", response_model=List[PersonalisationListResponse])
async def list_personalisations(
    organisation_id: str = Query(...),
    app_id: str = Query(...),
    search: Optional[str] = Query(
        None, description="Search personalisations by name or description"
    ),
    order_by: str = Query(
        "created_at", description="Order by field (created_at, name, status)"
    ),
    order_direction: str = Query("desc", description="Order direction (asc, desc)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    personalisations_crud = PersonalisationsCRUD(db)

    if search:
        personalisations = personalisations_crud.search_personalisations(
            organisation_id=organisation_id,
            app_id=app_id,
            search_term=search,
            skip=skip,
            limit=limit,
        )
    else:
        personalisations = personalisations_crud.get_multi_by_org(
            organisation_id=organisation_id,
            app_id=app_id,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_direction=order_direction,
        )

    return personalisations
