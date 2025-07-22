from typing import Any, Dict, List, Optional
from uuid import UUID as UUIDType
from pydantic import BaseModel


class GetExperienceRequest(BaseModel):
    organisation_id: str
    app_id: str
    user_id: str
    experience_name: str
    payload: dict = {}


class GetExperiencesRequest(BaseModel):
    organisation_id: str
    app_id: str
    user_id: str
    payload: dict = {}
    experience_names: Optional[List[str]] = None
