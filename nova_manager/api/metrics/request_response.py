from typing import Any, Dict, Literal
from uuid import UUID as UUIDType
from datetime import datetime
from pydantic import BaseModel


class TrackEventRequest(BaseModel):
    user_id: UUIDType
    organisation_id: str
    app_id: str
    timestamp: datetime
    event_name: str
    event_data: dict | None


class CreateMetricRequest(BaseModel):
    name: str
    description: str
    type: Literal["count", "aggregation", "ratio", "retention"]
    config: dict
    organisation_id: str
    app_id: str


class MetricResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    type: Literal["count", "aggregation", "ratio", "retention"]
    config: dict

    class Config:
        from_attributes = True


class TimeRange(BaseModel):
    start: str
    end: str


class ComputeMetricRequest(BaseModel):
    organisation_id: str
    app_id: str
    type: Literal["count", "aggregation", "ratio", "retention"]
    config: Dict[str, Any]
