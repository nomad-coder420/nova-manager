from typing import List, Optional, Dict, Any
from uuid import UUID as UUIDType
from fastapi import APIRouter, Depends, HTTPException, Query, status
from nova_manager.components.feature_flags.crud import FeatureFlagsCRUD
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from fastapi import Depends
from nova_manager.components.auth.dependencies import RoleRequired
from nova_manager.components.auth.enums import AppRole

from nova_manager.api.experiences.request_response import (
    ExperienceClone,
    ExperienceCreate,
    ExperienceDetailedResponse,
    ExperienceListResponse,
    ExperienceResponse,
    ExperienceStatusUpdate,
    ExperienceUpdate,
    MessageResponse,
    PersonalisationCreate,
    PersonalisationUpdate,
    PersonalisationDetailedResponse,
    PersonalisationListResponse,
    ExperienceSegmentCreate,
)
from nova_manager.components.experiences.crud import (
    ExperiencesCRUD,
    PersonalisationsCRUD,
)
from nova_manager.components.campaigns.crud import CampaignsCRUD
from nova_manager.components.segments.crud import SegmentsCRUD
from nova_manager.database.session import get_db

router = APIRouter()


@router.post(
    "/",
    response_model=ExperienceResponse,
    dependencies=[Depends(RoleRequired([
        AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def create_experience(
    experience_data: ExperienceCreate, db: Session = Depends(get_db)
):
    """Create a new experience with selected feature flags"""
    experiences_crud = ExperiencesCRUD(db)
    feature_flags_crud = FeatureFlagsCRUD(db)

    # Check if name already exists
    existing = experiences_crud.get_by_name(
        name=experience_data.name,
        organisation_id=experience_data.organisation_id,
        app_id=experience_data.app_id,
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Experience '{experience_data.name}' already exists",
        )

        # Validate selected objects exist
    if not experience_data.selected_objects:
        raise HTTPException(
            status_code=400, detail="At least one object must be selected"
        )

    # Get feature flags for validation using CRUD method
    feature_flags = feature_flags_crud.get_flags_by_pids(
        experience_data.selected_objects
    )

    # Check if all requested feature flags exist
    found_flag_ids = {flag.pid: flag for flag in feature_flags}

    for flag_id in experience_data.selected_objects:
        flag = found_flag_ids.get(flag_id)

        if not flag:
            raise HTTPException(
                status_code=400,
                detail=f"Feature flag not found: {flag_id}",
            )

        if flag.experience_id:
            raise HTTPException(
                status_code=400,
                detail=f"Feature flag already assigned to other experience: {flag.pid}",
            )

    # Create experience using CRUD method
    experience = experiences_crud.create(
        {
            "name": experience_data.name,
            "description": experience_data.description,
            "status": experience_data.status,
            "organisation_id": experience_data.organisation_id,
            "app_id": experience_data.app_id,
        }
    )

    # Bulk assign feature flags to experience using CRUD method
    feature_flags_crud.bulk_assign_experience(experience.pid, feature_flags)

    return experience


@router.get(
    "/",
    response_model=List[ExperienceListResponse],
    dependencies=[Depends(RoleRequired([
        AppRole.VIEWER, AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
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
    feature_flags_crud = FeatureFlagsCRUD(db)

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

    # Transform experiences to response format
    result = []
    for experience in experiences:
        # Get feature flags count for this experience
        feature_flags_count = feature_flags_crud.get_feature_flags_count(experience.pid)

        # Get segments count for this experience
        segment_count = experiences_crud.count_experience_segments(experience.pid)

        result.append(
            ExperienceListResponse(
                pid=experience.pid,
                name=experience.name,
                description=experience.description,
                status=experience.status,
                created_at=experience.created_at,
                modified_at=experience.modified_at,
                segment_count=segment_count,
                feature_flags_count=feature_flags_count,
            )
        )

    return result


@router.get(
    "/{experience_pid}/",
    response_model=ExperienceDetailedResponse,
    dependencies=[Depends(RoleRequired([
        AppRole.VIEWER, AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def get_experience(experience_pid: UUIDType, db: Session = Depends(get_db)):
    """Get experience by ID with full details"""
    experiences_crud = ExperiencesCRUD(db)
    experience = experiences_crud.get_with_full_details(experience_pid)

    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    feature_flags = experience.feature_flags
    personalisations = experience.personalisations
    experience_segments = experience.experience_segments

    return ExperienceDetailedResponse(
        pid=experience.pid,
        name=experience.name,
        description=experience.description,
        status=experience.status,
        created_at=experience.created_at,
        modified_at=experience.modified_at,
        feature_flags=feature_flags,
        personalisations=personalisations,
        experience_segments=experience_segments,
        feature_flags_count=len(feature_flags),
        personalisations_count=len(personalisations),
        segments_count=len(experience_segments),
    )


@router.put(
    "/{experience_pid}/",
    response_model=ExperienceResponse,
    dependencies=[Depends(RoleRequired([
        AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def update_experience(
    experience_pid: UUIDType,
    experience_update: ExperienceUpdate,
    db: Session = Depends(get_db),
):
    """Update experience"""
    experiences_crud = ExperiencesCRUD(db)
    experience = experiences_crud.get_by_pid(experience_pid)

    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    # Check name uniqueness if name is being updated
    if experience_update.name and experience_update.name != experience.name:
        existing = experiences_crud.get_by_name(
            name=experience_update.name,
            organisation_id=experience.organisation_id,
            app_id=experience.app_id,
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Experience '{experience_update.name}' already exists",
            )

    # Update other fields
    update_data = experience_update.model_dump(exclude_unset=True)
    if update_data:
        experience = experiences_crud.update(db_obj=experience, obj_in=update_data)

    return experience


@router.put(
    "/{experience_pid}/status/",
    response_model=ExperienceResponse,
    dependencies=[Depends(RoleRequired([
        AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def update_experience_status(
    experience_pid: UUIDType,
    status_update: ExperienceStatusUpdate,
    db: Session = Depends(get_db),
):
    """Update experience status"""
    experiences_crud = ExperiencesCRUD(db)
    experience = experiences_crud.update_status(experience_pid, status_update.status)

    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    return experience


@router.post(
    "/{experience_pid}/clone/",
    response_model=ExperienceResponse,
    dependencies=[Depends(RoleRequired([
        AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def clone_experience(
    experience_pid: UUIDType,
    clone_data: ExperienceClone,
    db: Session = Depends(get_db),
):
    """Clone an existing experience"""
    experiences_crud = ExperiencesCRUD(db)

    # Check if new name already exists
    if clone_data.name:
        # Get original experience to check org/app context
        original = experiences_crud.get_by_pid(experience_pid)
        if not original:
            raise HTTPException(status_code=404, detail="Source experience not found")

        existing = experiences_crud.get_by_name(
            name=clone_data.name,
            organisation_id=original.organisation_id,
            app_id=original.app_id,
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Experience '{clone_data.name}' already exists",
            )

    cloned_experience = experiences_crud.clone_experience(
        source_pid=experience_pid,
        new_name=clone_data.name,
        new_description=clone_data.description,
    )

    if not cloned_experience:
        raise HTTPException(status_code=404, detail="Source experience not found")

    return cloned_experience


# Personalisation endpoints
@router.post(
    "/{experience_pid}/personalisations/",
    response_model=PersonalisationDetailedResponse,
)
async def create_personalisation(
    experience_pid: UUIDType,
    personalisation_data: PersonalisationCreate,
    db: Session = Depends(get_db),
):
    """Create a new personalisation for an experience"""
    experiences_crud = ExperiencesCRUD(db)
    personalisations_crud = PersonalisationsCRUD(db)
    feature_flags_crud = FeatureFlagsCRUD(db)

    # Validate experience exists
    experience = experiences_crud.get_by_pid(experience_pid)
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
    feature_flag_ids = {variant.feature_id for variant in personalisation_data.variants}
    feature_flags = feature_flags_crud.get_flags_by_pids(list(feature_flag_ids))

    # Check if all feature flags exist and belong to this experience
    found_flags = {flag.pid: flag for flag in feature_flags}
    for variant in personalisation_data.variants:
        if variant.feature_id not in found_flags:
            raise HTTPException(
                status_code=400,
                detail=f"Feature flag not found: {variant.feature_id}",
            )

        flag = found_flags[variant.feature_id]
        if flag.experience_id != experience_pid:
            raise HTTPException(
                status_code=400,
                detail=f"Feature flag {variant.feature_id} does not belong to this experience",
            )

    # Create personalisation with variants
    personalisation = personalisations_crud.create_personalisation_with_variants(
        personalisation_data
    )

    return personalisation


@router.get(
    "/{experience_pid}/personalisations/",
    response_model=List[PersonalisationListResponse],
)
async def get_experience_personalisations(
    experience_pid: UUIDType,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get all personalisations for an experience"""
    experiences_crud = ExperiencesCRUD(db)
    personalisations_crud = PersonalisationsCRUD(db)

    # Validate experience exists
    experience = experiences_crud.get_by_pid(experience_pid)
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    personalisations = personalisations_crud.get_by_experience(
        experience_id=experience_pid,
        skip=skip,
        limit=limit,
    )

    # Transform to response format with variants count
    response_personalisations = []
    for personalisation in personalisations:
        response_personalisations.append(
            PersonalisationListResponse(
                pid=personalisation.pid,
                name=personalisation.name,
                description=personalisation.description,
                experience_id=personalisation.experience_id,
                last_updated_at=personalisation.last_updated_at,
                created_at=personalisation.created_at,
                variants_count=len(personalisation.feature_variants),
            )
        )

    return response_personalisations


@router.get(
    "/{experience_pid}/personalisations/{personalisation_pid}/",
    response_model=PersonalisationDetailedResponse,
)
async def get_personalisation(
    experience_pid: UUIDType,
    personalisation_pid: UUIDType,
    db: Session = Depends(get_db),
):
    """Get a specific personalisation with variants"""
    experiences_crud = ExperiencesCRUD(db)
    personalisations_crud = PersonalisationsCRUD(db)

    # Validate experience exists
    experience = experiences_crud.get_by_pid(experience_pid)
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    # Get personalisation with variants
    personalisation = personalisations_crud.get_with_variants(personalisation_pid)
    if not personalisation:
        raise HTTPException(status_code=404, detail="Personalisation not found")

    # Validate personalisation belongs to this experience
    if personalisation.experience_id != experience_pid:
        raise HTTPException(
            status_code=400,
            detail="Personalisation does not belong to this experience",
        )

    return personalisation


@router.put(
    "/{experience_pid}/personalisations/{personalisation_pid}/",
    response_model=PersonalisationDetailedResponse,
)
async def update_personalisation(
    experience_pid: UUIDType,
    personalisation_pid: UUIDType,
    personalisation_data: PersonalisationUpdate,
    db: Session = Depends(get_db),
):
    """Update a personalisation and its variants"""
    experiences_crud = ExperiencesCRUD(db)
    personalisations_crud = PersonalisationsCRUD(db)
    feature_flags_crud = FeatureFlagsCRUD(db)

    # Validate experience exists
    experience = experiences_crud.get_by_pid(experience_pid)
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    # Get existing personalisation
    existing_personalisation = personalisations_crud.get_by_pid(personalisation_pid)
    if not existing_personalisation:
        raise HTTPException(status_code=404, detail="Personalisation not found")

    # Validate personalisation belongs to this experience
    if existing_personalisation.experience_id != experience_pid:
        raise HTTPException(
            status_code=400,
            detail="Personalisation does not belong to this experience",
        )

    # Check if new name already exists (if name is being updated)
    if (
        personalisation_data.name
        and personalisation_data.name != existing_personalisation.name
    ):
        existing = personalisations_crud.get_by_name(
            name=personalisation_data.name,
            experience_id=experience_pid,
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Personalisation '{personalisation_data.name}' already exists in this experience",
            )

    # If variants are being updated, validate them
    if personalisation_data.variants:
        feature_flag_ids = {
            variant.feature_id for variant in personalisation_data.variants
        }
        feature_flags = feature_flags_crud.get_flags_by_pids(list(feature_flag_ids))

        # Check if all feature flags exist and belong to this experience
        found_flags = {flag.pid: flag for flag in feature_flags}
        for variant in personalisation_data.variants:
            if variant.feature_id not in found_flags:
                raise HTTPException(
                    status_code=400,
                    detail=f"Feature flag not found: {variant.feature_id}",
                )

            flag = found_flags[variant.feature_id]
            if flag.experience_id != experience_pid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Feature flag {variant.feature_id} does not belong to this experience",
                )

    # Update personalisation
    update_data = personalisation_data.model_dump(exclude_unset=True)
    variants_data = []
    if personalisation_data.variants:
        variants_data = [
            {
                "feature_id": variant.feature_id,
                "name": variant.name,
                "config": variant.config,
            }
            for variant in personalisation_data.variants
        ]

    personalisation = personalisations_crud.update_personalisation_with_variants(
        pid=personalisation_pid,
        personalisation_data=update_data,
        variants_data=variants_data,
    )

    if not personalisation:
        raise HTTPException(status_code=404, detail="Personalisation not found")

    # Load the personalisation with variants for response
    personalisation_with_variants = personalisations_crud.get_with_variants(
        personalisation.pid
    )
    return personalisation_with_variants


@router.delete("/{experience_pid}/personalisations/{personalisation_pid}/")
async def delete_personalisation(
    experience_pid: UUIDType,
    personalisation_pid: UUIDType,
    db: Session = Depends(get_db),
):
    """Delete a personalisation and its variants"""
    experiences_crud = ExperiencesCRUD(db)
    personalisations_crud = PersonalisationsCRUD(db)

    # Validate experience exists
    experience = experiences_crud.get_by_pid(experience_pid)
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    # Get existing personalisation
    existing_personalisation = personalisations_crud.get_by_pid(personalisation_pid)
    if not existing_personalisation:
        raise HTTPException(status_code=404, detail="Personalisation not found")

    # Validate personalisation belongs to this experience
    if existing_personalisation.experience_id != experience_pid:
        raise HTTPException(
            status_code=400,
            detail="Personalisation does not belong to this experience",
        )

    # Delete personalisation and its variants
    success = personalisations_crud.delete_personalisation_with_variants(
        personalisation_pid
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete personalisation")

    return MessageResponse(message="Personalisation deleted successfully")


# Create experience segment assignment
@router.post("/{experience_pid}/segments/", response_model=MessageResponse)
async def create_experience_segment(
    experience_pid: UUIDType,
    segment_data: ExperienceSegmentCreate,
    db: Session = Depends(get_db),
):
    """Create experience segment assignment with personalisation distribution"""
    experiences_crud = ExperiencesCRUD(db)
    segments_crud = SegmentsCRUD(db)
    personalisations_crud = PersonalisationsCRUD(db)

    # Validate experience exists
    experience = experiences_crud.get_by_pid(experience_pid)
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    # Validate segment exists
    segment = segments_crud.get_by_pid(segment_data.segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    # Validate personalisation percentages sum to 100
    total_percentage = sum(
        item.target_percentage for item in segment_data.personalisation_distribution
    )
    if total_percentage != 100:
        raise HTTPException(
            status_code=400,
            detail=f"Personalisation percentages must sum to 100%, got {total_percentage}%",
        )

    # Validate no duplicate personalisation assignments
    seen_personalisation_ids = set()
    default_count = 0

    for personalisation_item in segment_data.personalisation_distribution:
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

    # Find optimal priority for this experience segment
    existing_segments = experiences_crud.get_experience_segments(experience_pid)
    next_priority = len(existing_segments) + 1

    # Create experience segment
    experience_segment_data = {
        "experience_id": experience_pid,
        "segment_id": segment_data.segment_id,
        "target_percentage": segment_data.target_percentage,
        "priority": next_priority,
    }

    experience_segment = experiences_crud.create_experience_segment(
        experience_segment_data
    )

    # Process personalisation distribution
    for personalisation_item in segment_data.personalisation_distribution:
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

        # Create experience segment personalisation
        experiences_crud.create_experience_segment_personalisation(
            {
                "experience_segment_id": experience_segment.pid,
                "personalisation_id": personalisation_id,
                "target_percentage": personalisation_item.target_percentage,
            }
        )

    return MessageResponse(message="Experience segment created successfully")
