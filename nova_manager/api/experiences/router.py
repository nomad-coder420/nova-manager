from typing import List, Optional
from uuid import UUID as UUIDType
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from nova_manager.api.experiences.request_response import (
    ExperienceCreate,
    ExperienceComprehensiveCreate,
    ExperienceUpdate,
    ExperiencePriorityUpdate,
    ExperienceStatusUpdate,
    ExperienceClone,
    ExperienceSegmentCreate,
    ExperienceSegmentUpdate,
    ExperienceSegmentBulkUpdate,
    ExperienceResponse,
    ExperienceListResponse,
    ExperienceDetailedResponse,
    ExperienceStatsResponse,
    ExperienceSegmentResponse,
    ExperienceSegmentUsageResponse,
    MessageResponse,
    SegmentResponse,
    FeatureVariantResponse,
)
from nova_manager.components.experiences.crud import ExperiencesCRUD, ExperienceSegmentsCRUD
from nova_manager.components.segments.crud import SegmentsCRUD
from nova_manager.components.feature_flags.crud import FeatureFlagsCRUD, FeatureVariantsCRUD
from nova_manager.database.session import get_db

router = APIRouter()


@router.post("/", response_model=ExperienceResponse)
async def create_experience(
    experience_data: ExperienceCreate, db: Session = Depends(get_db)
):
    """Create a new experience"""
    try:
        experiences_crud = ExperiencesCRUD(db)

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

        # Check if priority is already taken
        existing_priority = experiences_crud.get_by_priority(
            priority=experience_data.priority,
            organisation_id=experience_data.organisation_id,
            app_id=experience_data.app_id,
        )
        if existing_priority:
            raise HTTPException(
                status_code=400,
                detail=f"Priority {experience_data.priority} is already taken. Use a different priority or update the existing experience.",
            )

        # Create experience
        experience = experiences_crud.create_experience(
            name=experience_data.name,
            description=experience_data.description,
            priority=experience_data.priority,
            status=experience_data.status,
            organisation_id=experience_data.organisation_id,
            app_id=experience_data.app_id,
        )

        return experience

    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Experience with this name already exists"
        )


@router.post("/comprehensive", response_model=ExperienceResponse)
async def create_experience_comprehensive(
    experience_data: ExperienceComprehensiveCreate, db: Session = Depends(get_db)
):
    """Create a new experience with variants and segments in one operation"""
    try:
        experiences_crud = ExperiencesCRUD(db)
        experience_segments_crud = ExperienceSegmentsCRUD(db)
        feature_flags_crud = FeatureFlagsCRUD(db)
        feature_variants_crud = FeatureVariantsCRUD(db)
        segments_crud = SegmentsCRUD(db)

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

        # Handle priority - if null, get highest priority + 1
        priority = experience_data.priority
        if priority is None:
            experiences = experiences_crud.get_multi_by_org(
                organisation_id=experience_data.organisation_id,
                app_id=experience_data.app_id,
                skip=0,
                limit=1,
                order_by="priority",
                order_direction="desc",
            )
            max_priority = experiences[0].priority if experiences else 0
            priority = max_priority + 1
        else:
            # Check if priority is already taken
            existing_priority = experiences_crud.get_by_priority(
                priority=priority,
                organisation_id=experience_data.organisation_id,
                app_id=experience_data.app_id,
            )
            if existing_priority:
                raise HTTPException(
                    status_code=400,
                    detail=f"Priority {priority} is already taken. Use a different priority or let the system auto-assign.",
                )

        # Create the experience
        experience = experiences_crud.create_experience(
            name=experience_data.name,
            description=experience_data.description,
            priority=priority,
            status=experience_data.status,
            organisation_id=experience_data.organisation_id,
            app_id=experience_data.app_id,
        )

        # Create feature variants for each selected object
        created_variants = []
        for object_id in experience_data.selected_objects:
            # Validate that the feature flag exists
            feature_flag = feature_flags_crud.get_by_pid(object_id)
            if not feature_flag:
                raise HTTPException(
                    status_code=400,
                    detail=f"Feature flag {object_id} not found",
                )

            # Get variant for this object (now single variant)
            object_variant = experience_data.object_variants.get(object_id)
            if object_variant:
                # Create variant
                variant_data = {
                    "experience_id": experience.pid,
                    "name": object_variant.name,
                    "config": object_variant.values,
                }
                
                variant = feature_variants_crud.create_variant(
                    feature_pid=object_id,
                    variant_data=variant_data
                )
                created_variants.append(variant)

        # Associate segments with the experience
        associated_segments = []
        if experience_data.selected_segments:
            for segment_input in experience_data.selected_segments:
                # Validate that the segment exists
                segment = segments_crud.get_by_pid(segment_input.segment_id)
                if not segment:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Segment {segment_input.segment_id} not found",
                    )

                # Add segment to experience
                exp_segment = experience_segments_crud.add_segment_to_experience(
                    experience_id=experience.pid,
                    segment_id=segment_input.segment_id,
                    target_percentage=segment_input.target_percentage,
                )
                associated_segments.append(exp_segment)

        # Commit all changes
        db.commit()

        return experience

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="Experience with this name already exists"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to create experience: {str(e)}"
        )


@router.get("/", response_model=List[ExperienceListResponse])
async def list_experiences(
    organisation_id: str = Query(...),
    app_id: str = Query(...),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(
        None, description="Search experiences by name or description"
    ),
    order_by: str = Query(
        "created_at", description="Order by field (created_at, priority, name, status)"
    ),
    order_direction: str = Query(
        "desc", description="Order direction (asc, desc)"
    ),
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

    # Add counts to each experience
    result = []
    for experience in experiences:
        # Get segments count
        experience_segments_crud = ExperienceSegmentsCRUD(db)
        segments = experience_segments_crud.get_by_experience(experience.pid)
        segment_count = len(segments)

        # Get feature variants count (assuming relationship exists)
        feature_variant_count = len(experience.feature_variants) if hasattr(experience, 'feature_variants') else 0

        result.append(
            ExperienceListResponse(
                pid=experience.pid,
                name=experience.name,
                description=experience.description,
                priority=experience.priority,
                status=experience.status,
                organisation_id=experience.organisation_id,
                app_id=experience.app_id,
                created_at=experience.created_at,
                modified_at=experience.modified_at,
                last_updated_at=experience.last_updated_at,
                segment_count=segment_count,
                feature_variant_count=feature_variant_count,
            )
        )

    return result


@router.get("/active", response_model=List[ExperienceListResponse])
async def list_active_experiences(
    organisation_id: str = Query(...),
    app_id: str = Query(...),
    db: Session = Depends(get_db),
):
    """List active experiences ordered by priority"""
    experiences_crud = ExperiencesCRUD(db)
    experiences = experiences_crud.get_active_experiences(
        organisation_id=organisation_id, app_id=app_id
    )

    # Add counts to each experience
    result = []
    for experience in experiences:
        experience_segments_crud = ExperienceSegmentsCRUD(db)
        segments = experience_segments_crud.get_by_experience(experience.pid)
        segment_count = len(segments)

        feature_variant_count = len(experience.feature_variants) if hasattr(experience, 'feature_variants') else 0

        result.append(
            ExperienceListResponse(
                pid=experience.pid,
                name=experience.name,
                description=experience.description,
                priority=experience.priority,
                status=experience.status,
                organisation_id=experience.organisation_id,
                app_id=experience.app_id,
                created_at=experience.created_at,
                modified_at=experience.modified_at,
                last_updated_at=experience.last_updated_at,
                segment_count=segment_count,
                feature_variant_count=feature_variant_count,
            )
        )

    return result


@router.get("/{experience_pid}/", response_model=ExperienceDetailedResponse)
async def get_experience(experience_pid: UUIDType, db: Session = Depends(get_db)):
    """Get experience by ID with full details"""
    experiences_crud = ExperiencesCRUD(db)
    experience = experiences_crud.get_with_full_details(experience_pid)
    
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    # Transform segments data
    segments = []
    for exp_seg in experience.experience_segments:
        if exp_seg.segment:
            segments.append(
                SegmentResponse(
                    pid=exp_seg.segment.pid,
                    name=exp_seg.segment.name,
                    description=exp_seg.segment.description,
                    rule_config=exp_seg.segment.rule_config,
                    target_percentage=exp_seg.target_percentage,
                    created_at=exp_seg.segment.created_at,
                )
            )

    # Transform feature variants data
    feature_variants = []
    for variant in experience.feature_variants:
        feature_variants.append(
            FeatureVariantResponse(
                pid=variant.pid,
                name=variant.name,
                config=variant.config,
                created_at=variant.created_at,
            )
        )

    return ExperienceDetailedResponse(
        pid=experience.pid,
        name=experience.name,
        description=experience.description,
        priority=experience.priority,
        status=experience.status,
        organisation_id=experience.organisation_id,
        app_id=experience.app_id,
        created_at=experience.created_at,
        modified_at=experience.modified_at,
        last_updated_at=experience.last_updated_at,
        segments=segments,
        feature_variants=feature_variants,
        segment_count=len(segments),
        feature_variant_count=len(feature_variants),
        user_experience_count=len(experience.user_experiences),
    )


@router.put("/{experience_pid}/", response_model=ExperienceResponse)
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

    # Handle priority update separately if provided
    if experience_update.priority is not None:
        updated_experience = experiences_crud.update_priority(
            experience_pid, experience_update.priority
        )
        if not updated_experience:
            raise HTTPException(status_code=404, detail="Experience not found")
    
    # Update other fields
    update_data = experience_update.dict(exclude_unset=True, exclude={'priority'})
    if update_data:
        experience = experiences_crud.update(db_obj=experience, obj_in=update_data)

    return experience


@router.put("/{experience_pid}/priority", response_model=ExperienceResponse)
async def update_experience_priority(
    experience_pid: UUIDType,
    priority_update: ExperiencePriorityUpdate,
    db: Session = Depends(get_db),
):
    """Update experience priority"""
    experiences_crud = ExperiencesCRUD(db)
    experience = experiences_crud.update_priority(
        experience_pid, priority_update.priority
    )
    
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    return experience


@router.put("/{experience_pid}/status", response_model=ExperienceResponse)
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


@router.post("/{experience_pid}/clone", response_model=ExperienceResponse)
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
        new_priority=clone_data.priority,
    )
    
    if not cloned_experience:
        raise HTTPException(status_code=404, detail="Source experience not found")

    return cloned_experience


@router.delete("/{experience_pid}/")
async def delete_experience(
    experience_pid: UUIDType,
    force: bool = Query(False, description="Force delete even if has active segments"),
    db: Session = Depends(get_db),
):
    """Delete experience"""
    experiences_crud = ExperiencesCRUD(db)
    experience = experiences_crud.get_by_pid(experience_pid)
    
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    # Check if experience has segments and is not force delete
    if not force:
        experience_segments_crud = ExperienceSegmentsCRUD(db)
        segments = experience_segments_crud.get_by_experience(experience_pid)
        if segments:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete experience. It has {len(segments)} segment(s) assigned. Use force=true to delete anyway.",
            )

    experiences_crud.delete_by_pid(pid=experience_pid)
    return MessageResponse(message="Experience deleted successfully")


@router.get("/{experience_pid}/stats", response_model=ExperienceStatsResponse)
async def get_experience_stats(
    experience_pid: UUIDType, db: Session = Depends(get_db)
):
    """Get experience statistics"""
    experiences_crud = ExperiencesCRUD(db)
    stats = experiences_crud.get_experience_stats(experience_pid)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Experience not found")

    return ExperienceStatsResponse(**stats)


# Experience Segments Management
@router.get("/{experience_pid}/segments", response_model=List[ExperienceSegmentResponse])
async def get_experience_segments(
    experience_pid: UUIDType, db: Session = Depends(get_db)
):
    """Get all segments for an experience"""
    experiences_crud = ExperiencesCRUD(db)
    experience = experiences_crud.get_by_pid(experience_pid)
    
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    experience_segments_crud = ExperienceSegmentsCRUD(db)
    segments = experience_segments_crud.get_by_experience(experience_pid)

    result = []
    for exp_seg in segments:
        result.append(
            ExperienceSegmentResponse(
                pid=exp_seg.pid,
                experience_id=exp_seg.experience_id,
                segment_id=exp_seg.segment_id,
                segment_name=exp_seg.segment.name if exp_seg.segment else "Unknown",
                segment_description=exp_seg.segment.description if exp_seg.segment else "",
                target_percentage=exp_seg.target_percentage,
                created_at=exp_seg.created_at,
            )
        )

    return result


@router.post("/{experience_pid}/segments", response_model=ExperienceSegmentResponse)
async def add_segment_to_experience(
    experience_pid: UUIDType,
    segment_data: ExperienceSegmentCreate,
    db: Session = Depends(get_db),
):
    """Add a segment to an experience"""
    experiences_crud = ExperiencesCRUD(db)
    segments_crud = SegmentsCRUD(db)
    experience_segments_crud = ExperienceSegmentsCRUD(db)

    # Check if experience exists
    experience = experiences_crud.get_by_pid(experience_pid)
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    # Check if segment exists
    segment = segments_crud.get_by_pid(segment_data.segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    # Add segment to experience
    exp_segment = experience_segments_crud.add_segment_to_experience(
        experience_id=experience_pid,
        segment_id=segment_data.segment_id,
        target_percentage=segment_data.target_percentage,
    )

    return ExperienceSegmentResponse(
        pid=exp_segment.pid,
        experience_id=exp_segment.experience_id,
        segment_id=exp_segment.segment_id,
        segment_name=segment.name,
        segment_description=segment.description,
        target_percentage=exp_segment.target_percentage,
        created_at=exp_segment.created_at,
    )


@router.put("/{experience_pid}/segments/{segment_id}", response_model=ExperienceSegmentResponse)
async def update_experience_segment(
    experience_pid: UUIDType,
    segment_id: UUIDType,
    segment_update: ExperienceSegmentUpdate,
    db: Session = Depends(get_db),
):
    """Update target percentage for an experience segment"""
    experience_segments_crud = ExperienceSegmentsCRUD(db)
    segments_crud = SegmentsCRUD(db)

    # Update the segment
    exp_segment = experience_segments_crud.update_target_percentage(
        experience_id=experience_pid,
        segment_id=segment_id,
        target_percentage=segment_update.target_percentage,
    )

    if not exp_segment:
        raise HTTPException(status_code=404, detail="Experience segment not found")

    # Get segment details
    segment = segments_crud.get_by_pid(segment_id)

    return ExperienceSegmentResponse(
        pid=exp_segment.pid,
        experience_id=exp_segment.experience_id,
        segment_id=exp_segment.segment_id,
        segment_name=segment.name if segment else "Unknown",
        segment_description=segment.description if segment else "",
        target_percentage=exp_segment.target_percentage,
        created_at=exp_segment.created_at,
    )


@router.delete("/{experience_pid}/segments/{segment_id}")
async def remove_segment_from_experience(
    experience_pid: UUIDType,
    segment_id: UUIDType,
    db: Session = Depends(get_db),
):
    """Remove a segment from an experience"""
    experience_segments_crud = ExperienceSegmentsCRUD(db)
    
    success = experience_segments_crud.remove_segment_from_experience(
        experience_id=experience_pid, segment_id=segment_id
    )

    if not success:
        raise HTTPException(status_code=404, detail="Experience segment not found")

    return MessageResponse(message="Segment removed from experience successfully")


@router.put("/{experience_pid}/segments", response_model=List[ExperienceSegmentResponse])
async def bulk_update_experience_segments(
    experience_pid: UUIDType,
    segments_data: ExperienceSegmentBulkUpdate,
    db: Session = Depends(get_db),
):
    """Bulk update segments for an experience"""
    experiences_crud = ExperiencesCRUD(db)
    segments_crud = SegmentsCRUD(db)
    experience_segments_crud = ExperienceSegmentsCRUD(db)

    # Check if experience exists
    experience = experiences_crud.get_by_pid(experience_pid)
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    # Validate all segments exist
    for segment_config in segments_data.segments:
        segment = segments_crud.get_by_pid(segment_config.segment_id)
        if not segment:
            raise HTTPException(
                status_code=404, 
                detail=f"Segment {segment_config.segment_id} not found"
            )

    # Bulk update segments
    segment_configs = [
        {
            "segment_id": seg.segment_id,
            "target_percentage": seg.target_percentage,
        }
        for seg in segments_data.segments
    ]

    updated_segments = experience_segments_crud.bulk_update_segments(
        experience_id=experience_pid, segment_configs=segment_configs
    )

    # Return formatted response
    result = []
    for exp_seg in updated_segments:
        segment = segments_crud.get_by_pid(exp_seg.segment_id)
        result.append(
            ExperienceSegmentResponse(
                pid=exp_seg.pid,
                experience_id=exp_seg.experience_id,
                segment_id=exp_seg.segment_id,
                segment_name=segment.name if segment else "Unknown",
                segment_description=segment.description if segment else "",
                target_percentage=exp_seg.target_percentage,
                created_at=exp_seg.created_at,
            )
        )

    return result


@router.get("/segments/{segment_id}/usage", response_model=List[ExperienceSegmentUsageResponse])
async def get_segment_usage_in_experiences(
    segment_id: UUIDType, db: Session = Depends(get_db)
):
    """Get usage of a segment across experiences"""
    segments_crud = SegmentsCRUD(db)
    experience_segments_crud = ExperienceSegmentsCRUD(db)

    # Check if segment exists
    segment = segments_crud.get_by_pid(segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    usage = experience_segments_crud.get_segment_usage_in_experience(segment_id)
    
    return [ExperienceSegmentUsageResponse(**usage_item) for usage_item in usage] 