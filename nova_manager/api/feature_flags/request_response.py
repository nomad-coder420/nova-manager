from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel


class VariantCreate(BaseModel):
    name: str
    config: Dict[str, Any] = {}


class FeatureFlagCreate(BaseModel):
    name: str
    organisation_id: str
    app_id: str
    description: Optional[str] = None
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
    description: Optional[str]
    is_active: bool
    organisation_id: str
    app_id: str
    created_at: datetime
    variants: List[VariantResponse] = []
    default_variant: Optional[VariantResponse] = None

    class Config:
        from_attributes = True


class FeatureFlagListItem(BaseModel):
    pid: UUID
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    variant_count: int

    class Config:
        from_attributes = True
