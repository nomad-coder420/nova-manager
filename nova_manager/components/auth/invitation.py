from uuid import uuid4
from datetime import datetime, timedelta
from enum import Enum as PyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, DateTime, Column, Enum as SAEnum
from nova_manager.core.models import BaseModel
from nova_manager.components.auth.enums import InvitationTargetType, InvitationStatus


class Invitation(BaseModel):
    __tablename__ = "invitations"

    target_type: Mapped[InvitationTargetType] = mapped_column(
        SAEnum(
            InvitationTargetType,
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )
    target_id: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    token: Mapped[str] = mapped_column(String, nullable=False, unique=True, default=lambda: str(uuid4()))
    status: Mapped[InvitationStatus] = mapped_column(
        SAEnum(
            InvitationStatus,
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=InvitationStatus.PENDING.value,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, 
        default=lambda: datetime.utcnow() + timedelta(days=7)
    )

    # relationships if needed for lookup
    # e.g. for org invites to join org or app
