from datetime import datetime
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict
from uuid import UUID
from pydantic import BaseModel

from nova_manager.api.experiences.request_response import ExperienceResponse


class NovaObjectKeyDefinition(TypedDict):
    type: str
    description: str
    default: Any


class NovaObjectDefinition(BaseModel):
    type: str
    keys: Dict[str, NovaObjectKeyDefinition]


class NovaExperienceObjectDefinition(TypedDict):
    pass


class NovaExperienceDefinition(BaseModel):
    description: str
    objects: Dict[str, NovaExperienceObjectDefinition]


class NovaObjectSyncRequest(BaseModel):
    organisation_id: str
    app_id: str
    objects: Dict[str, NovaObjectDefinition]
    experiences: Dict[str, NovaExperienceDefinition]


class NovaObjectSyncResponse(BaseModel):
    success: bool
    objects_processed: int
    objects_created: int
    objects_updated: int
    objects_skipped: int
    experiences_processed: int = 0
    experiences_created: int = 0
    experiences_updated: int = 0
    experiences_skipped: int = 0
    experience_features_created: int = 0
    dashboard_url: Optional[str] = None
    message: str
    details: List[Dict[str, Any]] = []


class FeatureFlagCreate(BaseModel):
    name: str
    organisation_id: str
    app_id: str
    description: Optional[str] = None
    keys_config: Dict[str, Any]
    is_active: bool = False


class FeatureFlagUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class FeatureFlagResponse(BaseModel):
    pid: UUID
    name: str
    description: str
    type: str
    is_active: bool
    keys_config: Dict[str, Any]
    default_variant: Dict[str, Any]

    class Config:
        from_attributes = True


class FeatureFlagExperienceResponse(BaseModel):
    experience_id: UUID


class FeatureFlagListItem(BaseModel):
    pid: UUID
    name: str
    description: str
    type: str
    is_active: bool
    keys_config: Dict[str, NovaObjectKeyDefinition]
    default_variant: Dict[str, Any]
    experiences: List[FeatureFlagExperienceResponse]

    class Config:
        from_attributes = True


class FeatureFlagExperienceDetailedResponse(FeatureFlagExperienceResponse):
    experience: ExperienceResponse


class FeatureFlagDetailedResponse(BaseModel):
    pid: UUID
    name: str
    description: str
    type: str
    is_active: bool
    keys_config: Dict[str, Any]
    default_variant: Dict[str, Any]
    experiences: List[FeatureFlagExperienceDetailedResponse]

    class Config:
        from_attributes = True
