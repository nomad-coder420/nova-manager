from typing import Any, Dict
from typing_extensions import TypedDict
from uuid import UUID
from pydantic import BaseModel


class ExperienceFeatureAssignment(TypedDict):
    feature_id: UUID
    feature_name: str
    variant_id: UUID | None
    variant_name: str | None
    config: Dict[str, Any]


class UserExperienceAssignment(BaseModel):
    experience_id: UUID
    personalisation_id: UUID | None
    personalisation_name: str | None
    features: Dict[str, ExperienceFeatureAssignment]
    evaluation_reason: str

    class Config:
        from_attributes = True
