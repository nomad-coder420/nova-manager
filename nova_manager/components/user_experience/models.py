from datetime import datetime
from uuid import UUID as UUIDType
from sqlalchemy import (
    JSON,
    UUID,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nova_manager.core.models import BaseOrganisationModel
from nova_manager.components.users.models import Users


class UserExperience(BaseOrganisationModel):
    __tablename__ = "user_experience"

    user_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.pid"),
        nullable=False,
    )
    experience_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiences.pid"),
        nullable=False,
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
        Index(
            "idx_user_experience_user_org_app", "user_id", "organisation_id", "app_id"
        ),
        Index(
            "idx_user_experience_experience_org_app",
            "experience_id",
            "organisation_id",
            "app_id",
        ),
        Index("idx_user_experience_org_app", "organisation_id", "app_id"),
        Index(
            "idx_user_experience_assigned_org_app",
            "assigned_at",
            "organisation_id",
            "app_id",
        ),
        # User experiences ordered by assignment time (very common pattern)
        Index("idx_user_experience_user_assigned", "user_id", "assigned_at"),
    )

    # Relationships
    user = relationship(
        "Users", foreign_keys=[user_id], back_populates="user_experiences"
    )
    experience = relationship(
        "Experiences", foreign_keys=[experience_id], back_populates="user_experiences"
    )


class UserFeatureVariants(BaseOrganisationModel):
    __tablename__ = "user_feature_variants"

    user_id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), nullable=False)
    feature_id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), nullable=False)
    experience_id = Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    variant_name: Mapped[str] = mapped_column(String, nullable=False)
    variant_config: Mapped[dict] = mapped_column(
        JSON, server_default=func.json("{}"), nullable=False
    )

    __table_args__ = (
        # BUSINESS RULE: One variant per user per feature per org/app
        UniqueConstraint(
            "user_id",
            "feature_id",
            "organisation_id",
            "app_id",
            name="uq_user_feature_variants_user_feature_org_app",
        ),
        # Index for common queries
        Index(
            "idx_user_feature_variants_user_org_app",
            "user_id",
            "organisation_id",
            "app_id",
        ),
        Index("idx_user_feature_variants_user_feature", "user_id", "feature_id"),
        Index(
            "idx_user_feature_variants_feature_org_app",
            "feature_id",
            "organisation_id",
            "app_id",
        ),
        Index("idx_user_feature_variants_org_app", "organisation_id", "app_id"),
        Index(
            "idx_user_feature_variants_experience",
            "experience_id",
            "organisation_id",
            "app_id",
        ),
    )
