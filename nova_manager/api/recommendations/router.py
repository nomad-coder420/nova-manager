from typing import List
from fastapi import APIRouter, Depends, Query
from nova_manager.api.recommendations.request_response import (
    GetAiRecommendationsRequest,
    RecommendationResponse,
)
from nova_manager.components.experiences.crud import ExperiencesCRUD
from nova_manager.components.recommendations.controller import RecommendationsController
from nova_manager.components.recommendations.crud import RecommendationsCRUD
from nova_manager.components.recommendations.schemas import AiRecommendationResponse
from nova_manager.database.session import get_db
from nova_manager.components.auth.dependencies import require_app_context,require_analyst_or_higher
from nova_manager.core.security import AuthContext
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/get-ai-recommendations/", response_model=AiRecommendationResponse)
async def get_ai_recommendations(
    validated_data: GetAiRecommendationsRequest, 
    auth: AuthContext = Depends(require_analyst_or_higher),
    db: Session = Depends(get_db)
):
    user_prompt = validated_data.user_prompt
    organisation_id = str(auth.organisation_id)
    app_id = auth.app_id

    experiences_crud = ExperiencesCRUD(db)
    experiences = experiences_crud.get_with_feature_details(
        organisation_id=organisation_id, app_id=app_id
    )

    experiences_context = [
        {
            "name": experience.name,
            "description": experience.description,
            "status": experience.status,
            "features": [
                {
                    "feature_flag": {
                        "name": feature.feature_flag.name,
                        "description": feature.feature_flag.description,
                        "type": feature.feature_flag.type,
                        "keys_config": feature.feature_flag.keys_config,
                    }
                }
                for feature in experience.features
            ],
        }
        for experience in experiences
    ]

    recommendations_controller = RecommendationsController()

    recommendation = await recommendations_controller.get_recommendation(
        user_prompt=user_prompt, experiences_context=experiences_context
    )

    recommendations_crud = RecommendationsCRUD(db)

    experience_name = recommendation.experience_name

    experience = experiences_crud.get_by_name(experience_name, organisation_id, app_id)

    recommendations_crud.create(
        {
            
            "organisation_id": organisation_id,
            "app_id": app_id,
            "experience_id": experience.pid,
            "personalisation_data": recommendation.model_dump(),
        }
    )

    return recommendation


@router.get("/", response_model=List[RecommendationResponse])
async def get_recommendations(
    auth: AuthContext = Depends(require_app_context),
    db: Session = Depends(get_db),
):
    recommendations_crud = RecommendationsCRUD(db)
    recommendations = recommendations_crud.get_multi_by_org(auth.organisation_id, auth.app_id)

    return recommendations
