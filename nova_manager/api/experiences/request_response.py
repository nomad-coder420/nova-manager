from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID as UUIDType
from pydantic import BaseModel, Field


class ExperienceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Experience name")
    description: str = Field(
        default="", max_length=500, description="Experience description"
    )
    status: str = Field(
        default="draft",
        description="Experience status (draft, active, paused, completed)",
    )
    selected_objects: List[UUIDType] = Field(
        ..., description="List of feature flag IDs to include in this experience"
    )
    organisation_id: str = Field(..., description="Organization ID")
    app_id: str = Field(..., description="Application ID")


class ExperienceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = None


class ExperienceStatusUpdate(BaseModel):
    status: str = Field(
        ..., description="New status (draft, active, paused, completed)"
    )


class ExperienceClone(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=100, description="New experience name"
    )
    description: Optional[str] = Field(None, max_length=500)


class FeatureVariantInput(BaseModel):
    name: str = Field(..., description="Variant name")
    values: Dict[str, Any] = Field(..., description="Variant configuration values")


class ObjectVariantInput(BaseModel):
    name: str = Field(..., description="Variant name")
    values: Dict[str, Any] = Field(..., description="Variant values/configuration")


class SegmentInput(BaseModel):
    segment_id: str = Field(..., description="Segment ID")
    name: str = Field(..., description="Segment name")
    target_percentage: int = Field(
        default=50, ge=0, le=100, description="Traffic split percentage"
    )
    estimated_users: int = Field(default=0, description="Estimated users in segment")


class CampaignInput(BaseModel):
    name: str = Field(..., description="Campaign name")
    description: str = Field(default="", description="Campaign description")
    rule_config: Dict[str, Any] = Field(..., description="Campaign rule configuration")
    launched_at: Optional[datetime] = Field(None, description="Campaign launch date")


class SegmentResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    rule_config: Dict[str, Any]

    class Config:
        from_attributes = True


class CampaignResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    status: str
    rule_config: Dict[str, Any]
    launched_at: datetime
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


class PersonalisationFeatureVariantResponse(BaseModel):
    """Response model for the junction table with nested feature variant data"""

    pid: UUIDType
    personalisation_id: UUIDType
    feature_variant_id: UUIDType
    created_at: datetime
    modified_at: datetime
    feature_variant: FeatureVariantResponse

    class Config:
        from_attributes = True


class ExperienceResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    status: str
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True


class ExperienceListResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    status: str
    created_at: datetime
    modified_at: datetime
    segment_count: int = 0
    feature_flags_count: int = 0

    class Config:
        from_attributes = True


class FeatureFlagResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    keys_config: Dict[str, Any]
    type: str
    is_active: bool
    default_variant: Dict[str, Any]
    created_at: datetime
    modified_at: datetime
    variants: List[FeatureVariantResponse] = []

    class Config:
        from_attributes = True


class PersonalisationResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    is_default: bool
    feature_variants: List[PersonalisationFeatureVariantResponse] = []
    last_updated_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class PersonalisationDetailedResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    experience_id: UUIDType
    last_updated_at: datetime
    created_at: datetime
    feature_variants: List[PersonalisationFeatureVariantResponse] = []

    class Config:
        from_attributes = True


class PersonalisationVariantCreate(BaseModel):
    feature_id: UUIDType = Field(..., description="Feature flag ID")
    variant_id: Optional[UUIDType] = Field(
        None, description="Existing variant ID to use (optional)"
    )
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Variant name (required if creating new)",
    )
    config: Optional[Dict[str, Any]] = Field(
        None, description="Variant configuration values (required if creating new)"
    )

    def model_validate(cls, values):
        """Validate that either variant_id is provided OR both name and config are provided"""
        variant_id = values.get("variant_id")
        name = values.get("name")
        config = values.get("config")

        if variant_id:
            # Using existing variant - name and config are optional
            return values
        elif name and config is not None:
            # Creating new variant - both name and config are required
            return values
        else:
            raise ValueError(
                "Either variant_id must be provided, or both name and config must be provided"
            )

    @classmethod
    def __get_validators__(cls):
        yield cls.model_validate


class PersonalisationCreate(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=100, description="Personalisation name"
    )
    description: str = Field(
        default="", max_length=500, description="Personalisation description"
    )
    experience_id: UUIDType = Field(..., description="Experience ID")
    variants: List[PersonalisationVariantCreate] = Field(
        ..., description="List of variants for each feature flag"
    )


class PersonalisationDistributionCreate(BaseModel):
    personalisation_id: Optional[UUIDType] = Field(
        None, description="ID of existing personalisation (if using existing)"
    )
    target_percentage: int = Field(
        ..., ge=0, le=100, description="Target percentage for this personalisation"
    )
    use_default: bool = Field(
        default=False, description="Whether to create a default personalisation"
    )


class ExperienceSegmentCreate(BaseModel):
    segment_id: UUIDType = Field(..., description="Segment ID to assign")
    target_percentage: int = Field(
        ..., ge=0, le=100, description="Target percentage of users for this segment"
    )
    personalisation_distribution: List[PersonalisationDistributionCreate] = Field(
        ..., description="Distribution of personalisations within this segment"
    )


class PersonalisationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    variants: Optional[List[PersonalisationVariantCreate]] = None


class PersonalisationListResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    experience_id: UUIDType
    last_updated_at: datetime
    created_at: datetime
    variants_count: int = 0

    class Config:
        from_attributes = True


class PersonalisationDistributionResponse(BaseModel):
    personalisation_id: UUIDType
    personalisation_name: str
    target_percentage: int

    class Config:
        from_attributes = True


class ExperienceSegmentPersonalisationResponse(BaseModel):
    pid: UUIDType
    personalisation_id: UUIDType
    personalisation: PersonalisationResponse
    target_percentage: int

    class Config:
        from_attributes = True


class ExperienceSegmentResponse(BaseModel):
    pid: UUIDType
    target_percentage: int
    priority: int
    segment: SegmentResponse
    personalisations: List[ExperienceSegmentPersonalisationResponse]

    class Config:
        from_attributes = True


class ExperienceDetailedResponse(BaseModel):
    """Detailed experience response with relationships"""

    pid: UUIDType
    name: str
    description: str
    status: str
    created_at: datetime
    modified_at: datetime

    feature_flags: List[FeatureFlagResponse] = []
    personalisations: List[PersonalisationResponse] = []
    experience_segments: List[ExperienceSegmentResponse] = []

    # Counts
    feature_flags_count: int = 0
    personalisations_count: int = 0
    segments_count: int = 0

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message: str
    success: bool = True
    details: Optional[Dict[str, Any]] = None


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
