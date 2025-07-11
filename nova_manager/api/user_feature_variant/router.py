from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from nova_manager.api.user_feature_variant.request_response import (
    BatchEvaluateRequest,
    EvaluateFeatureRequest,
    EvaluateFeatureResponse,
)
from nova_manager.components.user_feature_variant.flows import GetUserFeatureVariantFlow
from nova_manager.database.session import get_db


router = APIRouter()


@router.post("/get-user-feature-variant/", response_model=EvaluateFeatureResponse)
async def get_user_feature_variant(
    request: EvaluateFeatureRequest, db: Session = Depends(get_db)
):
    result = GetUserFeatureVariantFlow(db).get_user_feature_variant(
        user_id=request.user_id,
        feature_name=request.feature_name,
        organisation_id=request.organisation_id,
        app_id=request.app_id,
        payload=request.payload,
    )

    return result


@router.post("/features/batch")
async def batch_evaluate_features(
    request: BatchEvaluateRequest, db: Session = Depends(get_db)
):
    """Evaluate multiple features for a user at once"""

    evaluator = GetUserFeatureVariantFlow(db)

    # Evaluate features
    results = []

    # TODO: Optimize this
    for feature_id in request.feature_ids:
        try:
            result = evaluator.get_user_feature_variant(
                user_id=request.user_id,
                feature_id=feature_id,
                organisation_id=request.organisation_id,
                app_id=request.app_id,
                payload=request.payload,
            )
            results.append(result)
        except:
            continue

    return {"user_id": request.user_id, "features": results}
