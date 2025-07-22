from typing import Dict, List
from pydantic import BaseModel


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
