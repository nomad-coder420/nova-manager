from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from nova_manager.database.session import get_db
from nova_manager.flows.get_user_feature_variant_flow import GetUserFeatureVariantFlow
from nova_manager.api.user_experience.request_response import (
    GetVariantRequest,
    GetVariantResponse,
    GetVariantsRequest,
    GetVariantsResponse,
)

router = APIRouter()


@router.post("/get-variant/", response_model=GetVariantResponse)
async def get_user_feature_variant(
    request: GetVariantRequest,
    db: Session = Depends(get_db),
):
    """
    Get variant for a single feature/object for a user.
    This is the legacy endpoint for backward compatibility.
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

        return GetVariantResponse(
            feature_id=str(result.feature_id),
            feature_name=result.feature_name,
            variant_name=result.variant_name,
            variant_config=result.variant_config,
            experience_id=str(result.experience_id) if result.experience_id else None,
            experience_name=result.experience_name,
            evaluation_reason=result.evaluation_reason,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get-variants-batch/", response_model=GetVariantsResponse)
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

        features = []
        for result in results:
            features.append(
                GetVariantResponse(
                    feature_id=str(result.feature_id),
                    feature_name=result.feature_name,
                    variant_name=result.variant_name,
                    variant_config=result.variant_config,
                    experience_id=(
                        str(result.experience_id) if result.experience_id else None
                    ),
                    experience_name=result.experience_name,
                    evaluation_reason=result.evaluation_reason,
                )
            )

        return GetVariantsResponse(features=features)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get-all-variants/", response_model=GetVariantsResponse)
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

        features = []
        for result in results:
            features.append(
                GetVariantResponse(
                    feature_id=str(result.feature_id),
                    feature_name=result.feature_name,
                    variant_name=result.variant_name,
                    variant_config=result.variant_config,
                    experience_id=(
                        str(result.experience_id) if result.experience_id else None
                    ),
                    experience_name=result.experience_name,
                    evaluation_reason=result.evaluation_reason,
                )
            )

        return GetVariantsResponse(features=features)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
