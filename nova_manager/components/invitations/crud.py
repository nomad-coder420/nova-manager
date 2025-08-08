import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from nova_manager.components.invitations.models import Invitation
from nova_manager.components.auth.models import AuthUser, Organisation
from nova_manager.core.enums import UserRole, InvitationStatus


class InvitationsCRUD:
    def __init__(self, db: Session):
        self.db = db

    def generate_invite_token(self) -> str:
        """Generate a secure random token for invitations"""
        # Generate a cryptographically secure URL-safe token (32 bytes = 43 characters when base64url encoded)
        return secrets.token_urlsafe(32)

    def create_invitation(
        self,
        email: str,
        organisation_id: UUID,
        role: UserRole,
        invited_by: UUID,
        expires_in_days: int = 7,
    ) -> Invitation:
        """Create a new invitation"""
        # Generate unique token
        token = self.generate_invite_token()

        # Ensure token is unique
        while self.get_by_token(token):
            token = self.generate_invite_token()

        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        invitation = Invitation(
            email=email.lower(),  # Normalize email at storage
            organisation_id=organisation_id,
            role=role,
            token=token,
            expires_at=expires_at,
            invited_by=invited_by,
            status=InvitationStatus.PENDING,
        )

        self.db.add(invitation)
        self.db.commit()
        self.db.refresh(invitation)
        return invitation

    def get_by_token(self, token: str) -> Optional[Invitation]:
        """Get invitation by token"""
        return self.db.query(Invitation).filter(Invitation.token == token).first()

    def get_valid_invitation(self, token: str) -> Optional[Invitation]:
        """Get valid (non-expired, pending) invitation by token"""
        now = datetime.now(timezone.utc)
        return (
            self.db.query(Invitation)
            .filter(
                and_(
                    Invitation.token == token,
                    Invitation.status == InvitationStatus.PENDING,
                    Invitation.expires_at > now,
                )
            )
            .first()
        )

    def get_pending_by_email(
        self, email: str, organisation_id: UUID
    ) -> Optional[Invitation]:
        """Get pending invitation for email in organization (emails stored normalized)"""
        return (
            self.db.query(Invitation)
            .filter(
                and_(
                    Invitation.email == email.lower(),  # Normalize email for query
                    Invitation.organisation_id == organisation_id,
                    Invitation.status == InvitationStatus.PENDING,
                )
            )
            .first()
        )

    def list_by_organisation(
        self,
        organisation_id: UUID,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Invitation]:
        """List invitations for an organization"""
        query = (
            self.db.query(Invitation)
            .options(
                joinedload(Invitation.invited_by_user),
                joinedload(Invitation.organisation),
            )
            .filter(Invitation.organisation_id == organisation_id)
        )

        if status:
            query = query.filter(Invitation.status == status)

        return (
            query.order_by(Invitation.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def mark_as_accepted(self, token: str) -> bool:
        """Mark invitation as accepted"""
        invitation = self.get_by_token(token)
        if invitation and invitation.status == InvitationStatus.PENDING:
            invitation.status = InvitationStatus.ACCEPTED
            self.db.commit()
            return True
        return False

    def cancel_invitation(self, invitation_id: UUID, organisation_id: UUID) -> bool:
        """Cancel a pending invitation"""
        invitation = (
            self.db.query(Invitation)
            .filter(
                and_(
                    Invitation.pid == invitation_id,
                    Invitation.organisation_id == organisation_id,
                    Invitation.status == InvitationStatus.PENDING,
                )
            )
            .first()
        )

        if invitation:
            invitation.status = InvitationStatus.CANCELLED
            self.db.commit()
            return True
        return False

    def cleanup_expired_invitations(
        self, organisation_id: Optional[UUID] = None
    ) -> int:
        """Clean up expired invitations (mark as expired)"""
        now = datetime.now(timezone.utc)
        query = self.db.query(Invitation).filter(
            and_(
                Invitation.expires_at < now,
                Invitation.status == InvitationStatus.PENDING,
            )
        )

        if organisation_id:
            query = query.filter(Invitation.organisation_id == organisation_id)

        expired_invitations = query.all()
        count = len(expired_invitations)

        for invitation in expired_invitations:
            invitation.status = InvitationStatus.EXPIRED

        self.db.commit()
        return count

    def get_invitation_with_details(self, token: str) -> Optional[dict]:
        """Get invitation with organization and inviter details"""
        invitation = (
            self.db.query(Invitation)
            .options(
                joinedload(Invitation.organisation),
                joinedload(Invitation.invited_by_user),
            )
            .filter(Invitation.token == token)
            .first()
        )

        if not invitation:
            return None

        return {
            "invitation": invitation,
            "organisation_name": invitation.organisation.name,
            "invited_by_name": invitation.invited_by_user.name,
            "invited_by_email": invitation.invited_by_user.email,
        }
