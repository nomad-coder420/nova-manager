from datetime import datetime
from uuid import UUID as UUIDType
from sqlalchemy import UUID, String, ForeignKey, DateTime, Boolean, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nova_manager.core.models import BaseModel


class APIKey(BaseModel):
    __tablename__ = "api_keys"

    # Human-friendly name for the key
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Stored hashed key (we will store full token but in real prod store a hash)
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    organisation_id: Mapped[UUIDType] = mapped_column(
        UUID, ForeignKey("organisations.pid"), nullable=False
    )
    app_id: Mapped[UUIDType] = mapped_column(
        UUID, ForeignKey("apps.pid"), nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_by: Mapped[UUIDType] = mapped_column(
        UUID, ForeignKey("auth_users.pid"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    organisation = relationship("Organisation", foreign_keys=[organisation_id])
    app = relationship("App", foreign_keys=[app_id])
    creator = relationship("AuthUser", foreign_keys=[created_by])

    __table_args__ = (
        Index("ix_api_keys_org_app_active", "organisation_id", "app_id", "is_active"),
        UniqueConstraint("name", "organisation_id", "app_id", name="uq_api_keys_name_org_app"),
    )
