from typing import Any, Dict, List, Optional
from uuid import UUID as UUIDType
from pydantic import BaseModel


class GetExperienceRequest(BaseModel):
    organisation_id: str
    app_id: str
    user_id: str
    experience_name: str
    payload: dict = {}


class GetExperiencesRequest(BaseModel):
    organisation_id: str
    app_id: str
    user_id: str
    payload: dict = {}
    experience_names: Optional[List[str]] = None


class ExperienceVariant(BaseModel):
    variant_id: UUIDType
    variant_name: str
    variant_config: Dict[str, Any]


class ExperienceFeature(BaseModel):
    feature_id: UUIDType
    feature_name: str
    feature_config: Dict[str, Any]


class GetExperienceResponse(BaseModel):
    experience_id: UUIDType
    experience_name: str
    feature_id: UUIDType | None
    feature_name: str
    feature_config: Dict[str, Any]
    experience_name: str | None
    personalisation_id: UUIDType | None
    personalisation_name: str | None
    segment_id: UUIDType | None
    segment_name: str | None
    evaluation_reason: str
