from typing import List, Optional
from uuid import UUID as UUIDType
from fastapi import APIRouter, Depends, HTTPException, Query, status
from nova_manager.components.rule_evaluator.controller import RuleEvaluator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from nova_manager.api.segments.request_response import (
    SegmentCreate,
    SegmentDetailedResponse,
    SegmentListResponse,
    SegmentResponse,
    SegmentUpdate,
)
from nova_manager.components.segments.crud import SegmentsCRUD
from nova_manager.database.session import get_db

router = APIRouter()


@router.post("/", response_model=SegmentResponse)
async def create_segment(segment_data: SegmentCreate, db: Session = Depends(get_db)):
    """Create a new segment"""
    try:
        segments_crud = SegmentsCRUD(db)

        # Validate rule configuration
        validation = RuleEvaluator().validate_rule_config(segment_data.rule_config)
        if not validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid rule configuration: {', '.join(validation['errors'])}",
            )

        # Check if name already exists
        existing = segments_crud.get_by_name(
            name=segment_data.name,
            organisation_id=segment_data.organisation_id,
            app_id=segment_data.app_id,
        )
        if existing:
            raise HTTPException(
                status_code=400, detail=f"Segment '{segment_data.name}' already exists"
            )

        # Create segment
        segment = segments_crud.create_segment(
            name=segment_data.name,
            description=segment_data.description,
            rule_config=segment_data.rule_config,
            organisation_id=segment_data.organisation_id,
            app_id=segment_data.app_id,
        )

        return segment

    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Segment with this name already exists"
        )


@router.get("/", response_model=List[SegmentListResponse])
async def list_segments(
    organisation_id: str = Query(...),
    app_id: str = Query(...),
    search: Optional[str] = Query(
        None, description="Search segments by name or description"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List segments with optional search"""
    segments_crud = SegmentsCRUD(db)

    if search:
        segments = segments_crud.search_segments(
            organisation_id=organisation_id,
            app_id=app_id,
            search_term=search,
            skip=skip,
            limit=limit,
        )
    else:
        segments = segments_crud.get_multi_by_org(
            organisation_id=organisation_id, app_id=app_id, skip=skip, limit=limit
        )

    # TODO: Optimize this
    # Add experience count to each segment
    result = []
    for segment in segments:
        stats = segments_crud.get_segment_usage_stats(pid=segment.pid)
        result.append(
            {**segment.__dict__, "experience_count": stats.get("experience_count", 0)}
        )

    return result


@router.get("/{segment_pid}/", response_model=SegmentDetailedResponse)
async def get_segment(segment_pid: UUIDType, db: Session = Depends(get_db)):
    """Get segment by ID"""
    segments_crud = SegmentsCRUD(db)

    segment = segments_crud.get_segment_with_details(segment_pid)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    return segment


@router.put("/{segment_pid}/", response_model=SegmentResponse)
async def update_segment(
    segment_pid: UUIDType, segment_update: SegmentUpdate, db: Session = Depends(get_db)
):
    """Update segment"""
    segments_crud = SegmentsCRUD(db)

    segment = segments_crud.get_by_pid(segment_pid)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    # Validate rule configuration if provided
    if segment_update.rule_config is not None:
        validation = RuleEvaluator().validate_rule_config(segment_update.rule_config)
        if not validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid rule configuration: {', '.join(validation['errors'])}",
            )

    # Check name uniqueness if name is being updated
    if segment_update.name and segment_update.name != segment.name:
        existing = segments_crud.get_by_name(
            name=segment_update.name,
            organisation_id=segment.organisation_id,
            app_id=segment.app_id,
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Segment '{segment_update.name}' already exists",
            )

    # Update segment
    update_data = segment_update.dict(exclude_unset=True)
    updated_segment = segments_crud.update(db_obj=segment, obj_in=update_data)

    return updated_segment


# TODO: Fix this. Shouldnt delete directly from db.
@router.delete("/{segment_pid}/")
async def delete_segment(
    segment_pid: UUIDType,
    force: bool = Query(False, description="Force delete even if used in experiences"),
    db: Session = Depends(get_db),
):
    """Delete segment"""
    segments_crud = SegmentsCRUD(db)

    segment = segments_crud.get_by_pid(segment_pid)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    # Check if segment is used in experiences
    stats = segments_crud.get_segment_usage_stats(pid=segment_pid)
    if stats.get("experience_count", 0) > 0 and not force:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete segment. It is used in {stats['experience_count']} experience(s). Use force=true to delete anyway.",
        )

    segments_crud.delete_by_pid(pid=segment_pid)
    return {"message": "Segment deleted successfully"}
