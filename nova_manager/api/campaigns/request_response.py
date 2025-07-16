from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID as UUIDType
from pydantic import BaseModel, Field


class CampaignCondition(BaseModel):
    field: str = Field(..., description="Field to evaluate (e.g., 'utm_source', 'country')")
    operator: str = Field(..., description="Comparison operator")
    value: Any = Field(..., description="Value to compare against")


class CampaignRuleConfig(BaseModel):
    conditions: List[CampaignCondition] = Field(..., description="List of conditions")
    operator: str = Field(
        default="AND", description="Logic operator between conditions (AND/OR)"
    )


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Campaign name")
    description: str = Field(
        default="", max_length=500, description="Campaign description"
    )
    status: str = Field(
        default="draft", description="Campaign status (draft, active, paused, completed)"
    )
    rule_config: Dict[str, Any] = Field(..., description="Campaign rule configuration")
    launched_at: Optional[datetime] = Field(
        None, description="Campaign launch date and time"
    )
    organisation_id: str = Field(..., description="Organization ID")
    app_id: str = Field(..., description="Application ID")


class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None)
    rule_config: Optional[Dict[str, Any]] = None
    launched_at: Optional[datetime] = None


class CampaignResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    status: str
    rule_config: Dict[str, Any]
    launched_at: datetime
    organisation_id: str
    app_id: str
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True


class CampaignListResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    status: str
    rule_config: Dict[str, Any]
    launched_at: datetime
    organisation_id: str
    app_id: str
    created_at: datetime
    experience_count: int = 0

    class Config:
        from_attributes = True


class ExperienceResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    status: str
    priority: int
    created_at: str
    last_updated_at: str
    target_percentage: Optional[int] = None

    class Config:
        from_attributes = True


class CampaignDetailedResponse(BaseModel):
    """Detailed campaign response with relationships"""
    pid: UUIDType
    name: str
    description: str
    status: str
    rule_config: Dict[str, Any]
    launched_at: str
    organisation_id: str
    app_id: str
    created_at: str
    modified_at: str
    experiences: List[ExperienceResponse] = []
    experience_count: int = 0
    active_experiences: int = 0

    class Config:
        from_attributes = True


class CampaignCloneRequest(BaseModel):
    new_name: str = Field(..., min_length=1, max_length=100)
    new_description: Optional[str] = Field(None, max_length=500)


class CampaignStatusUpdate(BaseModel):
    status: str = Field(
        ..., description="New status (draft, active, paused, completed)"
    )


class CampaignUsageStats(BaseModel):
    campaign_name: str
    experience_count: int
    active_experiences: int
    rule_config: Dict[str, Any]
    status: str
    launched_at: str

    class Config:
        from_attributes = True
