import traceback
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from nova_manager.database.session import get_db
from nova_manager.flows.get_user_feature_variant_flow import GetUserFeatureVariantFlow
from nova_manager.api.user_experience.request_response import (
    GetVariantRequest,
    GetVariantResponse,
    GetVariantsRequest,
)

router = APIRouter()


@router.post("/get-variant/", response_model=GetVariantResponse)
async def get_user_feature_variant(
    request: GetVariantRequest,
    db: Session = Depends(get_db),
):
    """
    Get variant for a single feature/object for a user.
    """
    try:
        flow = GetUserFeatureVariantFlow(db)

        result = flow.get_user_feature_variant(
            user_id=request.user_id,
            feature_name=request.feature_name,
            organisation_id=request.organisation_id,
            app_id=request.app_id,
            payload=request.payload,
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get-variants-batch/", response_model=Dict[str, GetVariantResponse])
async def get_user_feature_variants_batch(
    request: GetVariantsRequest,
    db: Session = Depends(get_db),
):
    """
    Get variants for multiple specific features/objects for a user.
    """
    try:
        flow = GetUserFeatureVariantFlow(db)

        results = flow.get_variants_for_objects(
            user_id=request.user_id,
            organisation_id=request.organisation_id,
            app_id=request.app_id,
            payload=request.payload,
            feature_names=request.feature_names,
        )

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get-all-variants/", response_model=Dict[str, GetVariantResponse])
async def get_all_user_feature_variants(
    request: GetVariantsRequest,
    db: Session = Depends(get_db),
):
    """
    Get variants for all active features/objects for a user.
    """
    try:
        flow = GetUserFeatureVariantFlow(db)

        # Call without feature_names to get all variants
        results = flow.get_variants_for_objects(
            user_id=request.user_id,
            organisation_id=request.organisation_id,
            app_id=request.app_id,
            payload=request.payload,
            feature_names=None,  # None means get all
        )

        return results

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
