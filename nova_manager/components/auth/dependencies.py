from fastapi import Depends, HTTPException, logger
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nova_manager.components.auth.manager import UserManager, get_jwt_strategy, current_active_user, get_user_manager
from nova_manager.database.session import get_async_session
from nova_manager.components.auth.models import UserAppMembership, AppRole
from nova_manager.components.auth.models import UserOrganisationMembership
from nova_manager.components.auth.enums import OrganisationRole
from jose import jwt,JWTError

security = HTTPBearer()

async def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    strategy = get_jwt_strategy()

    try:
        # use the same secret/alg/audience as fastapi-users
        return jwt.decode(
            token,
            strategy.secret,
            algorithms=[strategy.algorithm],
            audience="jwt",
        )
    except JWTError as e:
        logger.error(f"JWT decode failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token") from e

async def get_current_app_pid(
    payload: dict = Depends(get_token_payload),
) -> str:
    """
    Extract the active app PID from token payload.
    """
    app_pid = payload.get("app_pid")
    if not app_pid:
        raise HTTPException(status_code=403, detail="No application context in token")
    return app_pid


async def get_current_org_pid(
    payload: dict = Depends(get_token_payload),
) -> str:
    """
    Extract the active organisation PID from token payload or query.
    """
    org_pid = payload.get("org_pid")
    if not org_pid:
        raise HTTPException(status_code=403, detail="No organisation context in token")
    return org_pid


# This is our "Level 1" dependency. It just checks if the user is logged in.
# We use it for organisation-level endpoints.
# It's just an alias to make the code's intent clearer.
require_user_authentication = current_active_user


class RoleRequired:
    """
    Dependency factory to enforce that the current user has one of the required roles on the given application.
    """
    def __init__(self, required_roles: list[AppRole]):
        self.required_roles = required_roles

    async def __call__(
        self,
        app_pid: str,
        payload: dict = Depends(get_token_payload),
        session: AsyncSession = Depends(get_async_session),
    ) -> None:
        """
        Verify the user (from JWT) has one of the required roles on the application identified by the path param app_pid.
        """
        user_id = int(payload.get("sub"))
        # Check membership on the application path parameter
        q = select(UserAppMembership).filter_by(user_id=user_id, app_id=app_pid)
        result = await session.execute(q)
        membership = result.scalars().first()
        if not membership or membership.role not in self.required_roles:
            raise HTTPException(status_code=403, detail="Insufficient application permissions")


class OrganisationRoleRequired:
    """
    Dependency factory to enforce that the current user has one of the required roles on the given organisation.
    """
    def __init__(self, required_roles: list[OrganisationRole]):
        self.required_roles = required_roles

    async def __call__(
        self,
        org_pid: str,
        payload: dict = Depends(get_token_payload),
        session: AsyncSession = Depends(get_async_session),
    ) -> None:
        user_id = int(payload.get("sub"))
        # Check membership on the organisation path parameter
        q = select(UserOrganisationMembership).filter_by(user_id=user_id, organisation_id=org_pid)
        result = await session.execute(q)
        membership = result.scalars().first()
        if not membership or membership.role not in self.required_roles:
            raise HTTPException(status_code=403, detail="Insufficient organisation permissions")
