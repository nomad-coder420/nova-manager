from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from nova_manager.components.auth.dependencies import (
    require_user_authentication,
    OrganisationRoleRequired,
    RoleRequired,
)
from nova_manager.components.auth.enums import (
    InvitationTargetType,
    InvitationStatus,
    OrganisationRole,
    AppRole,
)
from nova_manager.components.auth.models import (
    AuthUser,
    UserOrganisationMembership,
    UserAppMembership,
)
from nova_manager.components.auth.invitation import Invitation
from nova_manager.api.auth.request_response import (
    InvitationRequest,
    InvitationResponse,
    MemberResponse,
    RoleChangeRequest,
    TransferOwnershipRequest,
)
from nova_manager.database.session import get_async_session
from nova_manager.components.auth.models import Organisation, App
from nova_manager.core.config import BASE_URL, APP_INVITE_TEMPLATE_ID, ORG_INVITE_TEMPLATE_ID, FRONTEND_URL
from nova_manager.service.email_brevo_api import email_service

router = APIRouter()

class InvitationAction(BaseModel):
    action: Literal["accept", "decline"]
    token: str

from nova_manager.components.auth.enums import AppRole, OrganisationRole, InvitationStatus, InvitationTargetType
from nova_manager.components.auth.dependencies import RoleRequired, OrganisationRoleRequired
from nova_manager.components.auth.invitation import Invitation
from nova_manager.api.auth.request_response import InvitationResponse

@router.get("/apps/{app_pid}/pending-invites", response_model=list[InvitationResponse], tags=["invitations"])
async def get_pending_app_invites(
    app_pid: str,
    perm=Depends(RoleRequired([
        AppRole.OWNER, AppRole.ADMIN, AppRole.DEVELOPER, AppRole.ANALYST, AppRole.VIEWER
    ])),
    session: AsyncSession = Depends(get_async_session),
):
    """Get pending invitations for an app (viewer and above)."""
    q = select(Invitation).filter_by(
        target_type=InvitationTargetType.APP,
        target_id=app_pid,
        status=InvitationStatus.PENDING.value
    )
    res = await session.execute(q)
    invites = res.scalars().all()
    return [InvitationResponse(
        pid=str(inv.pid),
        target_type=inv.target_type.value,
        target_id=inv.target_id,
        email=inv.email,
        role=inv.role,
        token=inv.token,
        status=inv.status,
        created_at=inv.created_at,
        expires_at=inv.expires_at
    ) for inv in invites]

@router.post("/apps/{app_pid}/revoke-invite/{invite_pid}", response_model=InvitationResponse, tags=["invitations"])
async def revoke_app_invite(
    app_pid: str,
    invite_pid: str,
    user=Depends(require_user_authentication),
    perm=Depends(RoleRequired([AppRole.OWNER, AppRole.ADMIN])),
    session: AsyncSession = Depends(get_async_session),
):
    """Revoke an app invite (owner/admin only; admin cannot revoke admin invites)."""
    q_inv = select(Invitation).filter_by(pid=invite_pid, target_type=InvitationTargetType.APP, target_id=app_pid)
    res_inv = await session.execute(q_inv)
    invite = res_inv.scalars().first()
    if not invite or invite.status != InvitationStatus.PENDING.value:
        raise HTTPException(status_code=404, detail="Pending invite not found")
    # Get caller's membership
    q_caller = select(UserAppMembership).filter_by(app_id=app_pid, user_id=user.id)
    res_caller = await session.execute(q_caller)
    caller_mem = res_caller.scalars().first()
    if not caller_mem:
        raise HTTPException(status_code=403, detail="No app membership")
    from nova_manager.core.log import logger
    logger.debug(f"[DEBUG] session type: {type(session)}")
    # Admin cannot revoke admin invites
    if caller_mem.role == AppRole.ADMIN.value and invite.role == AppRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Admins cannot revoke admin invites")
    invite.status = InvitationStatus.REVOKED.value
    await session.flush()
    return InvitationResponse(
        pid=str(invite.pid),
        target_type=invite.target_type.value,
        target_id=invite.target_id,
        email=invite.email,
        role=invite.role,
        token=invite.token,
        status=invite.status,
        created_at=invite.created_at,
        expires_at=invite.expires_at
    )

@router.post("/orgs/{org_pid}/revoke-invite/{invite_pid}", response_model=InvitationResponse, tags=["invitations"])
async def revoke_org_invite(
    org_pid: str,
    invite_pid: str,
    user=Depends(require_user_authentication),
    perm=Depends(OrganisationRoleRequired([OrganisationRole.OWNER, OrganisationRole.ADMIN])),
    session: AsyncSession = Depends(get_async_session),
):
    """Revoke an org invite (owner/admin only; admin cannot revoke admin invites)."""
    q_inv = select(Invitation).filter_by(pid=invite_pid, target_type=InvitationTargetType.ORG, target_id=org_pid)
    res_inv = await session.execute(q_inv)
    invite = res_inv.scalars().first()
    if not invite or invite.status != InvitationStatus.PENDING.value:
        raise HTTPException(status_code=404, detail="Pending invite not found")
    # Get caller's membership
    q_caller = select(UserOrganisationMembership).filter_by(organisation_id=org_pid, user_id=user.id)
    res_caller = await session.execute(q_caller)
    caller_mem = res_caller.scalars().first()
    if not caller_mem:
        raise HTTPException(status_code=403, detail="No org membership")
    from nova_manager.core.log import logger
    logger.debug(f"[DEBUG] session type: {type(session)}")
    # Admin cannot revoke admin invites
    if caller_mem.role == OrganisationRole.ADMIN.value and invite.role == OrganisationRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Admins cannot revoke admin invites")
    invite.status = InvitationStatus.REVOKED.value
    await session.flush()
    return InvitationResponse(
        pid=str(invite.pid),
        target_type=invite.target_type.value,
        target_id=invite.target_id,
        email=invite.email,
        role=invite.role,
        token=invite.token,
        status=invite.status,
        created_at=invite.created_at,
        expires_at=invite.expires_at
    )

@router.get("/orgs/{org_pid}/pending-invites", response_model=list[InvitationResponse], tags=["invitations"])
async def get_pending_org_invites(
    org_pid: str,
    perm=Depends(OrganisationRoleRequired([
        OrganisationRole.OWNER, OrganisationRole.ADMIN, OrganisationRole.MEMBER
    ])),
    session: AsyncSession = Depends(get_async_session),
):
    """Get pending invitations for an org (member and above)."""
    q = select(Invitation).filter_by(
        target_type=InvitationTargetType.ORG,
        target_id=org_pid,
        status=InvitationStatus.PENDING.value
    )
    res = await session.execute(q)
    invites = res.scalars().all()
    return [InvitationResponse(
        pid=str(inv.pid),
        target_type=inv.target_type.value,
        target_id=inv.target_id,
        email=inv.email,
        role=inv.role,
        token=inv.token,
        status=inv.status,
        created_at=inv.created_at,
        expires_at=inv.expires_at
    ) for inv in invites]

@router.post("/orgs/{org_pid}/invite", response_model=InvitationResponse, tags=["invitations"])
async def invite_to_organisation(
    org_pid: str,
    data: InvitationRequest,
    user=Depends(require_user_authentication),
    perm=Depends(OrganisationRoleRequired([OrganisationRole.OWNER, OrganisationRole.ADMIN])),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Invite a user to an organisation (owner/admin only).
    """
    # Restrict org Admins from inviting OWNER or ADMIN roles
    q_caller = select(UserOrganisationMembership).filter_by(organisation_id=org_pid, user_id=user.id)
    res_caller = await session.execute(q_caller)
    caller_mem = res_caller.scalars().first()
    if caller_mem.role == OrganisationRole.ADMIN.value and data.role in (OrganisationRole.OWNER.value, OrganisationRole.ADMIN.value):
        raise HTTPException(status_code=403, detail="Admins may only invite members or viewers to the organization")
    inv = Invitation(
        target_type=InvitationTargetType.ORG,
        target_id=org_pid,
        email=data.email,
        role=data.role,
    )
    session.add(inv)
    await session.flush()
    # Log invitation link for manual testing or email stub
    from nova_manager.core.log import logger
    logger.info(f"Invitation created for org {org_pid}: /api/v1/invitations/{inv.pid}/respond?token={inv.token}")
    # Fetch organisation name
    org_res = await session.execute(select(Organisation).filter_by(pid=org_pid))
    org_obj = org_res.scalars().first()
    if not org_obj:
        raise HTTPException(status_code=404, detail="Organization not found")
    org_name = org_obj.name if org_obj else ""
    # Send invitation email
    link = f"{BASE_URL}/api/v1/invitations/{inv.pid}/respond?token={inv.token}"
    try:
        message_id = email_service.send_email_with_curl(
            to=inv.email,
            template_id=ORG_INVITE_TEMPLATE_ID,
            params={"link": link, "org": org_name}
        )
        logger.info(f"Invitation email sent to {inv.email}, message_id={message_id}")
    except Exception as e:
        logger.error(f"Failed to send invitation email to {inv.email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to send invitation email")
    return InvitationResponse(
        pid=str(inv.pid),
        target_type=inv.target_type.value,
        target_id=inv.target_id,
        email=inv.email,
        role=inv.role,
        token=inv.token,
        status=inv.status,
        created_at=inv.created_at,
        expires_at=inv.expires_at,
    )
    

@router.post("/apps/{app_pid}/invite", response_model=InvitationResponse, tags=["invitations"])
async def invite_to_app(
    app_pid: str,
    data: InvitationRequest,
    user=Depends(require_user_authentication),
    perm=Depends(RoleRequired([AppRole.ADMIN, AppRole.OWNER])),
    session: AsyncSession = Depends(get_async_session),
):
    # Validate role on app invite
    if data.role not in [role.value for role in AppRole]:
        raise HTTPException(status_code=400, detail=f"Invalid app invite role '{data.role}'")
    # Restrict app admins from inviting OWNER or ADMIN roles
    q_caller = select(UserAppMembership).filter_by(app_id=app_pid, user_id=user.id)
    res_caller = await session.execute(q_caller)
    caller_mem = res_caller.scalars().first()
    if caller_mem.role == AppRole.ADMIN.value and data.role in (AppRole.OWNER.value, AppRole.ADMIN.value):
        raise HTTPException(status_code=403, detail="Admins may only invite developer/analyst/viewer roles to the application")
    inv = Invitation(
        target_type=InvitationTargetType.APP,
        target_id=app_pid,
        email=data.email,
        role=data.role,
    )
    session.add(inv)
    await session.flush()
    # Log invitation link
    from nova_manager.core.log import logger
    logger.info(f"Invitation created for app {app_pid}: /api/v1/invitations/{inv.pid}/respond?token={inv.token}")
    # Fetch app name
    app_res = await session.execute(select(App).filter_by(pid=app_pid))
    app_obj = app_res.scalars().first()
    if not app_obj:
        raise HTTPException(status_code=404, detail="Application not found")
    app_name = app_obj.name
    # Send email
    link = f"{BASE_URL}/api/v1/invitations/{inv.pid}/respond?token={inv.token}"
    try:
        message_id = email_service.send_email_with_curl(
            to=inv.email,
            template_id=APP_INVITE_TEMPLATE_ID,
            params={"link": link, "app": app_name}
        )
        logger.info(f"Invitation email sent to {inv.email}, message_id={message_id}")
    except Exception as e:
        logger.error(f"Failed to send invitation email to {inv.email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to send invitation email")
    return InvitationResponse(
        pid=str(inv.pid),
        target_type=inv.target_type.value,
        target_id=inv.target_id,
        email=inv.email,
        role=inv.role,
        token=inv.token,
        status=inv.status,
        created_at=inv.created_at,
        expires_at=inv.expires_at,
    )


# Allow users to accept invitation via email link (no auth) and redirect
@router.get("/invitations/{invitation_pid}/respond", tags=["invitations"])
async def accept_invitation(
    invitation_pid: str,
    token: str,
    session: AsyncSession = Depends(get_async_session),
):
    from datetime import datetime, timezone
    # Fetch invitation
    result = await session.execute(select(Invitation).filter_by(pid=invitation_pid))
    inv = result.scalars().first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if inv.token != token:
        raise HTTPException(status_code=400, detail="Invalid invitation token")
    now = datetime.now(timezone.utc)
    if inv.expires_at < now:
        inv.status = InvitationStatus.DECLINED.value
        await session.flush()
        raise HTTPException(status_code=400, detail="Invitation expired")
    if inv.status != InvitationStatus.PENDING.value:
        # Already processed, just redirect
        return RedirectResponse(url=f"{FRONTEND_URL}/dashboard")
    
    # Auto-accept the invitation
    inv.status = InvitationStatus.ACCEPTED.value
    # find user by email
    from sqlalchemy import select as sa_select
    from nova_manager.components.auth.models import AuthUser
    result_user = await session.execute(sa_select(AuthUser).filter_by(email=inv.email))
    user_obj = result_user.scalars().first()
    if user_obj:
        # create membership only if registered
        if inv.target_type == InvitationTargetType.ORG.value:
            q = sa_select(UserOrganisationMembership).filter_by(user_id=user_obj.id, organisation_id=inv.target_id)
            existing = (await session.execute(q)).scalars().first()
            if not existing:
                session.add(UserOrganisationMembership(
                    user_id=user_obj.id,
                    organisation_id=inv.target_id,
                    role=inv.role,
                ))
        else:
            q = sa_select(UserAppMembership).filter_by(user_id=user_obj.id, app_id=inv.target_id)
            existing = (await session.execute(q)).scalars().first()
            if not existing:
                session.add(UserAppMembership(
                    user_id=user_obj.id,
                    app_id=inv.target_id,
                    role=inv.role,
                ))
    # if not registered, membership will be applied on registration hook
    await session.flush()
    # Redirect to frontend dashboard
    return RedirectResponse(url=f"{FRONTEND_URL}/dashboard")


@router.post("/invitations/{invitation_pid}/respond", response_model=InvitationResponse, tags=["invitations"])
async def respond_to_invitation(
    invitation_pid: str,
    action: InvitationAction,
    session: AsyncSession = Depends(get_async_session),
):
    from datetime import datetime, timezone
    # Fetch invitation
    result = await session.execute(select(Invitation).filter_by(pid=invitation_pid))
    inv = result.scalars().first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if inv.token != action.token:
        raise HTTPException(status_code=400, detail="Invalid invitation token")
    now = datetime.now(timezone.utc)
    if inv.expires_at < now:
        inv.status = InvitationStatus.DECLINED.value
        await session.flush()
        raise HTTPException(status_code=400, detail="Invitation expired")
    if inv.status != InvitationStatus.PENDING.value:
        raise HTTPException(status_code=400, detail=f"Invitation already {inv.status}")
    # Process response
    if action.action == "accept":
        inv.status = InvitationStatus.ACCEPTED.value
        # find user by email
        from sqlalchemy import select as sa_select
        from nova_manager.components.auth.models import AuthUser
        result_user = await session.execute(sa_select(AuthUser).filter_by(email=inv.email))
        user_obj = result_user.scalars().first()
        if user_obj:
            # create membership only if registered
            if inv.target_type == InvitationTargetType.ORG.value:
                q = sa_select(UserOrganisationMembership).filter_by(user_id=user_obj.id, organisation_id=inv.target_id)
                existing = (await session.execute(q)).scalars().first()
                if not existing:
                    session.add(UserOrganisationMembership(
                        user_id=user_obj.id,
                        organisation_id=inv.target_id,
                        role=inv.role,
                    ))
            else:
                q = sa_select(UserAppMembership).filter_by(user_id=user_obj.id, app_id=inv.target_id)
                existing = (await session.execute(q)).scalars().first()
                if not existing:
                    session.add(UserAppMembership(
                        user_id=user_obj.id,
                        app_id=inv.target_id,
                        role=inv.role,
                    ))
        # if not registered, membership will be applied on registration hook
    else:
        inv.status = InvitationStatus.DECLINED.value
    await session.flush()
    return InvitationResponse(
        pid=str(inv.pid),
        target_type=inv.target_type.value,
        target_id=inv.target_id,
        email=inv.email,
        role=inv.role,
        token=inv.token,
        status=inv.status,
        created_at=inv.created_at,
        expires_at=inv.expires_at,
    )
