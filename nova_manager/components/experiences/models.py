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
from nova_manager.components.personalisations.models import Personalisations
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
    features: Mapped[list["ExperienceFeatures"]] = relationship(
        "ExperienceFeatures",
        foreign_keys="ExperienceFeatures.experience_id",
        back_populates="experience",
    )

    variants = relationship(
        "ExperienceVariants",
        foreign_keys="ExperienceVariants.experience_id",
        back_populates="experience",
        cascade="all, delete-orphan",
    )

    personalisations: Mapped[list[Personalisations]] = relationship(
        "Personalisations",
        foreign_keys="Personalisations.experience_id",
        back_populates="experience",
        order_by="Personalisations.priority.desc()",
        cascade="all, delete-orphan",
    )

    user_experience_personalisations = relationship(
        "UserExperience",
        foreign_keys="UserExperience.experience_id",
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


class ExperienceVariants(BaseModel):
    __tablename__ = "experience_variants"

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
        UniqueConstraint(
            "name", "experience_id", name="uq_experience_variants_name_exp"
        ),
        Index("idx_experience_variants_experience_id", "experience_id"),
    )

    # Relationships
    experience = relationship(
        "Experiences", foreign_keys=[experience_id], back_populates="variants"
    )

    feature_variants: Mapped[list["ExperienceFeatureVariants"]] = relationship(
        "ExperienceFeatureVariants",
        foreign_keys="ExperienceFeatureVariants.experience_variant_id",
        back_populates="experience_variant",
        cascade="all, delete-orphan",
    )

    personalisations = relationship(
        "PersonalisationExperienceVariants",
        foreign_keys="PersonalisationExperienceVariants.experience_variant_id",
        back_populates="experience_variant",
        cascade="all, delete-orphan",
    )


class ExperienceFeatureVariants(BaseModel):
    __tablename__ = "experience_feature_variants"

    experience_variant_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experience_variants.pid"),
        nullable=False,
    )
    experience_feature_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experience_features.pid"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    config: Mapped[dict] = mapped_column(
        JSON, server_default=func.json("{}"), nullable=False
    )

    __table_args__ = (
        Index(
            "idx_experience_feature_variants_experience_feature_id",
            "experience_feature_id",
        ),
    )

    # Relationships
    experience_variant = relationship(
        "ExperienceVariants",
        foreign_keys=[experience_variant_id],
        back_populates="feature_variants",
    )

    experience_feature = relationship(
        "ExperienceFeatures",
        foreign_keys=[experience_feature_id],
        back_populates="variants",
    )
