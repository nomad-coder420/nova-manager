from typing import Any, Dict
from datetime import datetime
from typing_extensions import TypedDict
from uuid import UUID
from pydantic import BaseModel


class ExperienceFeatureAssignment(TypedDict):
    feature_id: str
    feature_name: str
    variant_id: str | None
    variant_name: str | None
    config: Dict[str, Any]


class UserExperienceAssignment(BaseModel):
    experience_id: UUID
    personalisation_id: UUID | None
    personalisation_name: str | None
    experience_variant_id: UUID | None
    features: Dict[str, ExperienceFeatureAssignment]
    evaluation_reason: str
    assigned_at: datetime | None = None  # Optional timestamp of assignment

    class Config:
        from_attributes = True
