from typing import Dict, List
from uuid import UUID
from pydantic import BaseModel


class GetAiRecommendationsRequest(BaseModel):
    user_prompt: str
    organisation_id: str
    app_id: str


class FeatureVariantRecommendation(BaseModel):
    feature_name: str
    variant_name: str
    config: dict


class ExperienceVariantRecommendation(BaseModel):
    name: str
    description: str
    feature_variants: List[FeatureVariantRecommendation]


class AiRecommendationResponse(BaseModel):
    name: str
    description: str
    experience_name: str
    rule_config: Dict
    experience_variant: ExperienceVariantRecommendation


class RecommendationResponse(BaseModel):
    pid: UUID
    experience_id: UUID
    personalisation_data: Dict
