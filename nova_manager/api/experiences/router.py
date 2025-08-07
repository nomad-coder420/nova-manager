from typing import List, Optional, Dict, Any
from uuid import UUID as UUIDType
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from fastapi import Depends
from nova_manager.components.auth.dependencies import RoleRequired
from nova_manager.components.auth.enums import AppRole

from nova_manager.api.experiences.request_response import (
    ExperienceDetailedResponse,
    ExperienceFeatureResponse,
    ExperienceListResponse,
)
from nova_manager.components.experiences.crud import (
    ExperienceFeaturesCRUD,
    ExperiencesCRUD,
)
from nova_manager.database.session import get_db

router = APIRouter()


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

    return experience


@router.get(
    "/{experience_pid}/features/",
    response_model=List[ExperienceFeatureResponse],
    dependencies=[Depends(RoleRequired([
        AppRole.VIEWER, AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
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
