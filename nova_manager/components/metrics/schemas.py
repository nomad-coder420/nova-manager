from uuid import UUID as UUIDType
from pydantic import BaseModel


class MetricResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    type: str
    config: dict
