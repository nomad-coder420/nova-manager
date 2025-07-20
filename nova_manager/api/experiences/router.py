from nova_manager.components.personalisations.crud import PersonalisationsCRUD
from typing import List, Optional, Dict, Any
from uuid import UUID as UUIDType
from fastapi import APIRouter, Depends, HTTPException, Query, status
from nova_manager.components.feature_flags.crud import FeatureFlagsCRUD
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from nova_manager.api.experiences.request_response import (
    ExperienceDetailedResponse,
    ExperienceFeatureResponse,
    ExperienceListResponse,
    ExperienceTargetingRuleCreate,
    GetExperienceResponse,
    MessageResponse,
)
from nova_manager.components.experiences.crud import (
    ExperienceFeaturesCRUD,
    ExperiencesCRUD,
    TargetingRulesCRUD,
)
from nova_manager.database.session import get_db

router = APIRouter()


@router.get("/", response_model=List[ExperienceListResponse])
async def list_experiences(
    organisation_id: str = Query(...),
    app_id: str = Query(...),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(
        None, description="Search experiences by name or description"
    ),
    order_by: str = Query(
        "created_at", description="Order by field (created_at, name, status)"
    ),
    order_direction: str = Query("desc", description="Order direction (asc, desc)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List experiences with filtering, search, and pagination"""
    experiences_crud = ExperiencesCRUD(db)

    if search:
        experiences = experiences_crud.search_experiences(
            organisation_id=organisation_id,
            app_id=app_id,
            search_term=search,
            skip=skip,
            limit=limit,
        )
    else:
        experiences = experiences_crud.get_multi_by_org(
            organisation_id=organisation_id,
            app_id=app_id,
            skip=skip,
            limit=limit,
            status=status,
            order_by=order_by,
            order_direction=order_direction,
        )

    return experiences


@router.get("/{experience_pid}/", response_model=GetExperienceResponse)
async def get_experience(experience_pid: UUIDType, db: Session = Depends(get_db)):
    """Get experience by ID with full details"""
    experiences_crud = ExperiencesCRUD(db)
    experience = experiences_crud.get_with_feature_flag_variants(experience_pid)

    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    return experience


@router.get(
    "/{experience_pid}/features/", response_model=List[ExperienceFeatureResponse]
)
async def get_experience_features(
    experience_pid: UUIDType, db: Session = Depends(get_db)
):
    """Get features for a specific experience"""
    experience_features_crud = ExperienceFeaturesCRUD(db)

    # Get experience with feature flags
    experience_features = experience_features_crud.get_experience_features(
        experience_pid
    )

    return experience_features


@router.get(
    "/{experience_pid}/personalisations/", response_model=ExperienceDetailedResponse
)
async def get_experience_personalisations(
    experience_pid: UUIDType, db: Session = Depends(get_db)
):
    """Get experience by ID with full details"""
    experiences_crud = ExperiencesCRUD(db)
    experience = experiences_crud.get_with_personalisations_data(experience_pid)

    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    return experience


# Create experience targeting rule
@router.post("/{experience_pid}/targeting-rules/", response_model=MessageResponse)
async def create_experience_targeting_rule(
    experience_pid: UUIDType,
    targeting_rule_data: ExperienceTargetingRuleCreate,
    db: Session = Depends(get_db),
):
    """Create experience targeting rule with personalisation distribution"""
    experiences_crud = ExperiencesCRUD(db)
    personalisations_crud = PersonalisationsCRUD(db)
    targeting_rules_crud = TargetingRulesCRUD(db)

    # Validate experience exists
    experience = experiences_crud.get_by_pid(experience_pid)
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    # Validate personalisation percentages sum to 100
    total_percentage = sum(
        item.target_percentage for item in targeting_rule_data.personalisations
    )
    if total_percentage != 100:
        raise HTTPException(
            status_code=400,
            detail=f"Personalisation percentages must sum to 100%, got {total_percentage}%",
        )

    # Validate no duplicate personalisation assignments
    seen_personalisation_ids = set()
    default_count = 0

    for personalisation_item in targeting_rule_data.personalisations:
        if personalisation_item.use_default:
            default_count += 1
            if default_count > 1:
                raise HTTPException(
                    status_code=400,
                    detail="Only one default personalisation can be assigned per segment",
                )
        elif personalisation_item.personalisation_id:
            if personalisation_item.personalisation_id in seen_personalisation_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Personalisation {personalisation_item.personalisation_id} is assigned multiple times",
                )
            seen_personalisation_ids.add(personalisation_item.personalisation_id)
        else:
            raise HTTPException(
                status_code=400,
                detail="Each personalisation must either have personalisation_id or use_default=True",
            )

    # Check if any of the regular personalisation assignments are actually default personalisations
    if seen_personalisation_ids:
        default_personalisations = (
            personalisations_crud.get_default_personalisations_by_ids(
                list(seen_personalisation_ids)
            )
        )
        if default_personalisations:
            default_names = [p.name for p in default_personalisations]
            raise HTTPException(
                status_code=400,
                detail=f"Default personalisations cannot be assigned as regular personalisations: {', '.join(default_names)}. Use 'use_default=True' instead.",
            )

    # Find priority for this experience targeting rule
    existing_targeting_rules = targeting_rules_crud.get_experience_targeting_rules(
        experience_pid
    )
    next_priority = len(existing_targeting_rules) + 1

    # Create targeting rule
    targeting_rule = targeting_rules_crud.create_targeting_rule(
        experience_pid,
        next_priority,
        targeting_rule_data.rule_config,
        targeting_rule_data.rollout_percentage,
    )

    # Process personalisation distribution
    for personalisation_item in targeting_rule_data.personalisations:
        personalisation_id = personalisation_item.personalisation_id

        # Handle default personalisation
        if personalisation_item.use_default:
            # Create default personalisation with all default variants
            default_personalisation = (
                personalisations_crud.create_default_personalisation(
                    experience_id=experience_pid
                )
            )
            personalisation_id = default_personalisation.pid

        # Create targeting rule personalisation
        targeting_rules_crud.create_targeting_rule_personalisation(
            targeting_rule_id=targeting_rule.pid,
            personalisation_id=personalisation_id,
            target_percentage=personalisation_item.target_percentage,
        )

    for segment_item in targeting_rule_data.segments:
        targeting_rules_crud.create_targeting_rule_segment(
            targeting_rule_id=targeting_rule.pid,
            segment_id=segment_item.segment_id,
            rule_config=segment_item.rule_config,
        )

    return {"message": "Experience targeting rule created successfully"}
