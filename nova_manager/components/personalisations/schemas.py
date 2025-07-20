from datetime import datetime
from uuid import UUID as UUIDType
from pydantic import BaseModel


class PersonalisationResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    experience_id: UUIDType
    priority: int
    rollout_percentage: int
    rule_config: dict
    last_updated_at: datetime

    class Config:
        from_attributes = True
