from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nova_manager.components.auth.manager import get_jwt_strategy, current_active_user
from nova_manager.database.session import get_async_session
from nova_manager.components.auth.models import UserAppMembership, AppRole

security = HTTPBearer()

async def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Decode JWT and return its payload.
    """
    token = credentials.credentials
    try:
        data = get_jwt_strategy().read_token(token)
        return data
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

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


# This is our "Level 1" dependency. It just checks if the user is logged in.
# We use it for organisation-level endpoints.
# It's just an alias to make the code's intent clearer.
require_user_authentication = Depends(current_active_user)


class RoleRequired:
    """
    Dependency factory to enforce that current token’s app_pid has one of the required roles.
    """
    def __init__(self, required_roles: list[AppRole]):
        self.required_roles = required_roles

    async def __call__(
        self,
        payload: dict = Depends(get_token_payload),
        session: AsyncSession = Depends(get_async_session),
    ) -> None:
        user_id = int(payload.get("sub"))
        app_pid = payload.get("app_pid")
        if app_pid is None:
            raise HTTPException(status_code=403, detail="No application context in token")
        # Check membership
        q = select(UserAppMembership).filter_by(user_id=user_id, app_id=app_pid)
        result = await session.execute(q)
        membership = result.scalars().first()
        if not membership or membership.role not in self.required_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
