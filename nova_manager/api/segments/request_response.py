from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID as UUIDType
from pydantic import BaseModel, Field


class SegmentCondition(BaseModel):
    field: str = Field(..., description="Field to evaluate (e.g., 'age', 'country')")
    operator: str = Field(..., description="Comparison operator")
    value: Any = Field(..., description="Value to compare against")


class SegmentRuleConfig(BaseModel):
    conditions: List[SegmentCondition] = Field(..., description="List of conditions")
    operator: str = Field(
        default="AND", description="Logic operator between conditions (AND/OR)"
    )


class SegmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Segment name")
    description: str = Field(
        default="", max_length=500, description="Segment description"
    )
    rule_config: Dict[str, Any] = Field(..., description="Segment rule configuration")
    organisation_id: str = Field(..., description="Organization ID")
    app_id: str = Field(..., description="Application ID")


class SegmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    rule_config: Optional[Dict[str, Any]] = None


class ExperienceSegmentResponse(BaseModel):
    pid: UUIDType
    experience_id: UUIDType
    name: str
    status: str
    target_percentage: int
    created_at: datetime


class SegmentResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    rule_config: Dict[str, Any]
    organisation_id: str
    app_id: str
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True


class SegmentListResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    rule_config: Dict[str, Any]
    organisation_id: str
    app_id: str
    created_at: datetime
    modified_at: datetime
    experience_count: int = 0

    class Config:
        from_attributes = True


class SegmentDetailedResponse(BaseModel):
    """Detailed segment response with relationships"""
    pid: UUIDType
    name: str
    description: str
    rule_config: Dict[str, Any]
    organisation_id: str
    app_id: str
    created_at: str
    modified_at: str
    experience_segments: List[ExperienceSegmentResponse] = []
    experience_count: int = 0
    active_experiences: int = 0

    class Config:
        from_attributes = True


class SegmentStatsResponse(BaseModel):
    segment_name: str
    experience_count: int
    active_experiences: int
    rule_config: Dict[str, Any]


class ValidationResponse(BaseModel):
    valid: bool
    errors: List[str]
    warnings: List[str]
