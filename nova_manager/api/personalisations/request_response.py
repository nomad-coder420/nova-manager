from datetime import datetime
from nova_manager.components.experiences.schemas import ExperienceResponse
from typing import List, Optional, Dict, Any
from uuid import UUID as UUIDType
from pydantic import BaseModel
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

# DTO for updating variants by ID
class PersonalisationUpdateExperienceVariant(BaseModel):
    experience_variant_id: UUIDType
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
    is_active: bool
    experience: ExperienceResponse

class ExperienceFeatureVariantResponse(BaseModel):
    experience_feature_id: UUIDType
    name: str
    config: dict

class ExperienceVariantResponse(BaseModel):
    name: str
    description: str
    is_default: bool
    feature_variants: List[ExperienceFeatureVariantResponse] = []

class PersonalisationExperienceVariantResponse(BaseModel):
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
    is_active: bool
    experience_variants: List[PersonalisationExperienceVariantResponse]
    metrics: List[PersonalisationMetric] = []

class PersonalisationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rule_config: Optional[Dict[str, Any]] = None
    rollout_percentage: Optional[int] = None
    selected_metrics: Optional[List[UUIDType]] = None
    # Use the same variant structure as create for consistency
    experience_variants: Optional[List[PersonalisationCreateExperienceVariant]] = None
    apply_to_existing: bool = False