import uuid
from typing import Optional

from fastapi import Depends, Request, HTTPException
from fastapi_users import BaseUserManager, FastAPIUsers, IntegerIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from datetime import datetime, timedelta
from typing import Any

from nova_manager.api.auth.request_response import UserCreate, UserRead, UserUpdate
from nova_manager.components.auth.database import get_user_db
from nova_manager.components.auth.models import AuthUser
from nova_manager.core.config import SECRET_KEY, DEBUG
from nova_manager.core.log import logger
from nova_manager.components.auth.enums import InvitationTargetType, InvitationStatus, OrganisationRole, AppRole
from nova_manager.core.config import FRONTEND_URL, PASSWORD_RESET_TEMPLATE_ID
from nova_manager.service.email_brevo_api import email_service


class UserManager(IntegerIDMixin, BaseUserManager[AuthUser, int]):
    reset_password_token_secret = SECRET_KEY
    verification_token_secret = SECRET_KEY

    async def on_after_register(self, user: AuthUser, request: Optional[Request] = None):
        # After a new user registers, attach any previously accepted invitations
        from nova_manager.database.session import SessionLocal
        from sqlalchemy import select
        from nova_manager.components.auth.invitation import Invitation
        from nova_manager.components.auth.enums import InvitationTargetType, InvitationStatus, OrganisationRole
        from nova_manager.components.auth.models import UserOrganisationMembership, UserAppMembership, App, Organisation

        db = SessionLocal()
        try:
            # Create a personal organisation for the new user
            org = Organisation(name=user.company_name)
            db.add(org)
            db.flush()  # assign org.pid
            db.add(UserOrganisationMembership(
                user_id=user.id,
                organisation_id=org.pid,
                role=OrganisationRole.OWNER.value,
            ))
            # find all accepted invites for this email
            stmt = select(Invitation).filter_by(email=user.email, status=InvitationStatus.ACCEPTED.value)
            accepted = db.execute(stmt).scalars().all()
            for inv in accepted:
                # validate invite role
                if inv.target_type == InvitationTargetType.ORG.value:
                    if inv.role not in [role.value for role in OrganisationRole]:
                        raise HTTPException(status_code=400, detail=f"Invalid organisation invite role '{inv.role}'")
                else:
                    if inv.role not in [role.value for role in AppRole]:
                        raise HTTPException(status_code=400, detail=f"Invalid app invite role '{inv.role}'")
                if inv.target_type == InvitationTargetType.ORG.value:
                    mem = UserOrganisationMembership(
                        user_id=user.id,
                        organisation_id=inv.target_id,
                        role=inv.role,
                    )
                    db.add(mem)
                else:
                    # ensure org membership first
                    app_obj = db.execute(select(App).filter_by(pid=inv.target_id)).scalars().first()
                    if app_obj:
                        org_id = app_obj.organisation_id
                        existing = db.query(UserOrganisationMembership).filter_by(
                            user_id=user.id, organisation_id=org_id
                        ).first()
                        if not existing:
                            db.add(UserOrganisationMembership(
                                user_id=user.id,
                                organisation_id=org_id,
                                role=OrganisationRole.MEMBER.value
                            ))
                        # add app membership
                        db.add(UserAppMembership(
                            user_id=user.id,
                            app_id=inv.target_id,
                            role=inv.role,
                        ))
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    async def on_after_forgot_password(
        self, user: AuthUser, token: str, request: Optional[Request] = None
    ):
        # Build password reset link and send via email
        reset_link = f"{FRONTEND_URL}/reset-password?token={token}"
        try:
            email_service.send_email_with_curl(
                to=user.email,
                template_id=PASSWORD_RESET_TEMPLATE_ID,
                params={"link": reset_link},
            )
            logger.info(f"Sent password reset email to user {user.id} at {user.email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.email}: {e}")

    async def on_after_request_verify(
        self, user: AuthUser, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id}. Verification token: {token}")


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="api/v1/auth/login")


def get_jwt_strategy() -> JWTStrategy:
    if DEBUG:
        logger.debug(f"JWTStrategy initialized with SECRET_KEY: '{SECRET_KEY[:5]}...'" )
    # Use the standard JWTStrategy from fastapi-users for login/register
    return JWTStrategy(
        secret=SECRET_KEY,
        lifetime_seconds=3600,
        token_audience=["jwt"]
        )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[AuthUser, int](
    get_user_manager,
    [auth_backend],
)

current_active_user = fastapi_users.current_user(active=True)
