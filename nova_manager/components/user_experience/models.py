from datetime import datetime
from uuid import UUID as UUIDType
from sqlalchemy import UUID, DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nova_manager.core.models import BaseModel


class UserExperience(BaseModel):
    __tablename__ = "user_experience"

    user_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.pid"),
        nullable=False,
        index=True,
    )
    experience_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiences.pid"),
        nullable=False,
        index=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        # Unique constraint: one assignment per user-experience pair
        UniqueConstraint(
            "user_id", "experience_id", name="uq_user_experience_user_exp"
        ),
        # Index for common queries
        Index("idx_user_experience_user", "user_id"),
        Index("idx_user_experience_experience", "experience_id"),
        Index("idx_user_experience_assigned", "assigned_at"),
    )

    # Relationships
    user = relationship(
        "Users", foreign_keys=[user_id], back_populates="user_experiences"
    )
    experience = relationship(
        "Experiences", foreign_keys=[experience_id], back_populates="user_experiences"
    )
