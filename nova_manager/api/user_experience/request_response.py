from typing import List, Optional
from pydantic import BaseModel


class GetVariantRequest(BaseModel):
    organisation_id: str
    app_id: str
    user_id: str
    feature_name: str
    payload: dict = {}


class GetVariantsRequest(BaseModel):
    organisation_id: str
    app_id: str
    user_id: str
    payload: dict = {}
    feature_names: Optional[List[str]] = None


class GetVariantResponse(BaseModel):
    feature_id: str
    feature_name: str
    variant_name: str
    variant_config: dict
    experience_id: Optional[str] = None
    experience_name: Optional[str] = None
    evaluation_reason: str


class GetVariantsResponse(BaseModel):
    features: List[GetVariantResponse]
