from fastapi import APIRouter, Depends
from nova_manager.api.users.request_response import (
    UpdateUserProfile,
    UserCreate,
    UserResponse,
)
from nova_manager.components.users.crud_async import UsersAsyncCRUD
from sqlalchemy.ext.asyncio import AsyncSession

from nova_manager.database.async_session import get_async_db
from nova_manager.core.log import logger

router = APIRouter()


@router.post("/create-user/", response_model=UserResponse)
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_async_db)):
    """Create a new user"""
    logger.info(f"Received create_user request: user_id={user_data.user_id}, org={user_data.organisation_id}, app={user_data.app_id}")

    users_crud = UsersAsyncCRUD(db)

    user_id = user_data.user_id
    organisation_id = user_data.organisation_id
    app_id = user_data.app_id
    user_profile = user_data.user_profile or {}

    existing_user = await users_crud.get_by_user_id(
        user_id=user_id, organisation_id=organisation_id, app_id=app_id
    )

    if existing_user:
        # User exists, update user profile with new user_profile
        logger.info(f"User exists, updating profile: {user_id}")
        user = await users_crud.update_user_profile(existing_user, user_profile)
    else:
        # User doesn't exist, create new user with user profile
        logger.info(f"User doesn't exist, creating new user: {user_id}")
        user = await users_crud.create_user(
            user_id, organisation_id, app_id, user_profile
        )

    logger.info(f"User operation successful: nova_user_id={user.pid}")
    return {"nova_user_id": user.pid}


@router.post("/update-user-profile/", response_model=UserResponse)
async def update_user_profile(
    user_profile_update: UpdateUserProfile, db: AsyncSession = Depends(get_async_db)
):
    """Update user profile"""

    users_crud = UsersAsyncCRUD(db)

    user_id = user_profile_update.user_id
    organisation_id = user_profile_update.organisation_id
    app_id = user_profile_update.app_id
    user_profile = user_profile_update.user_profile or {}

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
