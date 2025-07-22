from uuid import UUID as UUIDType
from pydantic import BaseModel


class UserCreate(BaseModel):
    user_id: str
    organisation_id: str
    app_id: str
    user_profile: dict | None


class UserResponse(BaseModel):
    nova_user_id: UUIDType


class UpdateUserProfile(BaseModel):
    user_id: str
    organisation_id: str
    app_id: str
    user_profile: dict | None
