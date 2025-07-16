from datetime import datetime
from uuid import UUID as UUIDType
from sqlalchemy import (
    UUID,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nova_manager.core.models import BaseModel, BaseOrganisationModel
from nova_manager.components.user_experience.models import UserExperience
from nova_manager.components.segments.models import Segments
from nova_manager.components.campaigns.models import Campaigns


class Experiences(BaseOrganisationModel):
    __tablename__ = "experiences"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # TODO: Verify these table args
    __table_args__ = (
        # Unique constraint: experience name must be unique within organization + app
        UniqueConstraint(
            "name", "organisation_id", "app_id", name="uq_experiences_name_org_app"
        ),
        # Priority must be unique within org/app (business rule)
        UniqueConstraint(
            "priority",
            "organisation_id",
            "app_id",
            name="uq_experiences_priority_org_app",
        ),
        # Index for common queries
        Index("idx_experiences_status_org_app", "status", "organisation_id", "app_id"),
        Index(
            "idx_experiences_priority_org_app", "priority", "organisation_id", "app_id"
        ),
        Index("idx_experiences_name_org_app", "name", "organisation_id", "app_id"),
        Index(
            "idx_experiences_updated_org_app",
            "last_updated_at",
            "organisation_id",
            "app_id",
        ),
        Index("idx_experiences_org_app", "organisation_id", "app_id"),
        # ORDERING INDEXES: For efficient sorting
        Index(
            "idx_experiences_priority_created_org_app",
            "priority",
            "created_at",
            "organisation_id",
            "app_id",
        ),
        # For reverse chronological ordering (most common pattern)
        Index("idx_experiences_created_desc", "created_at", postgresql_using="btree"),
    )

    # Relationships
    feature_variants = relationship(
        "FeatureVariants",
        foreign_keys="FeatureVariants.experience_id",
        back_populates="experience",
        cascade="all, delete-orphan",
    )

    experience_segments = relationship(
        "ExperienceSegments",
        foreign_keys="ExperienceSegments.experience_id",
        back_populates="experience",
        cascade="all, delete-orphan",
    )

    user_experiences = relationship(
        "UserExperience",
        foreign_keys="UserExperience.experience_id",
        back_populates="experience",
        cascade="all, delete-orphan",
    )

    experience_campaigns = relationship(
        "ExperienceCampaigns",
        foreign_keys="ExperienceCampaigns.experience_id",
        back_populates="experience",
        cascade="all, delete-orphan",
    )

    # Many-to-many relationship with campaigns through junction table
    campaigns = relationship(
        "Campaigns",
        secondary="experience_campaigns",
        back_populates="experiences",
        viewonly=True,
    )


class ExperienceCampaigns(BaseModel):
    __tablename__ = "experience_campaigns"

    experience_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiences.pid"),
        nullable=False,
    )
    campaign_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.pid"),
        nullable=False,
    )
    target_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # Unique constraint: one relationship per experience-campaign pair
        UniqueConstraint(
            "experience_id", "campaign_id", name="uq_experience_campaigns_exp_camp"
        ),
        # Check constraint: target_percentage must be between 0 and 100
        CheckConstraint(
            "target_percentage >= 0 AND target_percentage <= 100",
            name="ck_experience_campaigns_valid_percentage",
        ),
        # Index for common queries
        Index("idx_experience_campaigns_experience_id", "experience_id"),
        Index("idx_experience_campaigns_campaign_id", "campaign_id"),
    )

    # Relationships
    experience = relationship(
        "Experiences",
        foreign_keys=[experience_id],
        back_populates="experience_campaigns",
    )
    campaign = relationship(
        "Campaigns",
        foreign_keys=[campaign_id],
        back_populates="experience_campaigns",
    )


class ExperienceSegments(BaseModel):
    __tablename__ = "experience_segments"

    experience_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiences.pid"),
        nullable=False,
    )
    segment_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("segments.pid"),
        nullable=False,
    )
    target_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    __table_args__ = (
        # Unique constraint: one relationship per experience-segment pair
        UniqueConstraint(
            "experience_id", "segment_id", name="uq_experience_segments_exp_seg"
        ),
        # Check constraint: target_percentage must be between 0 and 100
        CheckConstraint(
            "target_percentage >= 0 AND target_percentage <= 100",
            name="ck_experience_segments_valid_percentage",
        ),
        # Index for common queries
        Index("idx_experience_segments_experience_id", "experience_id"),
        Index("idx_experience_segments_segment_id", "segment_id"),
    )

    # Relationships
    experience = relationship(
        "Experiences",
        foreign_keys=[experience_id],
        back_populates="experience_segments",
    )
    segment = relationship(
        "Segments", foreign_keys=[segment_id], back_populates="experience_segments"
    )
