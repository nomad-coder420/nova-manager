from typing import List, Optional
from uuid import UUID as UUIDType
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from nova_manager.api.experiences.request_response import (
    ExperienceCreate,
    CreateNewExperienceRequest,
    ExperienceUpdate,
    ExperiencePriorityUpdate,
    ExperienceStatusUpdate,
    ExperienceClone,
    ExperienceResponse,
    ExperienceListResponse,
    ExperienceDetailedResponse,
    MessageResponse,
    SegmentResponse,
    FeatureVariantResponse,
    CampaignResponse,
)
from nova_manager.components.experiences.crud import (
    ExperiencesCRUD,
    ExperienceSegmentsCRUD,
)
from nova_manager.components.campaigns.crud import CampaignsCRUD
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


@router.post("/create-new-experience/", response_model=ExperienceResponse)
async def create_new_experience(
    experience_data: CreateNewExperienceRequest, db: Session = Depends(get_db)
):
    """Create a new experience with variants, segments, and campaign"""
    try:
        # Initialize CRUD instances
        experiences_crud = ExperiencesCRUD(db)
        campaigns_crud = CampaignsCRUD(db)
        
        # Validate request data
        if not experience_data.campaign_id and not experience_data.new_campaign:
            raise HTTPException(
                status_code=400,
                detail="Either campaign_id or new_campaign must be provided"
            )
        
        if experience_data.campaign_id and experience_data.new_campaign:
            raise HTTPException(
                status_code=400,
                detail="Cannot provide both campaign_id and new_campaign"
            )
        
        # Extract selected objects from object_variants keys
        selected_objects = list(experience_data.object_variants.keys())
        
        if not selected_objects:
            raise HTTPException(
                status_code=400,
                detail="At least one object variant must be provided"
            )
        
        # Bulk validate feature flags existence
        feature_flag_validation = experiences_crud.bulk_validate_feature_flags(selected_objects)
        invalid_flags = [flag_id for flag_id, exists in feature_flag_validation.items() if not exists]
        
        if invalid_flags:
            raise HTTPException(
                status_code=400,
                detail=f"Feature flags not found: {', '.join(map(str, invalid_flags))}"
            )
        
        # Bulk validate segments if provided
        segment_ids = []
        if experience_data.selected_segments:
            segment_ids = [UUIDType(segment.segment_id) for segment in experience_data.selected_segments]
            segment_validation = experiences_crud.bulk_validate_segments(segment_ids)
            invalid_segments = [seg_id for seg_id, exists in segment_validation.items() if not exists]
            
            if invalid_segments:
                raise HTTPException(
                    status_code=400,
                    detail=f"Segments not found: {', '.join(map(str, invalid_segments))}"
                )
        
        # Check if experience name already exists
        existing_experience = experiences_crud.get_by_name(
            name=experience_data.name,
            organisation_id=experience_data.organisation_id,
            app_id=experience_data.app_id,
        )
        if existing_experience:
            raise HTTPException(
                status_code=400,
                detail=f"Experience '{experience_data.name}' already exists",
            )
        
        # Handle priority - single query optimization
        priority = experience_data.priority
        if priority is None:
            # Get highest priority in single query
            highest_priority_exp = experiences_crud.get_multi_by_org(
                organisation_id=experience_data.organisation_id,
                app_id=experience_data.app_id,
                skip=0,
                limit=1,
                order_by="priority",
                order_direction="desc",
            )
            priority = (highest_priority_exp[0].priority if highest_priority_exp else 0) + 1
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
        
        # Handle campaign creation or validation
        if experience_data.new_campaign:
            # Create new campaign
            new_campaign = campaigns_crud.create_campaign(
                name=experience_data.new_campaign.name,
                description=experience_data.new_campaign.description,
                status="active",
                rule_config=experience_data.new_campaign.rule_config,
                launched_at=experience_data.new_campaign.launched_at or datetime.utcnow(),
                organisation_id=experience_data.organisation_id,
                app_id=experience_data.app_id,
            )
            campaign_id = new_campaign.pid
        else:
            # Validate existing campaign
            if not experience_data.campaign_id:
                raise HTTPException(
                    status_code=400,
                    detail="campaign_id is required when not creating new campaign"
                )
            existing_campaign = campaigns_crud.get_by_pid(experience_data.campaign_id)
            if not existing_campaign:
                raise HTTPException(
                    status_code=400,
                    detail=f"Campaign {experience_data.campaign_id} not found"
                )
            
            # Validate campaign belongs to same org/app
            if (existing_campaign.organisation_id != experience_data.organisation_id or 
                existing_campaign.app_id != experience_data.app_id):
                raise HTTPException(
                    status_code=400,
                    detail="Campaign does not belong to the specified organization/app"
                )
        
            campaign_id = existing_campaign.pid

        # Prepare object variants data
        object_variants_data = {}
        for obj_id, variant_input in experience_data.object_variants.items():
            object_variants_data[obj_id] = {
                "name": variant_input.name,
                "values": variant_input.values
            }
        
        # Prepare segment configs
        segment_configs = []
        if experience_data.selected_segments:
            for segment_input in experience_data.selected_segments:
                segment_configs.append({
                    "segment_id": segment_input.segment_id,
                    "target_percentage": segment_input.target_percentage
                })
        
        # Create experience with all relationships in single transaction
        experience = experiences_crud.create_experience_with_relationships(
            name=experience_data.name,
            description=experience_data.description,
            priority=priority,
            status=experience_data.status,
            organisation_id=experience_data.organisation_id,
            app_id=experience_data.app_id,
            object_variants=object_variants_data,
            segment_configs=segment_configs if segment_configs else None,
        )
        
        # Create experience-campaign relationship
        campaigns_crud.add_experience_to_campaign(
            campaign_id=campaign_id,
            experience_id=experience.pid,
            target_percentage=experience_data.target_percentage
        )
        return experience

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to create experience: {str(e)}"
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

    # Add counts to each experience
    result = []
    for experience in experiences:
        # Get segments count
        experience_segments_crud = ExperienceSegmentsCRUD(db)
        segments = experience_segments_crud.get_by_experience(experience.pid)
        segment_count = len(segments)

        # Get feature variants count (assuming relationship exists)
        feature_variant_count = (
            len(experience.feature_variants)
            if hasattr(experience, "feature_variants")
            else 0
        )

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

    # Transform campaigns data
    campaigns = []
    for exp_campaign in experience.experience_campaigns:
        if exp_campaign.campaign:
            campaigns.append(
                CampaignResponse(
                    pid=exp_campaign.campaign.pid,
                    name=exp_campaign.campaign.name,
                    description=exp_campaign.campaign.description,
                    status=exp_campaign.campaign.status,
                    rule_config=exp_campaign.campaign.rule_config,
                    launched_at=exp_campaign.campaign.launched_at,
                    target_percentage=exp_campaign.target_percentage,
                    created_at=exp_campaign.campaign.created_at,
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
        campaigns=campaigns,
        segment_count=len(segments),
        feature_variant_count=len(feature_variants),
        user_experience_count=len(experience.user_experiences),
        campaign_count=len(campaigns),
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
    update_data = experience_update.dict(exclude_unset=True, exclude={"priority"})
    if update_data:
        experience = experiences_crud.update(db_obj=experience, obj_in=update_data)

    return experience


@router.put("/{experience_pid}/priority/", response_model=ExperienceResponse)
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


@router.put("/{experience_pid}/status/", response_model=ExperienceResponse)
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


@router.post("/{experience_pid}/clone/", response_model=ExperienceResponse)
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


# TODO: Fix this. Shouldnt delete directly from db.
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
