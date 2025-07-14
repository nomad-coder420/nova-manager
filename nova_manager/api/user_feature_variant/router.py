from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from nova_manager.api.user_feature_variant.request_response import (
    BatchEvaluateFeatureResponse,
    BatchEvaluateRequest,
    EvaluateAllFeaturesRequest,
    EvaluateAllFeaturesResponse,
    EvaluateFeatureRequest,
    EvaluateFeatureResponse,
)
from nova_manager.components.feature_flags.crud import FeatureFlagsCRUD
from nova_manager.components.user_feature_variant.flows import GetUserFeatureVariantFlow
from nova_manager.database.session import get_db


router = APIRouter()


@router.post("/get-variant/", response_model=EvaluateFeatureResponse)
async def get_user_feature_variant(
    request: EvaluateFeatureRequest, db: Session = Depends(get_db)
):
    evaluator = GetUserFeatureVariantFlow(db)

    result = evaluator.get_user_feature_variant(
        user_id=request.user_id,
        feature_name=request.feature_name,
        organisation_id=request.organisation_id,
        app_id=request.app_id,
        payload=request.payload,
    )

    return result


@router.post("/get-variants-batch/", response_model=BatchEvaluateFeatureResponse)
async def batch_evaluate_features(
    request: BatchEvaluateRequest, db: Session = Depends(get_db)
):
    """Evaluate multiple features for a user at once"""

    evaluator = GetUserFeatureVariantFlow(db)

    # Evaluate features
    results = []

    # TODO: Optimize this
    for feature_name in request.feature_names:
        try:
            result = evaluator.get_user_feature_variant(
                user_id=request.user_id,
                feature_name=feature_name,
                organisation_id=request.organisation_id,
                app_id=request.app_id,
                payload=request.payload,
            )
            results.append(result)
        except:
            continue

    return {"features": results}


@router.post("/get-all-variants/", response_model=EvaluateAllFeaturesResponse)
async def get_all_features_variant(
    request: EvaluateAllFeaturesRequest, db: Session = Depends(get_db)
):
    """Evaluate all features for a user at once"""

    flags_crud = FeatureFlagsCRUD(db)
    evaluator = GetUserFeatureVariantFlow(db)

    # Get all active feature flags for this org/app
    active_flags = flags_crud.get_active_flags(
        organisation_id=request.organisation_id, app_id=request.app_id
    )

    print("active_flags", active_flags)
    # Evaluate features
    results = []

    # TODO: Optimize this
    for feature_flag in active_flags:
        try:
            result = evaluator.get_user_feature_variant(
                user_id=request.user_id,
                feature_name=feature_flag.name,
                organisation_id=request.organisation_id,
                app_id=request.app_id,
                payload=request.payload,
            )
            print(feature_flag.name, result)
            results.append(result)
        except Exception as e:
            print("error", e)
            continue

    return {"features": results}
