from datetime import datetime
from uuid import UUID as UUIDType
from sqlalchemy import UUID, String, ForeignKey, DateTime, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nova_manager.core.models import BaseModel
from nova_manager.core.enums import UserRole, InvitationStatus


class Invitation(BaseModel):
    __tablename__ = "invitations"

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    organisation_id: Mapped[UUIDType] = mapped_column(
        UUID,
        ForeignKey("organisations.pid"),
        nullable=False,
        # No individual index - covered by composite indices
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), nullable=False, default=UserRole.MEMBER
    )
    token: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )  # Unique constraint creates index automatically
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    invited_by: Mapped[UUIDType] = mapped_column(
        UUID,
        ForeignKey("auth_users.pid"),
        nullable=False,
        # FK creates index automatically
    )
    status: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus), nullable=False, default=InvitationStatus.PENDING
    )

    # Relationships (for easier queries)
    organisation = relationship(
        "Organisation",
        foreign_keys=[organisation_id],
    )
    invited_by_user = relationship(
        "AuthUser",
        foreign_keys=[invited_by],
    )

    __table_args__ = (
        # Minimal, focused indices for actual query patterns
        Index(
            "ix_invitations_email_org_status", "email", "organisation_id", "status"
        ),  # Check pending invites for email/org
        Index(
            "ix_invitations_org_status_created",
            "organisation_id",
            "status",
            "created_at",
        ),  # List org invites by status with ordering
        Index(
            "ix_invitations_expires_status", "expires_at", "status"
        ),  # Cleanup expired invites
    )
