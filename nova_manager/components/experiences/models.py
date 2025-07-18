from datetime import datetime
from uuid import UUID as UUIDType
from nova_manager.components.feature_flags.models import FeatureFlags
from sqlalchemy import (
    UUID,
    Boolean,
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
from nova_manager.components.segments.models import Segments
from nova_manager.components.campaigns.models import Campaigns


class Experiences(BaseOrganisationModel):
    __tablename__ = "experiences"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    status: Mapped[str] = mapped_column(String, nullable=False)

    # TODO: Verify these table args
    __table_args__ = (
        # Unique constraint: experience name must be unique within organization + app
        UniqueConstraint(
            "name", "organisation_id", "app_id", name="uq_experiences_name_org_app"
        ),
        # Index for common queries
        Index("idx_experiences_status_org_app", "status", "organisation_id", "app_id"),
        Index("idx_experiences_name_org_app", "name", "organisation_id", "app_id"),
        Index("idx_experiences_org_app", "organisation_id", "app_id"),
    )

    # Relationships
    feature_flags = relationship(
        "FeatureFlags",
        foreign_keys="FeatureFlags.experience_id",
        back_populates="experience",
    )

    personalisations = relationship(
        "Personalisations",
        foreign_keys="Personalisations.experience_id",
        back_populates="experience",
        cascade="all, delete-orphan",
    )

    experience_segments = relationship(
        "ExperienceSegments",
        foreign_keys="ExperienceSegments.experience_id",
        back_populates="experience",
        order_by="ExperienceSegments.priority.asc()",
        cascade="all, delete-orphan",
    )

    user_experience_personalisations = relationship(
        "UserExperiencePersonalisation",
        foreign_keys="UserExperiencePersonalisation.experience_id",
        back_populates="experience",
        cascade="all, delete-orphan",
    )


class Personalisations(BaseModel):
    __tablename__ = "personalisations"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    experience_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiences.pid"),
        nullable=False,
    )
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("name", "experience_id", name="uq_personalisations_name_exp"),
        Index("idx_personalisations_experience_id", "experience_id"),
    )

    # Relationships
    experience = relationship(
        "Experiences", foreign_keys=[experience_id], back_populates="personalisations"
    )

    feature_variants = relationship(
        "PersonalisationFeatureVariants",
        foreign_keys="PersonalisationFeatureVariants.personalisation_id",
        back_populates="personalisation",
        cascade="all, delete-orphan",
    )

    experience_segment_personalisations = relationship(
        "ExperienceSegmentPersonalisations",
        foreign_keys="ExperienceSegmentPersonalisations.personalisation_id",
        back_populates="personalisation",
        cascade="all, delete-orphan",
    )

    user_experience_personalisations = relationship(
        "UserExperiencePersonalisation",
        foreign_keys="UserExperiencePersonalisation.personalisation_id",
        back_populates="personalisation",
        cascade="all, delete-orphan",
    )


class PersonalisationFeatureVariants(BaseModel):
    __tablename__ = "personalisation_feature_variants"

    personalisation_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personalisations.pid"),
        nullable=False,
    )
    feature_variant_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("feature_variants.pid"),
        nullable=False,
    )

    # Relationships
    personalisation = relationship(
        "Personalisations",
        foreign_keys=[personalisation_id],
        back_populates="feature_variants",
    )
    feature_variant = relationship(
        "FeatureVariants",
        foreign_keys=[feature_variant_id],
        back_populates="personalisation_feature_variants",
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
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

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
        Index("idx_experience_segments_priority", "priority"),
    )

    # Relationships
    experience = relationship(
        "Experiences",
        foreign_keys=[experience_id],
        back_populates="experience_segments",
    )
    segment = relationship(
        "Segments",
        foreign_keys=[segment_id],
        back_populates="experience_segments",
    )

    personalisations = relationship(
        "ExperienceSegmentPersonalisations",
        foreign_keys="ExperienceSegmentPersonalisations.experience_segment_id",
        back_populates="experience_segment",
        cascade="all, delete-orphan",
    )


class ExperienceSegmentPersonalisations(BaseModel):
    __tablename__ = "experience_segment_personalisations"

    experience_segment_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experience_segments.pid"),
        nullable=False,
        index=True,
    )
    personalisation_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personalisations.pid"),
        nullable=False,
        index=True,
    )
    target_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    # Relationships
    experience_segment = relationship(
        "ExperienceSegments",
        foreign_keys=[experience_segment_id],
        back_populates="personalisations",
    )

    personalisation = relationship(
        "Personalisations",
        foreign_keys=[personalisation_id],
        back_populates="experience_segment_personalisations",
    )
