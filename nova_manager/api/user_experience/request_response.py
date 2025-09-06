from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel


class GetExperienceRequest(BaseModel):
    user_id: UUID
    experience_name: str
    payload: dict = {}


class GetExperiencesRequest(BaseModel):
    user_id: UUID
    payload: dict = {}
    experience_names: Optional[List[str]] = None
