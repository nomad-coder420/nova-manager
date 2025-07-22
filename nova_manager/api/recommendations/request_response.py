from typing import Dict
from uuid import UUID
from pydantic import BaseModel


class GetAiRecommendationsRequest(BaseModel):
    user_prompt: str
    organisation_id: str
    app_id: str


class RecommendationResponse(BaseModel):
    pid: UUID
    experience_id: UUID
    personalisation_data: Dict
