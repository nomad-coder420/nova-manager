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

    variants = relationship(
        "ExperienceFeatureVariants",
        foreign_keys="ExperienceFeatureVariants.personalisation_id",
        back_populates="personalisation",
        cascade="all, delete-orphan",
    )

    targeting_rules = relationship(
        "TargetingRulePersonalisations",
        foreign_keys="TargetingRulePersonalisations.personalisation_id",
        back_populates="personalisation",
        cascade="all, delete-orphan",
    )

    user_experience_personalisations = relationship(
        "UserExperiencePersonalisation",
        foreign_keys="UserExperiencePersonalisation.personalisation_id",
        back_populates="personalisation",
        cascade="all, delete-orphan",
    )


class ExperienceFeatureVariants(BaseModel):
    __tablename__ = "experience_feature_variants"

    personalisation_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personalisations.pid"),
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

    # Relationships
    personalisation = relationship(
        "Personalisations",
        foreign_keys=[personalisation_id],
        back_populates="variants",
    )

    experience_feature = relationship(
        "ExperienceFeatures",
        foreign_keys=[experience_feature_id],
        back_populates="variants",
    )


class TargetingRules(BaseModel):
    __tablename__ = "targeting_rules"

    experience_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiences.pid"),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rule_config: Mapped[dict] = mapped_column(
        JSON, server_default=func.json("{}"), nullable=False
    )
    rollout_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "experience_id", "priority", name="uq_targeting_rules_exp_prio"
        ),
        Index("idx_targeting_rules_experience_id", "experience_id"),
        Index("idx_targeting_rules_priority", "priority"),
    )

    # Relationships
    experience = relationship(
        "Experiences",
        foreign_keys=[experience_id],
        back_populates="targeting_rules",
    )

    personalisations = relationship(
        "TargetingRulePersonalisations",
        foreign_keys="TargetingRulePersonalisations.targeting_rule_id",
        back_populates="targeting_rule",
        cascade="all, delete-orphan",
    )

    segments = relationship(
        "TargetingRuleSegments",
        foreign_keys="TargetingRuleSegments.targeting_rule_id",
        back_populates="targeting_rule",
        cascade="all, delete-orphan",
    )


class TargetingRulePersonalisations(BaseModel):
    __tablename__ = "targeting_rule_personalisations"

    targeting_rule_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("targeting_rules.pid"),
        nullable=False,
    )
    personalisation_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personalisations.pid"),
        nullable=False,
        index=True,
    )
    target_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    # Relationships
    targeting_rule = relationship(
        "TargetingRules",
        foreign_keys=[targeting_rule_id],
        back_populates="personalisations",
    )

    personalisation = relationship(
        "Personalisations",
        foreign_keys=[personalisation_id],
        back_populates="targeting_rules",
    )


class TargetingRuleSegments(BaseModel):
    __tablename__ = "targeting_rule_segments"

    targeting_rule_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("targeting_rules.pid"),
        nullable=False,
    )
    segment_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("segments.pid"),
        nullable=False,
    )
    rule_config: Mapped[dict] = mapped_column(
        JSON, server_default=func.json("{}"), nullable=False
    )

    __table_args__ = (
        # Unique constraint: one relationship per experience-segment pair
        UniqueConstraint(
            "targeting_rule_id", "segment_id", name="uq_targeting_rule_segments_tr_seg"
        ),
        # Index for common queries
        Index("idx_targeting_rule_segments_targeting_rule_id", "targeting_rule_id"),
        Index("idx_targeting_rule_segments_segment_id", "segment_id"),
    )

    # Relationships
    targeting_rule = relationship(
        "TargetingRules",
        foreign_keys=[targeting_rule_id],
        back_populates="segments",
    )

    segment = relationship(
        "Segments",
        foreign_keys=[segment_id],
        back_populates="targeting_rules",
    )
