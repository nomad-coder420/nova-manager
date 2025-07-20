from datetime import datetime
from nova_manager.components.personalisations.schemas import PersonalisationResponse
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


class SegmentPersonalisationResponse(BaseModel):
    personalisation: PersonalisationResponse


class SegmentListResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    rule_config: Dict[str, Any]

    class Config:
        from_attributes = True


class SegmentDetailedResponse(BaseModel):
    """Detailed segment response with relationships"""

    pid: UUIDType
    name: str
    description: str
    rule_config: Dict[str, Any]

    personalisations: List[SegmentPersonalisationResponse]

    class Config:
        from_attributes = True
