from typing import List
from fastapi import APIRouter, Depends, Query
from nova_manager.api.recommendations.request_response import (
    GetAiRecommendationsRequest,
    AiRecommendationResponse,
    RecommendationResponse,
)
from nova_manager.components.experiences.crud import ExperiencesCRUD
from nova_manager.components.recommendations.controller import RecommendationsController
from nova_manager.components.recommendations.crud import RecommendationsCRUD
from nova_manager.database.session import get_db
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/get-ai-recommendations/", response_model=List[AiRecommendationResponse])
async def get_ai_recommendations(
    validated_data: GetAiRecommendationsRequest, db: Session = Depends(get_db)
):
    user_prompt = validated_data.user_prompt
    organisation_id = validated_data.organisation_id
    app_id = validated_data.app_id

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

    recommendations = recommendations_controller.get_recommendations(
        user_prompt=user_prompt, experiences_context=experiences_context
    )

    recommendations_crud = RecommendationsCRUD(db)

    for recommendation in recommendations:
        experience_name = recommendation.get("experience_name")

        experience = experiences_crud.get_by_name(
            experience_name, organisation_id, app_id
        )

        recommendations_crud.create(
            {
                "experience_id": experience.pid,
                "personalisation_data": recommendation,
            }
        )

    return {"message": "Hello, World!"}


@router.get("/", response_model=List[RecommendationResponse])
async def get_recommendations(
    organisation_id: str = Query(...),
    app_id: str = Query(...),
    db: Session = Depends(get_db),
):
    recommendations_crud = RecommendationsCRUD(db)
    recommendations = recommendations_crud.get_multi_by_org(organisation_id, app_id)

    return recommendations
