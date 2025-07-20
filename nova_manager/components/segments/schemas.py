from typing import Any, Dict
from uuid import UUID as UUIDType
from pydantic import BaseModel


class SegmentResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    rule_config: Dict[str, Any]

    class Config:
        from_attributes = True
