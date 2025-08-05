from fastapi import APIRouter, Depends, HTTPException
from nova_manager.components.auth.manager import auth_backend, fastapi_users, current_active_user, get_user_manager
from nova_manager.api.auth.request_response import (
    UserRead,
    UserCreate,
    OrganisationCreate,
    OrganisationRead,
    AppCreate,
    AppResponse,
)

from datetime import datetime, timedelta  # noqa: F811
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from nova_manager.components.auth.dependencies import (
    get_token_payload,
    require_user_authentication,
)
from nova_manager.core.log import logger
from nova_manager.components.auth.enums import OrganisationRole, AppRole
from nova_manager.components.auth.models import (
    UserAppMembership,
    UserOrganisationMembership,
    Organisation,
    App,
    AuthUser,
)
from nova_manager.components.auth.manager import get_jwt_strategy
from nova_manager.database.session import get_async_session
from jose import jwt, JWTError

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



class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/auth/token/app/{app_pid}", response_model=TokenResponse, tags=["auth"])
async def switch_app(
    app_pid: str,
    user: AuthUser = Depends(require_user_authentication),
    session: AsyncSession = Depends(get_async_session),
):
    """Issue a new JWT scoped to the specified app_pid if the user is a member."""
    user_id = user.id
    q = select(UserAppMembership).filter_by(user_id=user_id, app_id=app_pid)
    result = await session.execute(q)
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this app")
    new_payload = {"sub": str(user_id), "app_pid": app_pid}

    strategy = get_jwt_strategy()
    now = datetime.utcnow()
    # Include the `aud` claim so fastapi-users read_token recognizes this token
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(seconds=strategy.lifetime_seconds),
        "aud": "jwt",  # Required for read_token verification; matches token_audience
        "app_pid": app_pid,
    }
    token = jwt.encode(payload, strategy.secret, algorithm="HS256")
    return {"access_token": token}

@router.get("/auth/apps", response_model=list[AppResponse], tags=["auth"])
async def list_apps(
    user: AuthUser = Depends(require_user_authentication),
    session: AsyncSession = Depends(get_async_session),
):
    """List all apps the current authenticated user is a member of."""
    # Query apps for this user
    q = select(App).join(UserAppMembership, App.pid == UserAppMembership.app_id).filter(
        UserAppMembership.user_id == user.id
    )
    result = await session.execute(q)
    apps = result.scalars().all()
    return [AppResponse(pid=str(app.pid), name=app.name) for app in apps]
  
# Replace this entire function
@router.post("/auth/organisations", response_model=OrganisationRead, tags=["auth"])
async def create_organisation(
    data: OrganisationCreate,
    user: AuthUser = Depends(require_user_authentication),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new organisation and add the current user as owner."""
    # In create_organisation function
    org = Organisation(name=data.name)
    session.add(org)
    await session.flush()  # Flush to get the generated org.pid

    membership = UserOrganisationMembership(
        user_id=user.id,
        organisation_id=str(org.pid),
        role=OrganisationRole.OWNER.value,
    )
    session.add(membership)
    logger.debug(f"In create_organisation: membership.role = {membership.role!r}")

    # No commit needed, the dependency handles it.
    return OrganisationRead(pid=str(org.pid), name=org.name)


@router.get("/auth/organisations", response_model=list[OrganisationRead], tags=["auth"])
async def list_organisations(
    user: AuthUser = Depends(require_user_authentication),
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
  
# Replace this entire function
@router.post("/auth/organisations/{org_pid}/apps", response_model=AppResponse, tags=["auth"])
async def create_app(
    org_pid: str,
    data: AppCreate,
    user: AuthUser = Depends(require_user_authentication),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new app within the given organisation if user is owner/admin."""
    # Verify the user is an owner or admin of the organisation
    q = select(UserOrganisationMembership).filter_by(
    user_id=user.id, organisation_id=org_pid
    )
    result = await session.execute(q)
    membership = result.scalars().first()
    if not membership or membership.role not in (
        OrganisationRole.OWNER.value, OrganisationRole.ADMIN.value
    ):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions for organisation"
        )

    app = App(name=data.name, organisation_id=org_pid)
    session.add(app)
    await session.flush()  # Flush to get the generated app.pid

    app_membership = UserAppMembership(
        user_id=user.id, app_id=str(app.pid), role=AppRole.OWNER.value
    )
    session.add(app_membership)

    # No commit needed, the dependency handles it.
    return AppResponse(pid=str(app.pid), name=app.name)

# Change password endpoint
class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

@router.post("/auth/password", status_code=204, tags=["auth"])
async def change_password(
    data: ChangePasswordRequest,
    user: AuthUser = Depends(current_active_user),
    user_manager=Depends(get_user_manager),
):
    """Change current user's password by verifying the old password first"""
    # Verify old password using password helper against hashed_password
    valid = user_manager.password_helper.verify(data.old_password, user.hashed_password)
    if not valid:
        raise HTTPException(status_code=403, detail="Old password is incorrect")
    # Update with new password
    from nova_manager.api.auth.request_response import UserUpdate
    update = UserUpdate(password=data.new_password)
    await user_manager.update(user, update)
    # No content on success
    return None
