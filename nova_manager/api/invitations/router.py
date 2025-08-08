from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from nova_manager.database.session import get_db
from nova_manager.components.auth.dependencies import require_roles, AuthContext
from nova_manager.core.enums import UserRole
from nova_manager.api.invitations.request_response import (
    InviteUserRequest, 
    InvitationResponse, 
    InvitationListResponse,
    ValidateInviteResponse
)
from nova_manager.components.invitations.crud import InvitationsCRUD
from nova_manager.components.auth.crud import AuthCRUD
from nova_manager.core.email import send_invitation_email

router = APIRouter()


@router.post("/invite", response_model=InvitationResponse)
async def send_invitation(
    invite_data: InviteUserRequest,
    auth: AuthContext = Depends(require_roles(UserRole.admin_roles())),
    db: Session = Depends(get_db)
):
    """Send invitation to a new user (admin/owner only)"""
    invitations_crud = InvitationsCRUD(db)
    auth_crud = AuthCRUD(db)
    
    # Check if user already exists with this email
    existing_user = auth_crud.get_auth_user_by_email(invite_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Check if there's already a pending invitation for this email
    existing_invite = invitations_crud.get_pending_by_email(
        invite_data.email, 
        auth.organisation_id
    )
    if existing_invite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation already sent to this email address"
        )
    
    # Create invitation
    invitation = invitations_crud.create_invitation(
        email=invite_data.email,
        organisation_id=auth.organisation_id,
        role=invite_data.role.value,
        invited_by=auth.auth_user_id
    )
    
    # Get organization and inviter details for email
    invitation_details = invitations_crud.get_invitation_with_details(invitation.token)
    
    # Send invitation email
    email_sent = await send_invitation_email(
        email=invite_data.email,
        invite_token=invitation.token,
        organisation_name=invitation_details["organisation_name"],
        invited_by_name=invitation_details["invited_by_name"]
    )
    
    if not email_sent:
        # Could still return success since invitation is created
        # But log the warning
        pass
    
    return InvitationResponse(
        id=invitation.pid,
        email=invitation.email,
        role=invitation.role,
        status=invitation.status,
        expires_at=invitation.expires_at,
        invited_by_name=invitation_details["invited_by_name"],
        organisation_name=invitation_details["organisation_name"],
        created_at=invitation.created_at
    )


@router.get("/invitations", response_model=List[InvitationListResponse])
async def list_invitations(
    status: str = "pending",
    auth: AuthContext = Depends(require_roles(UserRole.admin_roles())),
    db: Session = Depends(get_db)
):
    """List invitations for the organization (admin/owner only)"""
    invitations_crud = InvitationsCRUD(db)
    
    # Clean up expired invitations first
    invitations_crud.cleanup_expired_invitations(auth.organisation_id)
    
    invitations = invitations_crud.list_by_organisation(
        organisation_id=auth.organisation_id,
        status=status if status != "all" else None
    )
    
    return [
        InvitationListResponse(
            id=invite.pid,
            email=invite.email,
            role=invite.role,
            status=invite.status,
            expires_at=invite.expires_at,
            invited_by_name=invite.invited_by_user.name,
            created_at=invite.created_at
        )
        for invite in invitations
    ]


@router.delete("/invitations/{invitation_id}")
async def cancel_invitation(
    invitation_id: UUID,
    auth: AuthContext = Depends(require_roles(UserRole.admin_roles())),
    db: Session = Depends(get_db)
):
    """Cancel a pending invitation (admin/owner only)"""
    invitations_crud = InvitationsCRUD(db)
    
    success = invitations_crud.cancel_invitation(invitation_id, auth.organisation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found or cannot be cancelled"
        )
    
    return {"message": "Invitation cancelled successfully"}


@router.get("/validate-invite/{token}", response_model=ValidateInviteResponse)
async def validate_invite_token(token: str, db: Session = Depends(get_db)):
    """Validate invitation token and return organization details (public endpoint)"""
    invitations_crud = InvitationsCRUD(db)
    
    invitation = invitations_crud.get_valid_invitation(token)
    if not invitation:
        return ValidateInviteResponse(valid=False)
    
    # Get organization and inviter details
    details = invitations_crud.get_invitation_with_details(token)
    
    return ValidateInviteResponse(
        valid=True,
        organisation_name=details["organisation_name"],
        invited_by_name=details["invited_by_name"],
        role=invitation.role,
        email=invitation.email
    )