from typing import Any, Dict, List, Optional
from uuid import UUID as UUIDType
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
    feature_id: UUIDType
    feature_name: str
    variant_id: UUIDType | None
    variant_name: str
    variant_config: Dict[str, Any]
    experience_id: UUIDType | None
    experience_name: str | None
    personalisation_id: UUIDType | None
    personalisation_name: str | None
    segment_id: UUIDType | None
    segment_name: str | None
    evaluation_reason: str


class GetVariantsResponse(BaseModel):
    features: Dict[str, GetVariantResponse]
