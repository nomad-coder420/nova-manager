import uuid
from fastapi_users import schemas
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime



class UserRead(schemas.BaseUser[int]):
    full_name: str = Field(..., description="User's full name")
    company_name: str = Field(..., description="User's company name")


class UserCreate(schemas.BaseUserCreate):
    full_name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    company_name: str = Field(..., min_length=1, max_length=100, description="User's company name")


class UserUpdate(schemas.BaseUserUpdate):
    pass
 

class OrganisationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Organization name")

class OrganisationRead(BaseModel):
    pid: str
    name: str

class AppResponse(BaseModel):
    pid: str
    name: str

# Add request schema for creating apps
class AppCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

class InvitationRequest(BaseModel):
    email: EmailStr
    role: str = Field(..., description="Role for invitee (owner/admin/member/viewer)")

class InvitationResponse(BaseModel):
    pid: str
    target_type: str
    target_id: str
    email: EmailStr
    role: str
    token: str
    status: str
    created_at: datetime
    expires_at: datetime

class MemberResponse(BaseModel):
    user_id: int
    email: EmailStr
    full_name: str = Field(..., description="User's full name")
    role: str

class RoleChangeRequest(BaseModel):
    role: str

class TransferOwnershipRequest(BaseModel):
    new_owner_id: int

# Add response schema for authenticated user
class MeResponse(BaseModel):
    email: EmailStr
    full_name: str = Field(..., description="User's full name")
