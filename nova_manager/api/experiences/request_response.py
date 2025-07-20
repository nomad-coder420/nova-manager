from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID as UUIDType
from pydantic import BaseModel


class SegmentResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    rule_config: Dict[str, Any]

    class Config:
        from_attributes = True


class ExperienceResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    status: str

    class Config:
        from_attributes = True


class ExperienceFeatureIdResponse(BaseModel):
    pid: UUIDType

    class Config:
        from_attributes = True


class ExperienceListResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    status: str
    features: List[ExperienceFeatureIdResponse]

    class Config:
        from_attributes = True


class FeatureFlagResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    type: str
    is_active: bool
    keys_config: Dict[str, Any]
    default_variant: Dict[str, Any]

    class Config:
        from_attributes = True


class ExperienceFeatureFlagResponse(ExperienceFeatureIdResponse):
    feature_flag: FeatureFlagResponse

    class Config:
        from_attributes = True


class ExperienceFeatureResponse(ExperienceFeatureFlagResponse):
    feature_flag: FeatureFlagResponse

    class Config:
        from_attributes = True


class PersonalisationFeatureVariantResponse(BaseModel):
    pid: UUIDType
    name: str
    config: dict
    experience_feature: ExperienceFeatureResponse

    class Config:
        from_attributes = True


class PersonalisationResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    is_default: bool
    last_updated_at: datetime

    class Config:
        from_attributes = True


class PersonalisationDetailedResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    experience_id: UUIDType
    last_updated_at: datetime
    variants: List[PersonalisationFeatureVariantResponse] = []

    class Config:
        from_attributes = True


class PersonalisationListResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    experience_id: UUIDType
    last_updated_at: datetime
    variants_count: int = 0

    class Config:
        from_attributes = True


class PersonalisationDistributionResponse(BaseModel):
    personalisation_id: UUIDType
    personalisation_name: str
    target_percentage: int

    class Config:
        from_attributes = True


class TargetingRulePersonalisationResponse(BaseModel):
    personalisation: PersonalisationResponse
    target_percentage: int

    class Config:
        from_attributes = True


class TargetingRuleSegmentResponse(BaseModel):
    segment: SegmentResponse
    rule_config: dict

    class Config:
        from_attributes = True


class TargetingRuleResponse(BaseModel):
    pid: UUIDType
    rollout_percentage: int
    rule_config: dict
    priority: int
    personalisations: List[TargetingRulePersonalisationResponse]
    segments: List[TargetingRuleSegmentResponse]


class GetExperienceResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    status: str

    features: List[ExperienceFeatureResponse] = []

    class Config:
        from_attributes = True


class ExperienceDetailedResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    status: str

    personalisations: List[PersonalisationDetailedResponse]
    targeting_rules: List[TargetingRuleResponse]

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message: str
    success: bool = True
    details: Optional[Dict[str, Any]] = None


class PersonalisationDistributionCreate(BaseModel):
    personalisation_id: Optional[UUIDType]
    target_percentage: int
    use_default: bool


class TargetingRuleSegmentCreate(BaseModel):
    segment_id: UUIDType
    rule_config: dict


class ExperienceTargetingRuleCreate(BaseModel):
    rollout_percentage: int
    rule_config: dict
    personalisations: List[PersonalisationDistributionCreate]
    segments: List[TargetingRuleSegmentCreate]
