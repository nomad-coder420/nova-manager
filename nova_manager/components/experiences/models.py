from datetime import datetime
from uuid import UUID as UUIDType
from sqlalchemy import (
    UUID,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from nova_manager.core.models import BaseModel, BaseOrganisationModel
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Experiences(BaseOrganisationModel):
    __tablename__ = "experiences"

    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)

    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # TODO: Verify these table args
    __table_args__ = (
        # Unique constraint: feature flag name must be unique within organization + app
        UniqueConstraint(
            "name", "organisation_id", "app_id", name="uq_experiences_name_org_app"
        ),
        # Index for common queries
        Index("idx_experiences_status_org_app", "status", "organisation_id", "app_id"),
        Index(
            "idx_experiences_priority_org_app", "priority", "organisation_id", "app_id"
        ),
        Index(
            "idx_experiences_updated_org_app",
            "last_updated_at",
            "organisation_id",
            "app_id",
        ),
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


class ExperienceSegments(BaseModel):
    __tablename__ = "experience_segments"

    experience_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiences.pid"),
        nullable=False,
        index=True,
    )
    segment_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("segments.pid"),
        nullable=False,
        index=True,
    )
    target_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    __table_args__ = (
        # Unique constraint: one relationship per experience-segment pair
        UniqueConstraint(
            "experience_id", "segment_id", name="uq_experience_segments_exp_seg"
        ),
        # Index for common queries
        Index("idx_experience_segments_experience", "experience_id"),
        Index("idx_experience_segments_segment", "segment_id"),
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
