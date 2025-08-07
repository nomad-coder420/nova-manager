from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from nova_manager.components.auth.dependencies import require_user_authentication, OrganisationRoleRequired, RoleRequired
from nova_manager.components.auth.enums import OrganisationRole, AppRole
from nova_manager.components.auth.models import AuthUser, UserOrganisationMembership, UserAppMembership
from nova_manager.api.auth.request_response import MemberResponse, RoleChangeRequest, TransferOwnershipRequest
from nova_manager.database.session import get_async_session

router = APIRouter()

@router.post("/orgs/{org_pid}/transfer-ownership", response_model=MemberResponse, tags=["members"])
async def transfer_org_ownership(
    org_pid: str,
    data: TransferOwnershipRequest,
    current_user=Depends(require_user_authentication),
    perm=Depends(OrganisationRoleRequired([OrganisationRole.OWNER])),
    session: AsyncSession = Depends(get_async_session),
):
    """Transfer organization ownership to another member"""
    if data.new_owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot transfer ownership to yourself")
    q_new = select(UserOrganisationMembership).filter_by(organisation_id=org_pid, user_id=data.new_owner_id)
    res_new = await session.execute(q_new)
    new_mem = res_new.scalars().first()
    if not new_mem:
        raise HTTPException(status_code=404, detail="New owner membership not found")
    q_cur = select(UserOrganisationMembership).filter_by(organisation_id=org_pid, user_id=current_user.id)
    res_cur = await session.execute(q_cur)
    cur_mem = res_cur.scalars().first()
    cur_mem.role = OrganisationRole.ADMIN.value
    new_mem.role = OrganisationRole.OWNER.value
    await session.flush()
    user_obj = await session.get(AuthUser, new_mem.user_id)
    return MemberResponse(
        user_id=new_mem.user_id,
        email=user_obj.email,
        full_name=user_obj.full_name,
        role=new_mem.role,
    )

@router.post("/apps/{app_pid}/transfer-ownership", response_model=MemberResponse, tags=["members"])
async def transfer_app_ownership(
    app_pid: str,
    data: TransferOwnershipRequest,
    current_user=Depends(require_user_authentication),
    perm=Depends(RoleRequired([AppRole.OWNER])),
    session: AsyncSession = Depends(get_async_session),
):
    """Transfer application ownership to another member"""
    if data.new_owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot transfer ownership to yourself")
    q_new = select(UserAppMembership).filter_by(app_id=app_pid, user_id=data.new_owner_id)
    res_new = await session.execute(q_new)
    new_mem = res_new.scalars().first()
    if not new_mem:
        raise HTTPException(status_code=404, detail="New owner membership not found")
    q_cur = select(UserAppMembership).filter_by(app_id=app_pid, user_id=current_user.id)
    res_cur = await session.execute(q_cur)
    cur_mem = res_cur.scalars().first()
    cur_mem.role = AppRole.ADMIN.value
    new_mem.role = AppRole.OWNER.value
    await session.flush()
    user_obj = await session.get(AuthUser, new_mem.user_id)
    return MemberResponse(
        user_id=new_mem.user_id,
        email=user_obj.email,
        full_name=user_obj.full_name,
        role=new_mem.role,
    )

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
    q = select(UserOrganisationMembership).filter_by(organisation_id=org_pid, user_id=user_id)
    result = await session.execute(q)
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    q_c = select(UserOrganisationMembership).filter_by(organisation_id=org_pid, user_id=user.id)
    res_c = await session.execute(q_c)
    caller_mem = res_c.scalars().first()
    if caller_mem.role == OrganisationRole.ADMIN.value:
        if membership.role in (OrganisationRole.OWNER.value, OrganisationRole.ADMIN.value) or \
           data.role in (OrganisationRole.OWNER.value, OrganisationRole.ADMIN.value):
            raise HTTPException(status_code=403, detail="Admins may only change member/viewer roles in the organization")
    membership.role = data.role
    await session.flush()
    user_obj = await session.get(AuthUser, user_id)
    return MemberResponse(
        user_id=user_id,
        email=user_obj.email,
        full_name=user_obj.full_name,
        role=membership.role,
    )

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
    q = select(UserAppMembership).filter_by(app_id=app_pid, user_id=user_id)
    result = await session.execute(q)
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    q_c = select(UserAppMembership).filter_by(app_id=app_pid, user_id=user.id)
    res_c = await session.execute(q_c)
    caller_mem = res_c.scalars().first()
    if caller_mem.role == AppRole.ADMIN.value:
        if membership.role in (AppRole.OWNER.value, AppRole.ADMIN.value) or \
           data.role in (AppRole.OWNER.value, AppRole.ADMIN.value):
            raise HTTPException(status_code=403, detail="Admins may only change developer/analyst/viewer roles in the application")
    membership.role = data.role
    await session.flush()
    user_obj = await session.get(AuthUser, user_id)
    return MemberResponse(
        user_id=user_id,
        email=user_obj.email,
        full_name=user_obj.full_name,
        role=membership.role,
    )

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
    q_c = select(UserOrganisationMembership).filter_by(organisation_id=org_pid, user_id=user.id)
    res_c = await session.execute(q_c)
    caller_mem = res_c.scalars().first()
    if caller_mem.role == OrganisationRole.ADMIN.value and membership.role in (OrganisationRole.OWNER.value, OrganisationRole.ADMIN.value):
        raise HTTPException(status_code=403, detail="Admins may only remove members or viewers from the organization")
    from nova_manager.components.auth.models import App, UserAppMembership as UAM
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
    if membership.role == OrganisationRole.OWNER.value:
        q_count = select(func.count()).select_from(UserOrganisationMembership).filter_by(
            organisation_id=org_pid, role=OrganisationRole.OWNER.value
        )
        owner_count = (await session.execute(q_count)).scalar_one()
        if owner_count <= 1:
            raise HTTPException(status_code=403, detail="Cannot leave as the sole organization owner")
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
    if membership.role == AppRole.ADMIN.value:
        q_count = select(func.count()).select_from(UserAppMembership).filter_by(
            app_id=app_pid, role=AppRole.ADMIN.value
        )
        admin_count = (await session.execute(q_count)).scalar_one()
        if admin_count <= 1:
            raise HTTPException(status_code=403, detail="Cannot leave as the sole application admin")
    await session.delete(membership)
    await session.flush()
