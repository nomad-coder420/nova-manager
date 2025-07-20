from datetime import datetime
from uuid import UUID as UUIDType
from sqlalchemy import (
    JSON,
    UUID,
    Boolean,
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
from nova_manager.components.feature_flags.models import FeatureFlags


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
    features = relationship(
        "ExperienceFeatures",
        foreign_keys="ExperienceFeatures.experience_id",
        back_populates="experience",
    )

    personalisations = relationship(
        "Personalisations",
        foreign_keys="Personalisations.experience_id",
        back_populates="experience",
        cascade="all, delete-orphan",
    )

    targeting_rules = relationship(
        "TargetingRules",
        foreign_keys="TargetingRules.experience_id",
        back_populates="experience",
        order_by="TargetingRules.priority.asc()",
        cascade="all, delete-orphan",
    )

    user_experience_personalisations = relationship(
        "UserExperiencePersonalisation",
        foreign_keys="UserExperiencePersonalisation.experience_id",
        back_populates="experience",
        cascade="all, delete-orphan",
    )


class ExperienceFeatures(BaseModel):
    __tablename__ = "experience_features"

    experience_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiences.pid"),
        nullable=False,
    )
    feature_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("feature_flags.pid"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "experience_id", "feature_id", name="uq_experience_features_exp_feat"
        ),
        Index("idx_experience_features_experience_id", "experience_id"),
        Index("idx_experience_features_feature_flag_id", "feature_id"),
    )

    # Relationships
    experience = relationship(
        "Experiences",
        foreign_keys=[experience_id],
        back_populates="features",
    )

    feature_flag = relationship(
        "FeatureFlags",
        foreign_keys=[feature_id],
        back_populates="experiences",
    )

    variants = relationship(
        "ExperienceFeatureVariants",
        foreign_keys="ExperienceFeatureVariants.experience_feature_id",
        back_populates="experience_feature",
        cascade="all, delete-orphan",
    )
