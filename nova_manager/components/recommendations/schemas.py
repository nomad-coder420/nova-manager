from typing import TypedDict


class FeatureVariantRecommendationSchema(TypedDict):
    feature_name: str
    variant_name: str
    config: dict


class ExperienceVariantRecommendationSchema(TypedDict):
    name: str
    description: str
    feature_variants: list[FeatureVariantRecommendationSchema]


class RecommendationSchema(TypedDict):
    name: str
    description: str
    experience_name: str
    rule_config: dict
    experience_variant: ExperienceVariantRecommendationSchema
