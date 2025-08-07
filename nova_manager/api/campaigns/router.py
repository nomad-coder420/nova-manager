from typing import List, Optional
from uuid import UUID as UUIDType
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from nova_manager.components.rule_evaluator.controller import RuleEvaluator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from nova_manager.api.campaigns.request_response import (
    CampaignCreate,
    CampaignDetailedResponse,
    CampaignListResponse,
    CampaignResponse,
    CampaignUpdate,
    CampaignCloneRequest,
    CampaignStatusUpdate,
    CampaignUsageStats,
)
from nova_manager.components.campaigns.crud import CampaignsCRUD
from nova_manager.database.session import get_db
from nova_manager.components.auth.dependencies import RoleRequired
from nova_manager.components.auth.enums import AppRole

router = APIRouter()


@router.post("/", response_model=CampaignResponse,
    dependencies=[Depends(RoleRequired([
        AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def create_campaign(campaign_data: CampaignCreate, db: Session = Depends(get_db)):
    """Create a new campaign"""
    try:
        campaigns_crud = CampaignsCRUD(db)

        # Validate rule configuration
        validation = RuleEvaluator().validate_rule_config(campaign_data.rule_config)
        if not validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid rule configuration: {', '.join(validation['errors'])}",
            )

        # Check if name already exists
        existing = campaigns_crud.get_by_name(
            name=campaign_data.name,
            organisation_id=campaign_data.organisation_id,
            app_id=campaign_data.app_id,
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Campaign '{campaign_data.name}' already exists",
            )

        # Set default launch time if not provided
        launched_at = campaign_data.launched_at or datetime.utcnow()

        # Create campaign
        campaign = campaigns_crud.create_campaign(
            name=campaign_data.name,
            description=campaign_data.description,
            status=campaign_data.status,
            rule_config=campaign_data.rule_config,
            launched_at=launched_at,
            organisation_id=campaign_data.organisation_id,
            app_id=campaign_data.app_id,
        )

        return campaign

    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Campaign with this name already exists"
        )


@router.get("/", response_model=List[CampaignListResponse],
    dependencies=[Depends(RoleRequired([
        AppRole.VIEWER, AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def list_campaigns(
    organisation_id: str = Query(...),
    app_id: str = Query(...),
    status: Optional[str] = Query(None, description="Filter campaigns by status"),
    search: Optional[str] = Query(
        None, description="Search campaigns by name or description"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List campaigns with optional filters"""
    campaigns_crud = CampaignsCRUD(db)

    if search:
        campaigns = campaigns_crud.search_campaigns(
            organisation_id=organisation_id,
            app_id=app_id,
            search_term=search,
            skip=skip,
            limit=limit,
        )
    else:
        campaigns = campaigns_crud.get_multi_by_org(
            organisation_id=organisation_id,
            app_id=app_id,
            status=status,
            skip=skip,
            limit=limit,
        )

    # Add experience count to each campaign
    result = []
    for campaign in campaigns:
        stats = campaigns_crud.get_campaign_usage_stats(pid=campaign.pid)
        result.append(
            {**campaign.__dict__, "experience_count": stats.get("experience_count", 0)}
        )

    return result


@router.get("/{campaign_pid}/", response_model=CampaignDetailedResponse,
    dependencies=[Depends(RoleRequired([
        AppRole.VIEWER, AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def get_campaign(campaign_pid: UUIDType, db: Session = Depends(get_db)):
    """Get campaign by ID with detailed information"""
    campaigns_crud = CampaignsCRUD(db)

    campaign = campaigns_crud.get_campaign_with_details(campaign_pid)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return campaign


@router.put("/{campaign_pid}/", response_model=CampaignResponse,
    dependencies=[Depends(RoleRequired([
        AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def update_campaign(
    campaign_pid: UUIDType,
    campaign_update: CampaignUpdate,
    db: Session = Depends(get_db),
):
    """Update campaign"""
    campaigns_crud = CampaignsCRUD(db)

    campaign = campaigns_crud.get_by_pid(campaign_pid)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Validate rule configuration if provided
    if campaign_update.rule_config is not None:
        validation = RuleEvaluator().validate_rule_config(campaign_update.rule_config)
        if not validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid rule configuration: {', '.join(validation['errors'])}",
            )

    # Check name uniqueness if name is being updated
    if campaign_update.name and campaign_update.name != campaign.name:
        existing = campaigns_crud.get_by_name(
            name=campaign_update.name,
            organisation_id=campaign.organisation_id,
            app_id=campaign.app_id,
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Campaign '{campaign_update.name}' already exists",
            )

    # Update campaign
    update_data = campaign_update.dict(exclude_unset=True)
    updated_campaign = campaigns_crud.update(db_obj=campaign, obj_in=update_data)

    return updated_campaign


@router.put("/{campaign_pid}/status", response_model=CampaignResponse,
    dependencies=[Depends(RoleRequired([
        AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def update_campaign_status(
    campaign_pid: UUIDType,
    status_update: CampaignStatusUpdate,
    db: Session = Depends(get_db),
):
    """Update campaign status"""
    campaigns_crud = CampaignsCRUD(db)

    campaign = campaigns_crud.get_by_pid(campaign_pid)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Validate status
    valid_statuses = ["draft", "active", "paused", "completed"]
    if status_update.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )

    updated_campaign = campaigns_crud.update_status(campaign_pid, status_update.status)
    return updated_campaign


@router.post("/{campaign_pid}/clone", response_model=CampaignResponse,
    dependencies=[Depends(RoleRequired([
        AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def clone_campaign(
    campaign_pid: UUIDType,
    clone_request: CampaignCloneRequest,
    db: Session = Depends(get_db),
):
    """Clone an existing campaign"""
    campaigns_crud = CampaignsCRUD(db)

    # Check if source campaign exists
    source_campaign = campaigns_crud.get_by_pid(campaign_pid)
    if not source_campaign:
        raise HTTPException(status_code=404, detail="Source campaign not found")

    # Check if new name already exists
    existing = campaigns_crud.get_by_name(
        name=clone_request.new_name,
        organisation_id=source_campaign.organisation_id,
        app_id=source_campaign.app_id,
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Campaign '{clone_request.new_name}' already exists",
        )

    # Clone campaign
    cloned_campaign = campaigns_crud.clone_campaign(
        source_pid=campaign_pid,
        new_name=clone_request.new_name,
        new_description=clone_request.new_description,
    )

    if not cloned_campaign:
        raise HTTPException(status_code=500, detail="Failed to clone campaign")

    return cloned_campaign


@router.get("/{campaign_pid}/stats", response_model=CampaignUsageStats,
    dependencies=[Depends(RoleRequired([
        AppRole.VIEWER, AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def get_campaign_stats(campaign_pid: UUIDType, db: Session = Depends(get_db)):
    """Get campaign usage statistics"""
    campaigns_crud = CampaignsCRUD(db)

    stats = campaigns_crud.get_campaign_usage_stats(campaign_pid)
    if not stats:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return stats


@router.delete("/{campaign_pid}/",
    dependencies=[Depends(RoleRequired([
        AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def delete_campaign(
    campaign_pid: UUIDType,
    force: bool = Query(False, description="Force delete even if used in experiences"),
    db: Session = Depends(get_db),
):
    """Delete campaign"""
    campaigns_crud = CampaignsCRUD(db)

    campaign = campaigns_crud.get_by_pid(campaign_pid)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Check if campaign is used in experiences
    stats = campaigns_crud.get_campaign_usage_stats(pid=campaign_pid)
    if stats.get("experience_count", 0) > 0 and not force:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete campaign. It is used in {stats['experience_count']} experience(s). Use force=true to delete anyway.",
        )

    campaigns_crud.delete_by_pid(pid=campaign_pid)
    return {"message": "Campaign deleted successfully"}


@router.get("/status/{status}", response_model=List[CampaignListResponse],
    dependencies=[Depends(RoleRequired([
        AppRole.VIEWER, AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def get_campaigns_by_status(
    status: str,
    organisation_id: str = Query(...),
    app_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get campaigns by status"""
    campaigns_crud = CampaignsCRUD(db)

    # Validate status
    valid_statuses = ["draft", "active", "paused", "completed"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )

    campaigns = campaigns_crud.get_campaigns_by_status(
        organisation_id=organisation_id,
        app_id=app_id,
        status=status,
        skip=skip,
        limit=limit,
    )

    # Add experience count to each campaign
    result = []
    for campaign in campaigns:
        stats = campaigns_crud.get_campaign_usage_stats(pid=campaign.pid)
        result.append(
            {**campaign.__dict__, "experience_count": stats.get("experience_count", 0)}
        )

    return result


@router.get("/launched-after/{date}", response_model=List[CampaignListResponse],
    dependencies=[Depends(RoleRequired([
        AppRole.VIEWER, AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def get_campaigns_launched_after(
    date: datetime,
    organisation_id: str = Query(...),
    app_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get campaigns launched after a specific date"""
    campaigns_crud = CampaignsCRUD(db)

    campaigns = campaigns_crud.get_campaigns_launched_after(
        organisation_id=organisation_id,
        app_id=app_id,
        launched_after=date,
        skip=skip,
        limit=limit,
    )

    # Add experience count to each campaign
    result = []
    for campaign in campaigns:
        stats = campaigns_crud.get_campaign_usage_stats(pid=campaign.pid)
        result.append(
            {**campaign.__dict__, "experience_count": stats.get("experience_count", 0)}
        )

    return result
