from typing import Any, Dict
from uuid import UUID as UUIDType
from pydantic import BaseModel


class FeatureFlagResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    type: str
    is_active: bool
    keys_config: Dict[str, Any]
    default_variant: Dict[str, Any]

    class Config:
        from_attributes = True
