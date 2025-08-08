from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from nova_manager.database.session import get_db
from nova_manager.components.auth.crud import AuthCRUD
from nova_manager.api.auth.request_response import (
    AuthUserRegister,
    AuthUserLogin,
    TokenResponse,
    RefreshTokenRequest,
    AuthUserResponse,
    AppCreate,
    AppResponse,
    SwitchAppRequest,
)
from nova_manager.components.auth.dependencies import (
    get_current_auth,
    require_org_context,
    get_current_auth_ignore_expiry,
)
from nova_manager.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    AuthContext,
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register(user_data: AuthUserRegister, db: Session = Depends(get_db)):
    """Register a new user and create organisation"""
    auth_crud = AuthCRUD(db)
    
    # Check if user already exists
    existing_user = auth_crud.get_auth_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Create organisation
    organisation = auth_crud.create_organisation(name=user_data.company)
    
    # Create auth user
    auth_user = auth_crud.create_auth_user(
        email=user_data.email,
        password=user_data.password,
        name=user_data.name,
        organisation_id=organisation.pid
    )
    
    # Create tokens (no app_id yet)
    token_data = {
        "auth_user_id": str(auth_user.pid),
        "organisation_id": str(organisation.pid),
        "app_id": None,
        "email": auth_user.email,
    }
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"auth_user_id": str(auth_user.pid)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/login", response_model=TokenResponse)
async def login(user_data: AuthUserLogin, db: Session = Depends(get_db)):
    """Login user"""
    auth_crud = AuthCRUD(db)
    
    # Find user
    auth_user = auth_crud.get_auth_user_by_email(user_data.email)
    if not auth_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials"
        )
    
    # Check password
    if not auth_crud.verify_user_password(auth_user, user_data.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials"
        )
    
    # Get user's apps to determine if they have app context
    apps = auth_crud.get_apps_by_organisation(auth_user.organisation_id)
    current_app_id = str(apps[0].pid) if apps else None
    
    # Create tokens
    token_data = {
        "auth_user_id": str(auth_user.pid),
        "organisation_id": str(auth_user.organisation_id),
        "app_id": current_app_id,
        "email": auth_user.email,
    }
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"auth_user_id": str(auth_user.pid)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    current_auth: Optional[AuthContext] = Depends(get_current_auth_ignore_expiry),
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    # Verify refresh token
    payload = verify_token(refresh_data.refresh_token)
    
    # Ensure this is a refresh token
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh token"
        )
    
    auth_user_id = payload.get("auth_user_id")
    if not auth_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh token"
        )
    
    # Get current user data
    auth_crud = AuthCRUD(db)
    auth_user = auth_crud.get_auth_user_by_id(auth_user_id)
    if not auth_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    # Try to preserve current app context using dependency
    current_app_id = current_auth.app_id if current_auth else None
    
    # If no current app context, get user's apps
    if not current_app_id:
        apps = auth_crud.get_apps_by_organisation(auth_user.organisation_id)
        current_app_id = str(apps[0].pid) if apps else None
    
    # Create new access token with preserved app context
    token_data = {
        "auth_user_id": str(auth_user.pid),
        "organisation_id": str(auth_user.organisation_id),
        "app_id": current_app_id,
        "email": auth_user.email,
    }
    
    access_token = create_access_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_data.refresh_token,  # Keep same refresh token
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=AuthUserResponse)
async def get_current_user(
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db)
):
    """Get current user info"""
    auth_crud = AuthCRUD(db)
    auth_user = auth_crud.get_auth_user_by_id(auth.auth_user_id)
    
    if not auth_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    has_apps = auth_crud.user_has_apps(auth_user)
    
    return AuthUserResponse(
        name=auth_user.name,
        email=auth_user.email,
        has_apps=has_apps
    )


@router.post("/apps", response_model=AppResponse)
async def create_app(
    app_data: AppCreate,
    auth: AuthContext = Depends(require_org_context),
    db: Session = Depends(get_db)
):
    """Create a new app"""
    auth_crud = AuthCRUD(db)
    
    # Create app
    app = auth_crud.create_app(
        name=app_data.name,
        organisation_id=auth.organisation_id,
        description=app_data.description
    )
    
    return AppResponse(
        id=app.pid,
        name=app.name,
        description=app_data.description,
        created_at=app.created_at.isoformat() if hasattr(app, 'created_at') else ""
    )


@router.get("/apps", response_model=list[AppResponse])
async def list_apps(
    auth: AuthContext = Depends(require_org_context),
    db: Session = Depends(get_db)
):
    """List user's apps"""
    auth_crud = AuthCRUD(db)
    
    apps = auth_crud.get_apps_by_organisation(auth.organisation_id)
    
    return [
        AppResponse(
            id=app.pid,
            name=app.name,
            description=getattr(app, 'description', None),
            created_at=app.created_at.isoformat() if hasattr(app, 'created_at') else ""
        )
        for app in apps
    ]


@router.post("/switch-app", response_model=TokenResponse)
async def switch_app(
    switch_data: SwitchAppRequest,
    auth: AuthContext = Depends(require_org_context),
    db: Session = Depends(get_db)
):
    """Switch to a different app context"""
    auth_crud = AuthCRUD(db)
    
    # Verify the app belongs to the user's organisation
    app = auth_crud.get_app_by_id(switch_data.app_id, auth.organisation_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )
    
    # Create new access token with the new app context
    token_data = {
        "auth_user_id": str(auth.auth_user_id),
        "organisation_id": str(auth.organisation_id),
        "app_id": switch_data.app_id,
        "email": auth.email,
    }
    
    access_token = create_access_token(token_data)
    
    # Generate new refresh token as well
    refresh_token = create_refresh_token({"auth_user_id": str(auth.auth_user_id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )