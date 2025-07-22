import traceback
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from nova_manager.database.async_session import get_async_db
from nova_manager.api.user_experience.request_response import (
    GetExperienceRequest,
    GetExperienceResponse,
    GetExperiencesRequest,
)
from nova_manager.flows.get_user_experience_variant_flow_async import (
    GetUserExperienceVariantFlowAsync,
)

router = APIRouter()


@router.post("/get-experience/", response_model=GetExperienceResponse)
async def get_user_experience_variant(
    request: GetExperienceRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get variant for a single feature/object for a user.
    """
    try:
        flow = GetUserExperienceVariantFlowAsync(db)

        result = await flow.get_user_experience_variant(
            user_id=request.user_id,
            experience_name=request.experience_name,
            organisation_id=request.organisation_id,
            app_id=request.app_id,
            payload=request.payload,
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get-experiences/", response_model=Dict[str, GetExperienceResponse])
async def get_user_experiences(
    request: GetExperiencesRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get variants for multiple specific features/objects for a user.
    """
    try:
        flow = GetUserExperienceVariantFlowAsync(db)

        results = await flow.get_user_experience_variants(
            user_id=request.user_id,
            organisation_id=request.organisation_id,
            app_id=request.app_id,
            payload=request.payload,
            experience_names=request.experience_names,
        )

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get-all-experiences/", response_model=Dict[str, GetExperienceResponse])
async def get_all_user_experiences(
    request: GetExperiencesRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get experiences for all active features/objects for a user.
    """
    try:
        flow = GetUserExperienceVariantFlowAsync(db)

        # Call without feature_names to get all variants
        results = await flow.get_user_experience_variants(
            user_id=request.user_id,
            organisation_id=request.organisation_id,
            app_id=request.app_id,
            payload=request.payload,
            experience_names=None,  # None means get all
        )

        return results

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
