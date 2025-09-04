from typing import List, Optional, Dict, Any
from uuid import UUID as UUIDType
from pydantic import BaseModel

from nova_manager.api.experiences.request_response import ExperienceVariantResponse
from nova_manager.components.experiences.schemas import ExperienceResponse
from nova_manager.components.metrics.schemas import MetricResponse


class ExperienceFeatureVariantCreate(BaseModel):
    experience_feature_id: UUIDType
    name: str
    config: dict


class ExperienceVariantCreate(BaseModel):
    name: str
    description: str
    is_default: bool

    feature_variants: List[ExperienceFeatureVariantCreate] | None = None


class PersonalisationCreateExperienceVariant(BaseModel):
    experience_variant: ExperienceVariantCreate
    target_percentage: int


class PersonalisationCreate(BaseModel):
    name: str
    description: str
    experience_id: UUIDType
    priority: int | None = None
    rule_config: dict
    rollout_percentage: int
    selected_metrics: List[UUIDType] = []

    experience_variants: List[PersonalisationCreateExperienceVariant]


class PersonalisationListResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    experience_id: UUIDType
    experience: ExperienceResponse


class PersonalisationExperienceVariantResponse(BaseModel):
    pid: UUIDType
    target_percentage: int
    experience_variant: ExperienceVariantResponse


class PersonalisationMetric(BaseModel):
    metric: MetricResponse


class PersonalisationDetailedResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    experience_id: UUIDType
    priority: int
    rollout_percentage: int
    rule_config: dict
    experience_variants: List[PersonalisationExperienceVariantResponse]
    metrics: List[PersonalisationMetric] = []


class ExperienceFeatureVariantUpdate(BaseModel):
    experience_feature_id: UUIDType
    name: str
    config: dict
    pid: Optional[UUIDType] = None  # Present for updates, None for creates


class ExperienceVariantUpdate(BaseModel):
    name: str
    description: str
    is_default: bool
    pid: Optional[UUIDType] = None  # Present for updates, None for creates

    feature_variants: List[ExperienceFeatureVariantUpdate] | None = None


class PersonalisationUpdateExperienceVariant(BaseModel):
    experience_variant: ExperienceVariantUpdate
    target_percentage: int


class PersonalisationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rule_config: Optional[Dict[str, Any]] = None
    rollout_percentage: Optional[int] = None
    selected_metrics: Optional[List[UUIDType]] = None
    experience_variants: Optional[List[PersonalisationUpdateExperienceVariant]] = None

    reassign: bool = False
