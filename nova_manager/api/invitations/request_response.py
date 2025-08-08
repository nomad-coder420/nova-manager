from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr

from nova_manager.core.enums import UserRole, InvitationStatus


class InviteUserRequest(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.MEMBER


class InvitationResponse(BaseModel):
    id: UUID
    email: str
    role: UserRole
    status: InvitationStatus
    expires_at: datetime
    invited_by_name: str
    organisation_name: str
    created_at: datetime

    class Config:
        from_attributes = True


class InvitationListResponse(BaseModel):
    id: UUID
    email: str
    role: UserRole
    status: InvitationStatus
    expires_at: datetime
    invited_by_name: str
    created_at: datetime

    class Config:
        from_attributes = True


class ValidateInviteResponse(BaseModel):
    valid: bool
    organisation_name: str | None = None
    invited_by_name: str | None = None
    role: UserRole | None = None
    email: str | None = None
