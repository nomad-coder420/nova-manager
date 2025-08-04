from nova_manager.components.personalisations.schemas import PersonalisationResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from nova_manager.database.session import get_db
from fastapi import Depends
from nova_manager.components.auth.dependencies import RoleRequired
from nova_manager.components.auth.enums import AppRole
from nova_manager.api.personalisations.request_response import (
    PersonalisationCreate,
    PersonalisationDetailedResponse,
    PersonalisationListResponse,
)
from nova_manager.components.experiences.crud import (
    ExperiencesCRUD,
    ExperienceVariantsCRUD,
    ExperienceFeatureVariantsCRUD,
)
from nova_manager.components.personalisations.crud import (
    PersonalisationExperienceVariantsCRUD,
    PersonalisationsCRUD,
)
from nova_manager.components.metrics.crud import (
    MetricsCRUD,
    PersonalisationMetricsCRUD,
)
from uuid import UUID


router = APIRouter()


# Personalisation endpoints
@router.post(
    "/create-personalisation/",
    response_model=PersonalisationResponse,
    dependencies=[Depends(RoleRequired([
        AppRole.DEVELOPER, AppRole.ANALYST, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def create_personalisation(
    personalisation_data: PersonalisationCreate,
    db: Session = Depends(get_db),
):
    """Create a new personalisation for an experience"""
    experiences_crud = ExperiencesCRUD(db)
    personalisations_crud = PersonalisationsCRUD(db)
    experience_variants_crud = ExperienceVariantsCRUD(db)
    experience_feature_variants_crud = ExperienceFeatureVariantsCRUD(db)
    personalisation_experience_variants_crud = PersonalisationExperienceVariantsCRUD(db)
    metrics_crud = MetricsCRUD(db)
    personalisation_metrics_crud = PersonalisationMetricsCRUD(db)

    experience_id = personalisation_data.experience_id
    experience_variants = personalisation_data.experience_variants
    selected_metrics = personalisation_data.selected_metrics

    # Validate experience exists
    experience = experiences_crud.get_with_features(experience_id)
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    # Validate metrics exist
    if selected_metrics:
        for metric_id in selected_metrics:
            metric = metrics_crud.get_by_pid(metric_id)
            if not metric:
                raise HTTPException(status_code=404, detail=f"Metric not found: {metric_id}")

    # Check if personalisation name already exists in this experience
    existing = personalisations_crud.get_by_name(
        name=personalisation_data.name,
        experience_id=experience_id,
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Personalisation '{personalisation_data.name}' already exists in this experience",
        )

    # Validate that all feature flags exist and belong to this experience and no duplicate experience feature variants and total percentage is 100
    experience_features = [exp_feature.pid for exp_feature in experience.features]

    default_count = 0
    total_percentage = 0

    for i in experience_variants:
        total_percentage += i.target_percentage

        experience_variant = i.experience_variant

        if experience_variant.is_default:
            default_count += 1
            if default_count > 1:
                raise HTTPException(
                    status_code=400,
                    detail="Only one default personalisation can be assigned per segment",
                )

        elif experience_variant.feature_variants:
            seen_experience_feature_ids = set()

            for feature_variant in experience_variant.feature_variants:
                experience_feature_id = feature_variant.experience_feature_id

                if experience_feature_id not in experience_features:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Experience Feature not found: {experience_feature_id}",
                    )

                if experience_feature_id in seen_experience_feature_ids:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Experience Feature {experience_feature_id} is assigned multiple times",
                    )

                seen_experience_feature_ids.add(feature_variant.experience_feature_id)

        else:
            raise HTTPException(
                status_code=400,
                detail="Each Experience Variant must either have feature_variants or is_default=True",
            )

    if total_percentage != 100:
        raise HTTPException(
            status_code=400,
            detail=f"Experience Variant percentages must sum to 100%, got {total_percentage}%",
        )

    max_priority_personalisation = (
        personalisations_crud.get_experience_max_priority_personalisation(
            experience_id=experience_id
        )
    )

    if max_priority_personalisation:
        next_priority = max_priority_personalisation.priority + 1
    else:
        next_priority = 1

    # Create personalisation with variants
    personalisation = personalisations_crud.create_personalisation(
        experience_id=experience_id,
        organisation_id=experience.organisation_id,
        app_id=experience.app_id,
        name=personalisation_data.name,
        description=personalisation_data.description,
        priority=next_priority,
        rule_config=personalisation_data.rule_config,
        rollout_percentage=personalisation_data.rollout_percentage,
    )

    for i in experience_variants:
        target_percentage = i.target_percentage
        experience_variant = i.experience_variant

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

            for feature_variant in experience_variant.feature_variants:
                experience_feature_variants_crud.create(
                    {
                        "experience_variant_id": experience_variant_obj.pid,
                        "experience_feature_id": feature_variant.experience_feature_id,
                        "name": feature_variant.name,
                        "config": feature_variant.config,
                    }
                )

        personalisation_experience_variants_crud.create(
            {
                "personalisation_id": personalisation.pid,
                "experience_variant_id": experience_variant_obj.pid,
                "target_percentage": target_percentage,
            }
        )

    # Create personalisation metrics associations
    if selected_metrics:
        for metric_id in selected_metrics:
            personalisation_metrics_crud.create_personalisation_metric(
                personalisation_id=personalisation.pid,
                metric_id=metric_id
            )

    return personalisation


@router.get(
    "/",
    response_model=List[PersonalisationListResponse],
    dependencies=[Depends(RoleRequired([
        AppRole.VIEWER, AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
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


@router.get(
    "/personalised-experiences/{experience_id}/",
    response_model=List[PersonalisationDetailedResponse],
    dependencies=[Depends(RoleRequired([
        AppRole.VIEWER, AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def list_personalisations(
    experience_id: UUID,
    db: Session = Depends(get_db),
):
    personalisations_crud = PersonalisationsCRUD(db)

    personalisations = personalisations_crud.get_experience_personalisations(
        experience_id=experience_id,
    )

    return personalisations
