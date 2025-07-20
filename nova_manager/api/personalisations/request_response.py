from datetime import datetime
from nova_manager.api.experiences.request_response import ExperienceResponse
from typing import Optional, Dict, Any
from uuid import UUID as UUIDType
from pydantic import BaseModel


class PersonalisationVariantCreate(BaseModel):
    name: str
    config: Dict[str, Any]


class PersonalisationCreate(BaseModel):
    name: str
    description: str
    experience_pid: UUIDType
    variants: Dict[UUIDType, PersonalisationVariantCreate]


class PersonalisationUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    variants: Optional[Dict[UUIDType, PersonalisationVariantCreate]] = None


class PersonalisationListResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    experience_id: UUIDType
    is_default: bool
    last_updated_at: datetime
    experience: ExperienceResponse
