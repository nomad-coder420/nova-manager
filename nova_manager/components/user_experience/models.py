from datetime import datetime
from typing import Optional
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


class UserExperiencePersonalisation(BaseOrganisationModel):
    __tablename__ = "user_experience_personalisation"

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
    personalisation_id: Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personalisations.pid"),
        nullable=True,
    )
    segment_id: Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("segments.pid"),
        nullable=True,
    )
    experience_segment_personalisation_id: Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    evaluation_reason: Mapped[str] = mapped_column(String, nullable=False)

    # TODO: Review these table args
    __table_args__ = (
        # Unique constraint: one specific personalisation assignment per user-experience pair
        UniqueConstraint(
            "user_id",
            "experience_id",
            "personalisation_id",
            name="uq_user_experience_user_exp_pers",
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
        "Users",
        foreign_keys=[user_id],
        back_populates="user_experience_personalisations",
    )
    experience = relationship(
        "Experiences",
        foreign_keys=[experience_id],
        back_populates="user_experience_personalisations",
    )
    personalisation = relationship(
        "Personalisations",
        foreign_keys=[personalisation_id],
        back_populates="user_experience_personalisations",
    )
    segment = relationship(
        "Segments",
        foreign_keys=[segment_id],
    )


# class UserFeatureVariants(BaseOrganisationModel):
#     __tablename__ = "user_feature_variants"

#     user_id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), nullable=False)
#     feature_id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), nullable=False)
#     experience_id: Mapped[UUIDType | None] = mapped_column(
#         UUID(as_uuid=True), nullable=True
#     )
#     variant_id: Mapped[UUIDType | None] = mapped_column(
#         UUID(as_uuid=True), nullable=True
#     )
#     variant_name: Mapped[str] = mapped_column(String, nullable=False)
#     variant_config: Mapped[dict] = mapped_column(
#         JSON, server_default=func.json("{}"), nullable=False
#     )
#     personalisation_id: Mapped[UUIDType | None] = mapped_column(
#         UUID(as_uuid=True), nullable=True
#     )
#     segment_id: Mapped[UUIDType | None] = mapped_column(
#         UUID(as_uuid=True), nullable=True
#     )
#     experience_segment_personalisation_id: Mapped[UUIDType | None] = mapped_column(
#         UUID(as_uuid=True), nullable=True
#     )
#     experience_segment_id: Mapped[UUIDType | None] = mapped_column(
#         UUID(as_uuid=True), nullable=True
#     )
#     personalisation_feature_variant_id: Mapped[UUIDType | None] = mapped_column(
#         UUID(as_uuid=True), nullable=True
#     )
#     evaluation_reason: Mapped[str] = mapped_column(String, nullable=False)
#     variant_assigned_at: Mapped[datetime] = mapped_column(
#         DateTime(timezone=True),
#         nullable=False,
#         server_default=func.now(),
#     )

#     __table_args__ = (
#         # BUSINESS RULE: One variant per user per feature per org/app
#         UniqueConstraint(
#             "user_id",
#             "feature_id",
#             "organisation_id",
#             "app_id",
#             name="uq_user_feature_variants_user_feature_org_app",
#         ),
#     )
