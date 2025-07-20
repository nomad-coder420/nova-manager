from datetime import datetime
from nova_manager.core.schemas import PidResponse
from typing import List, Optional, Dict, Any
from uuid import UUID as UUIDType
from pydantic import BaseModel

from nova_manager.components.feature_flags.schemas import FeatureFlagResponse


class ExperienceListResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    status: str
    variants: List[PidResponse]
    features: List[PidResponse]

    class Config:
        from_attributes = True


class ExperienceFeatureResponse(PidResponse):
    feature_flag: FeatureFlagResponse

    class Config:
        from_attributes = True


class ExperienceFeatureVariantResponse(BaseModel):
    experience_feature_id: UUIDType
    name: str
    config: dict


class ExperienceVariantResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    is_default: bool
    last_updated_at: datetime

    feature_variants: List[ExperienceFeatureVariantResponse]

    class Config:
        from_attributes = True


class ExperienceDetailedResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    status: str

    features: List[ExperienceFeatureResponse]
    variants: List[ExperienceVariantResponse]

    class Config:
        from_attributes = True
