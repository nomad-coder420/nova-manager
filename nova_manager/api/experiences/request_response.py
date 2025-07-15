from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID as UUIDType
from pydantic import BaseModel, Field


class ExperienceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Experience name")
    description: str = Field(
        default="", max_length=500, description="Experience description"
    )
    priority: int = Field(..., ge=1, description="Experience priority (1 is highest)")
    status: str = Field(
        default="draft", 
        description="Experience status (draft, active, paused, completed)"
    )
    organisation_id: str = Field(..., description="Organization ID")
    app_id: str = Field(..., description="Application ID")


class ExperienceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    priority: Optional[int] = Field(None, ge=1)
    status: Optional[str] = None


class ExperiencePriorityUpdate(BaseModel):
    priority: int = Field(..., ge=1, description="New priority for the experience")


class ExperienceStatusUpdate(BaseModel):
    status: str = Field(
        ..., 
        description="New status (draft, active, paused, completed)"
    )


class ExperienceClone(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="New experience name")
    description: Optional[str] = Field(None, max_length=500)
    priority: Optional[int] = Field(None, ge=1)


class ExperienceSegmentCreate(BaseModel):
    segment_id: UUIDType = Field(..., description="Segment ID to add to experience")
    target_percentage: int = Field(
        default=100, ge=0, le=100, description="Target percentage for this segment"
    )


class ExperienceSegmentUpdate(BaseModel):
    target_percentage: int = Field(
        ..., ge=0, le=100, description="New target percentage for the segment"
    )


class ExperienceSegmentBulkUpdate(BaseModel):
    segments: List[ExperienceSegmentCreate] = Field(
        ..., description="List of segments to assign to the experience"
    )


class FeatureVariantInput(BaseModel):
    name: str = Field(..., description="Variant name")
    values: Dict[str, Any] = Field(..., description="Variant configuration values")


class ObjectVariantInput(BaseModel):
    name: str = Field(..., description="Variant name")
    values: Dict[str, Any] = Field(..., description="Variant values/configuration")


class SegmentInput(BaseModel):
    segment_id: str = Field(..., description="Segment ID")
    name: str = Field(..., description="Segment name")
    target_percentage: int = Field(default=50, ge=0, le=100, description="Traffic split percentage")
    estimated_users: int = Field(default=0, description="Estimated users in segment")


class ExperienceComprehensiveCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Experience name")
    description: str = Field(
        default="", max_length=500, description="Experience description"
    )
    priority: Optional[int] = Field(None, ge=1, description="Experience priority (1 is highest). If null, uses highest priority + 1")
    status: str = Field(
        default="draft", 
        description="Experience status (draft, active, paused, completed)"
    )
    organisation_id: str = Field(..., description="Organization ID")
    app_id: str = Field(..., description="Application ID")
    selected_objects: List[str] = Field(..., description="List of selected object IDs (feature flag IDs)")
    object_variants: Dict[str, ObjectVariantInput] = Field(..., description="Object variants mapping")
    selected_segments: Optional[List[SegmentInput]] = Field(default=[], description="Selected segments with splits")
    traffic_split: Optional[int] = Field(default=50, ge=0, le=100, description="Traffic split percentage for global audience")
    # Optional metadata fields that can be stored in experience description or ignored
    campaign_type: Optional[str] = Field(default="existing", description="Campaign type")
    campaign_id: Optional[str] = Field(None, description="Campaign ID if using existing")
    new_campaign: Optional[Dict[str, Any]] = Field(None, description="New campaign data")
    start_date: Optional[str] = Field(None, description="Experience start date")
    end_date: Optional[str] = Field(None, description="Experience end date")
    auto_rollout: Optional[Dict[str, Any]] = Field(None, description="Auto-rollout configuration")


class SegmentResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    rule_config: Dict[str, Any]
    target_percentage: int
    created_at: datetime

    class Config:
        from_attributes = True


class FeatureVariantResponse(BaseModel):
    pid: UUIDType
    name: str
    config: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class ExperienceResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    priority: int
    status: str
    organisation_id: str
    app_id: str
    created_at: datetime
    modified_at: datetime
    last_updated_at: datetime

    class Config:
        from_attributes = True


class ExperienceListResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    priority: int
    status: str
    organisation_id: str
    app_id: str
    created_at: datetime
    modified_at: datetime
    last_updated_at: datetime
    segment_count: int = 0
    feature_variant_count: int = 0

    class Config:
        from_attributes = True


class ExperienceDetailedResponse(BaseModel):
    """Detailed experience response with relationships"""
    pid: UUIDType
    name: str
    description: str
    priority: int
    status: str
    organisation_id: str
    app_id: str
    created_at: datetime
    modified_at: datetime
    last_updated_at: datetime
    segments: List[SegmentResponse] = []
    feature_variants: List[FeatureVariantResponse] = []
    segment_count: int = 0
    feature_variant_count: int = 0
    user_experience_count: int = 0

    class Config:
        from_attributes = True


class ExperienceStatsResponse(BaseModel):
    experience_name: str
    status: str
    priority: int
    segment_count: int
    feature_variant_count: int
    user_experience_count: int
    created_at: str
    last_updated_at: str


class ExperienceSegmentResponse(BaseModel):
    pid: UUIDType
    experience_id: UUIDType
    segment_id: UUIDType
    segment_name: str
    segment_description: str
    target_percentage: int
    created_at: datetime

    class Config:
        from_attributes = True


class ExperienceSegmentUsageResponse(BaseModel):
    experience_id: UUIDType
    experience_name: str
    experience_status: str
    target_percentage: int
    created_at: str


class MessageResponse(BaseModel):
    message: str
    success: bool = True
    details: Optional[Dict[str, Any]] = None


class ValidationResponse(BaseModel):
    valid: bool
    errors: List[str]
    warnings: List[str]


class ExperienceSearchResponse(BaseModel):
    experiences: List[ExperienceListResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class BulkOperationResponse(BaseModel):
    success: bool
    processed: int
    updated: int
    errors: List[str] = []
    details: List[Dict[str, Any]] = [] 