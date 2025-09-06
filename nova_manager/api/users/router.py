from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from nova_manager.api.users.request_response import (
    UpdateUserProfile,
    UserCreate,
    UserResponse,
)
from nova_manager.components.users.crud_async import UsersAsyncCRUD
from nova_manager.database.async_session import get_async_db
from nova_manager.components.auth.dependencies import require_sdk_app_context
from nova_manager.core.security import SDKAuthContext

router = APIRouter()


@router.post("/create-user/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    auth: SDKAuthContext = Depends(require_sdk_app_context),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new user using API key to infer organisation/app"""

    users_crud = UsersAsyncCRUD(db)

    user_id = user_data.user_id
    organisation_id = auth.organisation_id
    app_id = auth.app_id
    user_profile = user_data.user_profile or {}

    existing_user = await users_crud.get_by_user_id(
        user_id=user_id, organisation_id=organisation_id, app_id=app_id
    )

    if existing_user:
        # User exists, update user profile with new user_profile
        user = await users_crud.update_user_profile(existing_user, user_profile)
    else:
        # User doesn't exist, create new user with user profile
        user = await users_crud.create_user(
            user_id, organisation_id, app_id, user_profile
        )

    return {"nova_user_id": user.pid}


@router.post("/update-user-profile/", response_model=UserResponse)
async def update_user_profile(
    user_profile_update: UpdateUserProfile,
    auth: SDKAuthContext = Depends(require_sdk_app_context),
    db: AsyncSession = Depends(get_async_db),
):
    """Update user profile using API key to infer organisation/app"""

    users_crud = UsersAsyncCRUD(db)

    user_id = user_profile_update.user_id
    organisation_id = auth.organisation_id
    app_id = auth.app_id
    user_profile = user_profile_update.user_profile or {}

    existing_user = await users_crud.get_by_user_id(
        user_id=user_id, organisation_id=organisation_id, app_id=app_id
    )

    if existing_user:
        user = await users_crud.update_user_profile(existing_user, user_profile)
    else:
        user = await users_crud.create_user(
            user_id, organisation_id, app_id, user_profile
        )

    return {"nova_user_id": str(user.pid)}
