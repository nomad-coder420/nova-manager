from typing import Any, Dict, Literal, Optional
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
    type: Literal["count", "aggregation", "ratio", "retention"]
    config: Dict[str, Any]


class EventsSchemaResponse(BaseModel):
    pid: UUIDType
    event_name: str
    event_schema: dict

    class Config:
        from_attributes = True


class UserProfileKeyResponse(BaseModel):
    pid: UUIDType
    key: str
    type: str
    description: str

    class Config:
        from_attributes = True
