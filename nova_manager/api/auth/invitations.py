from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
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

router = APIRouter()

class InvitationAction(BaseModel):
    action: Literal["accept", "decline"]
    token: str

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
    
@router.post("/orgs/{org_pid}/transfer-ownership", response_model=MemberResponse, tags=["members"])
async def transfer_org_ownership(
    org_pid: str,
    data: TransferOwnershipRequest,
    current_user=Depends(require_user_authentication),
    perm=Depends(OrganisationRoleRequired([OrganisationRole.OWNER])),
    session: AsyncSession = Depends(get_async_session),
):
    """Transfer organization ownership to another member"""
    # Prevent no-op transfer to self
    if data.new_owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot transfer ownership to yourself")
    # Verify new_owner exists in org
    q_new = select(UserOrganisationMembership).filter_by(organisation_id=org_pid, user_id=data.new_owner_id)
    res_new = await session.execute(q_new)
    new_mem = res_new.scalars().first()
    if not new_mem:
        raise HTTPException(status_code=404, detail="New owner membership not found")
    # Demote current owner
    q_cur = select(UserOrganisationMembership).filter_by(organisation_id=org_pid, user_id=current_user.id)
    res_cur = await session.execute(q_cur)
    cur_mem = res_cur.scalars().first()
    cur_mem.role = OrganisationRole.ADMIN.value
    # Promote new owner
    new_mem.role = OrganisationRole.OWNER.value
    await session.flush()
    email = (await session.get(AuthUser, new_mem.user_id)).email
    return MemberResponse(user_id=new_mem.user_id, email=email, role=new_mem.role)

@router.post("/apps/{app_pid}/transfer-ownership", response_model=MemberResponse, tags=["members"])
async def transfer_app_ownership(
    app_pid: str,
    data: TransferOwnershipRequest,
    current_user=Depends(require_user_authentication),
    perm=Depends(RoleRequired([AppRole.OWNER])),
    session: AsyncSession = Depends(get_async_session),
):
    """Transfer application ownership to another member"""
    # Prevent no-op transfer to self
    if data.new_owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot transfer ownership to yourself")
    # Verify new_owner exists in app
    q_new = select(UserAppMembership).filter_by(app_id=app_pid, user_id=data.new_owner_id)
    res_new = await session.execute(q_new)
    new_mem = res_new.scalars().first()
    if not new_mem:
        raise HTTPException(status_code=404, detail="New owner membership not found")
    # Demote current owner
    q_cur = select(UserAppMembership).filter_by(app_id=app_pid, user_id=current_user.id)
    res_cur = await session.execute(q_cur)
    cur_mem = res_cur.scalars().first()
    cur_mem.role = AppRole.ADMIN.value
    # Promote new owner
    new_mem.role = AppRole.OWNER.value
    await session.flush()
    email = (await session.get(AuthUser, new_mem.user_id)).email
    return MemberResponse(user_id=new_mem.user_id, email=email, role=new_mem.role)
    
# --- Membership Management Endpoints ---
@router.get("/orgs/{org_pid}/members", response_model=list[MemberResponse], tags=["members"])
async def list_org_members(
    org_pid: str,
    user=Depends(require_user_authentication),
    perm=Depends(OrganisationRoleRequired([
        OrganisationRole.OWNER, OrganisationRole.ADMIN, OrganisationRole.MEMBER
    ])),
    session: AsyncSession = Depends(get_async_session),
):
    """List all members of an organization"""
    q = select(UserOrganisationMembership).filter_by(organisation_id=org_pid)
    result = await session.execute(q)
    memberships = result.scalars().all()
    members = []
    for m in memberships:
        # load user details
        user_obj = await session.get(AuthUser, m.user_id)
        members.append(MemberResponse(
            user_id=m.user_id,
            email=user_obj.email,
            full_name=user_obj.full_name,
            role=m.role
        ))
    return members

@router.get("/apps/{app_pid}/members", response_model=list[MemberResponse], tags=["members"])
async def list_app_members(
    app_pid: str,
    user=Depends(require_user_authentication),
    perm=Depends(RoleRequired([AppRole.OWNER, AppRole.ADMIN, AppRole.DEVELOPER, AppRole.ANALYST, AppRole.VIEWER])),
    session: AsyncSession = Depends(get_async_session),
):
    """List all members of an application"""
    q = select(UserAppMembership).filter_by(app_id=app_pid)
    result = await session.execute(q)
    memberships = result.scalars().all()
    members = []
    for m in memberships:
        user_obj = await session.get(AuthUser, m.user_id)
        members.append(MemberResponse(
            user_id=m.user_id,
            email=user_obj.email,
            full_name=user_obj.full_name,
            role=m.role
        ))
    return members

@router.patch("/orgs/{org_pid}/members/{user_id}/role", response_model=MemberResponse, tags=["members"])
async def change_org_member_role(
    org_pid: str,
    user_id: int,
    data: RoleChangeRequest,
    user=Depends(require_user_authentication),
    perm=Depends(OrganisationRoleRequired([OrganisationRole.OWNER, OrganisationRole.ADMIN])),
    session: AsyncSession = Depends(get_async_session),
):
    """Change role of an organization member"""
    # Fetch target membership
    q = select(UserOrganisationMembership).filter_by(organisation_id=org_pid, user_id=user_id)
    result = await session.execute(q)
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    # Fetch caller membership
    q_c = select(UserOrganisationMembership).filter_by(organisation_id=org_pid, user_id=user.id)
    res_c = await session.execute(q_c)
    caller_mem = res_c.scalars().first()
    # If caller is ADMIN, cannot change roles of OWNER or ADMIN, or promote to those roles
    if caller_mem.role == OrganisationRole.ADMIN.value:
        if membership.role in (OrganisationRole.OWNER.value, OrganisationRole.ADMIN.value) or \
           data.role in (OrganisationRole.OWNER.value, OrganisationRole.ADMIN.value):
            raise HTTPException(status_code=403, detail="Admins may only change member/viewer roles in the organization")
    # Apply role change
    membership.role = data.role
    await session.flush()
    email = (await session.get(AuthUser, user_id)).email
    return MemberResponse(user_id=user_id, email=email, role=membership.role)

@router.patch("/apps/{app_pid}/members/{user_id}/role", response_model=MemberResponse, tags=["members"])
async def change_app_member_role(
    app_pid: str,
    user_id: int,
    data: RoleChangeRequest,
    user=Depends(require_user_authentication),
    perm=Depends(RoleRequired([AppRole.OWNER, AppRole.ADMIN])),
    session: AsyncSession = Depends(get_async_session),
):
    """Change role of an application member"""
    # Fetch target membership
    q = select(UserAppMembership).filter_by(app_id=app_pid, user_id=user_id)
    result = await session.execute(q)
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    # Fetch caller membership
    q_c = select(UserAppMembership).filter_by(app_id=app_pid, user_id=user.id)
    res_c = await session.execute(q_c)
    caller_mem = res_c.scalars().first()
    # If caller is ADMIN, cannot change roles of OWNER or ADMIN, or promote to those roles
    if caller_mem.role == AppRole.ADMIN.value:
        if membership.role in (AppRole.OWNER.value, AppRole.ADMIN.value) or \
           data.role in (AppRole.OWNER.value, AppRole.ADMIN.value):
            raise HTTPException(status_code=403, detail="Admins may only change developer/analyst/viewer roles in the application")
    # Apply role change
    membership.role = data.role
    await session.flush()
    email = (await session.get(AuthUser, user_id)).email
    return MemberResponse(user_id=user_id, email=email, role=membership.role)

@router.delete("/orgs/{org_pid}/members/{user_id}", tags=["members"], status_code=204)
async def remove_org_member(
    org_pid: str,
    user_id: int,
    user=Depends(require_user_authentication),
    perm=Depends(OrganisationRoleRequired([OrganisationRole.OWNER, OrganisationRole.ADMIN])),
    session: AsyncSession = Depends(get_async_session),
):
    """Remove a member from an organization"""
    q = select(UserOrganisationMembership).filter_by(organisation_id=org_pid, user_id=user_id)
    result = await session.execute(q)
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    # Restrict Admins from removing OWNER or ADMIN
    q_c = select(UserOrganisationMembership).filter_by(organisation_id=org_pid, user_id=user.id)
    res_c = await session.execute(q_c)
    caller_mem = res_c.scalars().first()
    if caller_mem.role == OrganisationRole.ADMIN.value and membership.role in (OrganisationRole.OWNER.value, OrganisationRole.ADMIN.value):
        raise HTTPException(status_code=403, detail="Admins may only remove members or viewers from the organization")
    # Also remove user from all apps under this organisation
    from nova_manager.components.auth.models import App, UserAppMembership as UAM
    # Find app memberships where app.organisation_id == org_pid
    q_apps = select(UAM).join(App, UAM.app_id == App.pid).filter(
        UAM.user_id == user_id, App.organisation_id == org_pid
    )
    result_apps = await session.execute(q_apps)
    for app_mem in result_apps.scalars().all():
        await session.delete(app_mem)
    await session.delete(membership)
    await session.flush()

@router.delete("/apps/{app_pid}/members/{user_id}", tags=["members"], status_code=204)
async def remove_app_member(
    app_pid: str,
    user_id: int,
    user=Depends(require_user_authentication),
    perm=Depends(RoleRequired([AppRole.OWNER, AppRole.ADMIN])),
    session: AsyncSession = Depends(get_async_session),
):
    """Remove a member from an application"""
    q = select(UserAppMembership).filter_by(app_id=app_pid, user_id=user_id)
    result = await session.execute(q)
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    # Restrict Admins from removing OWNER or ADMIN
    q_c = select(UserAppMembership).filter_by(app_id=app_pid, user_id=user.id)
    res_c = await session.execute(q_c)
    caller_mem = res_c.scalars().first()
    if caller_mem.role == AppRole.ADMIN.value and membership.role in (AppRole.OWNER.value, AppRole.ADMIN.value):
        raise HTTPException(status_code=403, detail="Admins may only remove developer/analyst/viewer roles from the application")
    await session.delete(membership)
    await session.flush()

@router.delete("/orgs/{org_pid}/members/me", tags=["members"], status_code=204)
async def leave_organisation(
    org_pid: str,
    current_user=Depends(require_user_authentication),
    perm=Depends(OrganisationRoleRequired([OrganisationRole.OWNER, OrganisationRole.ADMIN, OrganisationRole.MEMBER])),
    session: AsyncSession = Depends(get_async_session),
):
    """Current user leaves an organization"""
    q = select(UserOrganisationMembership).filter_by(organisation_id=org_pid, user_id=current_user.id)
    result = await session.execute(q)
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    from sqlalchemy import func
    # Only prevent leaving if this is the last owner
    if membership.role == OrganisationRole.OWNER.value:
        q_count = select(func.count()).select_from(UserOrganisationMembership).filter_by(
            organisation_id=org_pid, role=OrganisationRole.OWNER.value
        )
        owner_count = (await session.execute(q_count)).scalar_one()
        if owner_count <= 1:
            raise HTTPException(status_code=403, detail="Cannot leave as the sole organization owner")
    # Cascade remove from child apps
    from nova_manager.components.auth.models import App, UserAppMembership as UAM
    q_apps = select(UAM).join(App, UAM.app_id == App.pid).filter(
        UAM.user_id == current_user.id, App.organisation_id == org_pid
    )
    result_apps = await session.execute(q_apps)
    for app_mem in result_apps.scalars().all():
        await session.delete(app_mem)
    await session.delete(membership)
    await session.flush()

@router.delete("/apps/{app_pid}/members/me", tags=["members"], status_code=204)
async def leave_application(
    app_pid: str,
    current_user=Depends(require_user_authentication),
    perm=Depends(RoleRequired([AppRole.OWNER, AppRole.ADMIN, AppRole.DEVELOPER, AppRole.ANALYST, AppRole.VIEWER])),
    session: AsyncSession = Depends(get_async_session),
):
    """Current user leaves an application"""
    q = select(UserAppMembership).filter_by(app_id=app_pid, user_id=current_user.id)
    result = await session.execute(q)
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    from sqlalchemy import func
    # Only prevent leaving if this is the last admin
    if membership.role == AppRole.ADMIN.value:
        q_count = select(func.count()).select_from(UserAppMembership).filter_by(
            app_id=app_pid, role=AppRole.ADMIN.value
        )
        admin_count = (await session.execute(q_count)).scalar_one()
        if admin_count <= 1:
            raise HTTPException(status_code=403, detail="Cannot leave as the sole application admin")
    await session.delete(membership)
    await session.flush()

@router.post("/apps/{app_pid}/invite", response_model=InvitationResponse, tags=["invitations"])
async def invite_to_app(
    app_pid: str,
    data: InvitationRequest,
    user=Depends(require_user_authentication),
    perm=Depends(RoleRequired([AppRole.ADMIN, AppRole.OWNER])),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Invite a user to an application (app owner/admin only).
    """
    # Restrict app Admins from inviting OWNER or ADMIN roles
    q_caller = select(UserAppMembership).filter_by(app_id=app_pid, user_id=user.id)
    res_caller = await session.execute(q_caller)
    caller_mem = res_caller.scalars().first()
    if caller_mem.role == AppRole.ADMIN.value and data.role in (AppRole.OWNER.value, AppRole.ADMIN.value):
        raise HTTPException(status_code=403, detail="Admins may only invite developers, analysts, or viewers to the application")
    inv = Invitation(
        target_type=InvitationTargetType.APP,
        target_id=app_pid,
        email=data.email,
        role=data.role,
    )
    session.add(inv)
    await session.flush()
    # Log invitation link for manual testing or email stub
    from nova_manager.core.log import logger
    logger.info(f"Invitation created for app {app_pid}: /api/v1/invitations/{inv.pid}/respond?token={inv.token}")
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

@router.post("/invitations/{invitation_pid}/respond", response_model=InvitationResponse, tags=["invitations"])
async def respond_to_invitation(
    invitation_pid: str,
    action: InvitationAction,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Accept or decline an invitation.
    """
    # Lookup invitation
    q = select(Invitation).filter_by(pid=invitation_pid)
    result = await session.execute(q)
    inv = result.scalars().first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    # Validate token and status
    if inv.token != action.token:
        raise HTTPException(status_code=403, detail="Invalid token")
    if inv.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Invitation already responded to")
    if inv.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invitation expired")

    # Process action
    if action.action == "accept":
        # Try to lookup an existing user by invited email
        q2 = select(AuthUser).filter_by(email=inv.email)
        res2 = await session.execute(q2)
        auth_user = res2.scalars().first()
        if auth_user:
            # Add membership only for registered users
            if inv.target_type == InvitationTargetType.ORG:
                membership = UserOrganisationMembership(
                    user_id=auth_user.id,
                    organisation_id=inv.target_id,
                    role=inv.role,
                )
                session.add(membership)
            else:
                # APP invite: ensure org membership exists first
                from nova_manager.components.auth.models import App
                res_app = await session.execute(select(App).filter_by(pid=inv.target_id))
                app_obj = res_app.scalars().first()
                if not app_obj:
                    raise HTTPException(status_code=404, detail="Application not found")
                org_pid = app_obj.organisation_id
                # Check or add org membership
                q3 = select(UserOrganisationMembership).filter_by(
                    user_id=auth_user.id, organisation_id=org_pid
                )
                has_org = (await session.execute(q3)).scalars().first()
                if not has_org:
                    session.add(UserOrganisationMembership(
                        user_id=auth_user.id,
                        organisation_id=org_pid,
                        role=OrganisationRole.MEMBER.value,
                    ))
                # Add app membership
                session.add(UserAppMembership(
                    user_id=auth_user.id,
                    app_id=inv.target_id,
                    role=inv.role,
                ))
    else:
        inv.status = InvitationStatus.DECLINED

    # Update invitation status
    if action.action == "accept":
        inv.status = InvitationStatus.ACCEPTED
    # Flush and return
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
