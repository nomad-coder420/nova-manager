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
    segment_name: Mapped[str | None] = mapped_column(String, nullable=True)
    segment_id: Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    experience_segment_id: Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
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
        # BUSINESS RULE: One personalisation assignment per user-experience pair within org/app scope
        # Fixed to include organisation_id and app_id for proper scoping
        UniqueConstraint(
            "user_id",
            "experience_id",
            "organisation_id",
            "app_id",
            name="uq_user_experience_user_exp_org_app",
        ),
        # PRIMARY QUERY OPTIMIZATION: Covers main query pattern from get_user_experiences_personalisations
        # Query: user_id = ? AND organisation_id = ? AND app_id = ? AND experience_id IN (?)
        Index(
            "idx_user_experience_main_query",
            "user_id",
            "organisation_id",
            "app_id",
            "experience_id",
        ),
        # EXPERIENCE-BASED QUERIES: For queries filtering by experience within org/app
        Index(
            "idx_user_experience_experience_org_app",
            "experience_id",
            "organisation_id",
            "app_id",
        ),
        # TIME-BASED QUERIES: For analytics and reporting by assignment time
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
