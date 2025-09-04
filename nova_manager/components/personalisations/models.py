from datetime import datetime
from uuid import UUID as UUIDType
from sqlalchemy import (
    JSON,
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
from nova_manager.components.metrics.models import PersonalisationMetrics


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
    # Flag to indicate existing user assignments should be re-evaluated
    reassign: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # Active flag for enabling/disabling personalisation
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        onupdate=func.now(),  # Auto-update on every modification
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("name", "experience_id", name="uq_personalisations_name_exp"),
        UniqueConstraint(
            "experience_id", "priority", name="uq_personalisations_exp_prio"
        ),
        # COMPREHENSIVE INDEX: Covers experience queries + active filtering + priority ordering
        # Supports: 1) WHERE experience_id = ? (replaces old idx_personalisations_experience_id)
        #           2) WHERE experience_id = ? AND is_active = ?
        #           3) WHERE experience_id = ? AND is_active = True ORDER BY priority DESC
        #           4) All prefix combinations of these columns
        Index(
            "idx_personalisations_exp_active_priority",
            "experience_id",
            "is_active",
            "priority",
        ),
        # ORG/APP SEARCH OPTIMIZATION: For search queries and listings
        # Supports: WHERE organisation_id = ? AND app_id = ? [AND name/description ILIKE ?]
        #           ORDER BY created_at/name/priority
        Index(
            "idx_personalisations_org_app_search",
            "organisation_id",
            "app_id",
            "name",  # For name-based ordering and search optimization
            "created_at",  # For time-based ordering (most common)
        ),
    )

    # Relationships
    experience = relationship(
        "Experiences",
        foreign_keys=[experience_id],
        back_populates="personalisations",
    )

    experience_variants: Mapped[list["PersonalisationExperienceVariants"]] = (
        relationship(
            "PersonalisationExperienceVariants",
            foreign_keys="PersonalisationExperienceVariants.personalisation_id",
            back_populates="personalisation",
            cascade="all, delete-orphan",
        )
    )

    segment_rules = relationship(
        "PersonalisationSegmentRules",
        foreign_keys="PersonalisationSegmentRules.personalisation_id",
        back_populates="personalisation",
        cascade="all, delete-orphan",
    )

    user_experience_personalisations = relationship(
        "UserExperience",
        foreign_keys="UserExperience.personalisation_id",
        back_populates="personalisation",
        cascade="all, delete-orphan",
    )

    # Metrics relationship
    metrics: Mapped[list[PersonalisationMetrics]] = relationship(
        "PersonalisationMetrics",
        foreign_keys="PersonalisationMetrics.personalisation_id",
        cascade="all, delete-orphan",
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
        # Check constraint to ensure percentage is between 0 and 100
        CheckConstraint(
            "target_percentage >= 0 AND target_percentage <= 100",
            name="ck_target_percentage_range",
        ),
        # Check constraint to ensure sum equals 100% per experience variant
        CheckConstraint(
            """
            100 = (
                SELECT SUM(target_percentage) 
                FROM personalisation_experience_variants pev2 
                WHERE pev2.experience_variant_id = personalisation_experience_variants.experience_variant_id
            )
            """,
            name="ck_experience_variant_percentages_sum_100",
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
