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
from nova_manager.components.experiences.models import Experiences


class Personalisations(BaseOrganisationModel):
    __tablename__ = "personalisations"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    experience_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiences.pid"),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rule_config: Mapped[dict] = mapped_column(
        JSON, server_default=func.json("{}"), nullable=False
    )
    rollout_percentage: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("name", "experience_id", name="uq_personalisations_name_exp"),
        UniqueConstraint(
            "experience_id", "priority", name="uq_personalisations_exp_prio"
        ),
        Index("idx_personalisations_experience_id", "experience_id"),
        Index("idx_personalisations_priority", "priority"),
    )

    # Relationships
    experience = relationship(
        "Experiences",
        foreign_keys=[experience_id],
        back_populates="personalisations",
    )

    experience_variants = relationship(
        "PersonalisationExperienceVariants",
        foreign_keys="PersonalisationExperienceVariants.personalisation_id",
        back_populates="personalisation",
        cascade="all, delete-orphan",
    )

    segment_rules = relationship(
        "PersonalisationSegmentRules",
        foreign_keys="PersonalisationSegmentRules.personalisation_id",
        back_populates="personalisation",
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

    feature_variants = relationship(
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


class PersonalisationExperienceVariants(BaseModel):
    __tablename__ = "personalisation_experience_variants"

    personalisation_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personalisations.pid"),
        nullable=False,
        index=True,
    )
    experience_variant_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experience_variants.pid"),
        nullable=False,
        index=True,
    )
    target_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    __table_args__ = (
        # Unique constraint: one relationship per personalisation-experience variant pair
        UniqueConstraint(
            "personalisation_id",
            "experience_variant_id",
            name="uq_personalisation_experience_variants_per_exp_var",
        ),
    )

    # Relationships
    personalisation = relationship(
        "Personalisations",
        foreign_keys=[personalisation_id],
        back_populates="experience_variants",
    )

    experience_variant = relationship(
        "ExperienceVariants",
        foreign_keys=[experience_variant_id],
        back_populates="personalisations",
    )


class PersonalisationSegmentRules(BaseModel):
    __tablename__ = "personalisation_segment_rules"

    personalisation_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personalisations.pid"),
        nullable=False,
        index=True,
    )
    segment_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("segments.pid"),
        nullable=False,
        index=True,
    )
    rule_config: Mapped[dict] = mapped_column(
        JSON, server_default=func.json("{}"), nullable=False
    )

    __table_args__ = (
        # Unique constraint: one relationship per experience-segment pair
        UniqueConstraint(
            "personalisation_id",
            "segment_id",
            name="uq_personalisation_segment_rules_tr_seg",
        ),
    )

    # Relationships
    personalisation = relationship(
        "Personalisations",
        foreign_keys=[personalisation_id],
        back_populates="segment_rules",
    )

    segment = relationship(
        "Segments",
        foreign_keys=[segment_id],
        back_populates="personalisations",
    )
