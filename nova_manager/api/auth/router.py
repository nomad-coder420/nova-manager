from fastapi import APIRouter, Depends, HTTPException
from nova_manager.components.auth.manager import auth_backend, fastapi_users
from nova_manager.api.auth.request_response import (
    UserRead,
    UserCreate,
    OrganisationCreate,
    OrganisationRead,
)

router = APIRouter()

# Auth routes (login, logout)
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)

# Register routes
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

# Reset password routes
router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)

# Verify routes
router.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from nova_manager.components.auth.dependencies import (
    get_token_payload,
    require_user_authentication,
)
from nova_manager.components.auth.enums import OrganisationRole
from nova_manager.components.auth.models import (
    UserAppMembership,
    UserOrganisationMembership,
    Organisation,
    App,
    AuthUser,
)
from nova_manager.components.auth.manager import get_jwt_strategy
from nova_manager.database.session import get_async_session


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/auth/token/app/{app_pid}", response_model=TokenResponse, tags=["auth"])
async def switch_app(
    app_pid: str,
    payload: dict = Depends(get_token_payload),
    session: AsyncSession = Depends(get_async_session),
):
    """Issue a new JWT scoped to the specified app_pid if the user is a member."""
    user_id = int(payload.get("sub"))
    q = select(UserAppMembership).filter_by(user_id=user_id, app_id=app_pid)
    result = await session.execute(q)
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this app")
    new_payload = {**payload, "app_pid": app_pid}
    token = get_jwt_strategy().write_token(new_payload)
    return {"access_token": token}

@router.get("/auth/apps", tags=["auth"])
async def list_apps(
    payload: dict = Depends(get_token_payload),
    session: AsyncSession = Depends(get_async_session),
):
    """List all apps the current user is a member of."""
    user_id = int(payload.get("sub"))
    q = select(App).join(UserAppMembership, App.pid == UserAppMembership.app_id).filter(
        UserAppMembership.user_id == user_id
    )
    result = await session.execute(q)
    apps = result.scalars().all()
    return [{"pid": str(app.pid), "name": app.name} for app in apps]
  
@router.post("/auth/organisations", response_model=OrganisationRead, tags=["auth"])
async def create_organisation(
    data: OrganisationCreate,
    user: AuthUser = require_user_authentication,
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new organisation and add the current user as owner."""
    org = Organisation(name=data.name)
    session.add(org)
    await session.flush()
    membership = UserOrganisationMembership(
        user_id=user.id,
        organisation_id=str(org.pid),
        role=OrganisationRole.OWNER,
    )
    session.add(membership)
    await session.commit()
    return OrganisationRead(pid=str(org.pid), name=org.name)


@router.get("/auth/organisations", response_model=list[OrganisationRead], tags=["auth"])
async def list_organisations(
    user: AuthUser = require_user_authentication,
    session: AsyncSession = Depends(get_async_session),
):
    """List all organisations the current user belongs to."""
    q = (
        select(Organisation)
        .join(
            UserOrganisationMembership,
            Organisation.pid == UserOrganisationMembership.organisation_id,
        )
        .filter(UserOrganisationMembership.user_id == user.id)
    )
    result = await session.execute(q)
    orgs = result.scalars().all()
    return [OrganisationRead(pid=str(o.pid), name=o.name) for o in orgs]
