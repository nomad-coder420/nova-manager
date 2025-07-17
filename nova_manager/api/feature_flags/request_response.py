from datetime import datetime
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict
from uuid import UUID
from pydantic import BaseModel


class VariantCreate(BaseModel):
    name: str
    config: Dict[str, Any] = {}


class NovaObjectKeyDefinition(TypedDict):
    type: str
    description: str
    default: Any


class NovaObjectDefinition(BaseModel):
    type: str
    keys: Dict[str, NovaObjectKeyDefinition]


class NovaObjectSyncRequest(BaseModel):
    organisation_id: str
    app_id: str
    objects: Dict[str, NovaObjectDefinition]


class NovaObjectSyncResponse(BaseModel):
    success: bool
    objects_processed: int
    objects_created: int
    objects_updated: int
    objects_skipped: int
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


class TargetingRuleCreate(BaseModel):
    priority: int
    rule_config: Dict[str, Any]


class IndividualTargetingCreate(BaseModel):
    rule_config: Dict[str, Any]


class VariantResponse(BaseModel):
    pid: UUID
    name: str
    config: Dict[str, Any]

    class Config:
        from_attributes = True


class FeatureFlagResponse(BaseModel):
    pid: UUID
    name: str
    description: str
    type: str
    is_active: bool
    created_at: datetime
    modified_at: datetime
    variants: List[VariantResponse] = []
    keys_config: Dict[str, Any]
    default_variant: Dict[str, Any]

    class Config:
        from_attributes = True


class FeatureFlagListItem(BaseModel):
    pid: UUID
    name: str
    description: str
    type: str
    is_active: bool
    keys_config: Dict[str, NovaObjectKeyDefinition]
    default_variant: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class FeatureFlagDetailedResponse(BaseModel):
    pid: UUID
    name: str
    description: str
    is_active: bool
    organisation_id: str
    app_id: str
    created_at: datetime
    modified_at: datetime
    variants: List[VariantResponse] = []
    keys_config: Dict[str, Any]
    default_variant: Dict[str, Any]

    # Experience usage
    experiences: List[Dict[str, Any]] = []
    experience_count: int = 0

    # Variant count
    variant_count: int = 0

    class Config:
        from_attributes = True
