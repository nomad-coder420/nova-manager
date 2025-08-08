from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


class AuthUserRegister(BaseModel):
    """Registration request schema"""
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    name: str = Field(..., min_length=2, description="Name must be at least 2 characters")
    company: str = Field(..., min_length=2, description="Company name must be at least 2 characters")


class AuthUserLogin(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str


class AuthUserResponse(BaseModel):
    """Auth user response schema (no internal IDs exposed)"""
    name: str
    email: str
    has_apps: bool  # Whether user has created any apps


class AppCreate(BaseModel):
    """App creation request schema"""
    name: str = Field(..., min_length=2, description="App name must be at least 2 characters")
    description: Optional[str] = None


class AppResponse(BaseModel):
    """App response schema (no internal IDs exposed)"""
    id: UUID  # App's public UUID, not internal org/app IDs
    name: str
    description: Optional[str]
    created_at: str


class SwitchAppRequest(BaseModel):
    """App switch request schema"""
    app_id: str = Field(..., description="App ID to switch to")
