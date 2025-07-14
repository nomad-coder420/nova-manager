from typing import Any, Dict, List
from uuid import UUID
from pydantic import BaseModel


class EvaluateFeatureRequest(BaseModel):
    user_id: str
    feature_name: str
    organisation_id: str
    app_id: str
    payload: Dict[str, Any] = {}


class EvaluateFeatureResponse(BaseModel):
    feature_id: UUID
    feature_name: str
    variant_name: str
    variant_config: Dict[str, Any]
    evaluation_reason: str  # "explicit_assignment", "targeting_rule", "individual_targeting", "default"


class BatchEvaluateRequest(BaseModel):
    user_id: str
    organisation_id: str
    app_id: str
    payload: Dict[str, Any] = {}
    feature_names: list[str]


class BatchEvaluateFeatureResponse(BaseModel):
    features: List[EvaluateFeatureResponse]


class EvaluateAllFeaturesRequest(BaseModel):
    user_id: str
    organisation_id: str
    app_id: str
    payload: Dict[str, Any] = {}


class EvaluateAllFeaturesResponse(BaseModel):
    features: List[EvaluateFeatureResponse]
