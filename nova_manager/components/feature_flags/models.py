from uuid import UUID as UUIDType
from sqlalchemy import (
    JSON,
    UUID,
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nova_manager.core.models import BaseModel, BaseOrganisationModel


class FeatureFlags(BaseOrganisationModel):
    __tablename__ = "feature_flags"

    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    keys_config: Mapped[dict] = mapped_column(
        JSON, server_default=func.json("{}"), nullable=False
    )
    # TODO: Add type field here
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Unique constraint: feature flag name must be unique within organization + app
    __table_args__ = (
        UniqueConstraint(
            "name", "organisation_id", "app_id", name="uq_feature_flags_name_org_app"
        ),
        # Index for common queries
        Index(
            "idx_feature_flags_active_org_app", "is_active", "organisation_id", "app_id"
        ),
    )

    # Relationships
    variants = relationship(
        "FeatureVariants",
        foreign_keys="FeatureVariants.feature_id",
        back_populates="feature_flag",
        cascade="all, delete-orphan",
    )

    targeting_rules = relationship(
        "TargetingRules",
        foreign_keys="TargetingRules.feature_id",
        back_populates="feature_flag",
        cascade="all, delete-orphan",
        order_by="TargetingRules.priority",
    )

    individual_targeting = relationship(
        "IndividualTargeting",
        foreign_keys="IndividualTargeting.feature_id",
        back_populates="feature_flag",
        cascade="all, delete-orphan",
    )

    @property
    def default_variant(self):
        return {key: self.keys_config[key].get("default") for key in self.keys_config}


class FeatureVariants(BaseModel):
    __tablename__ = "feature_variants"

    feature_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("feature_flags.pid"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    config: Mapped[dict] = mapped_column(
        JSON, server_default=func.json("{}"), nullable=False
    )

    # Unique constraint: variant name must be unique within a feature flag
    __table_args__ = (
        UniqueConstraint("name", "feature_id", name="uq_feature_variants_name_feature"),
    )

    # Relationships
    feature_flag = relationship(
        "FeatureFlags", foreign_keys=[feature_id], back_populates="variants"
    )


class TargetingRules(BaseModel):
    __tablename__ = "targeting_rules"

    feature_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("feature_flags.pid"),
        nullable=False,
        index=True,
    )
    # TODO: Define this into proper columns later
    rule_config: Mapped[dict] = mapped_column(
        JSON, server_default=func.json("{}"), nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False)

    # Unique constraint: priority must be unique within a feature flag
    __table_args__ = (
        UniqueConstraint(
            "feature_id", "priority", name="uq_targeting_rules_feature_priority"
        ),
        # Index for priority-based queries
        Index("idx_targeting_rules_feature_priority", "feature_id", "priority"),
    )

    # Relationships
    feature_flag = relationship(
        "FeatureFlags", foreign_keys=[feature_id], back_populates="targeting_rules"
    )


class IndividualTargeting(BaseModel):
    __tablename__ = "individual_targeting"

    feature_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("feature_flags.pid"),
        nullable=False,
        index=True,
    )
    # TODO: Define this into proper rows & columns later
    rule_config: Mapped[dict] = mapped_column(
        JSON, server_default=func.json("{}"), nullable=False
    )

    # Relationships
    feature_flag = relationship(
        "FeatureFlags",
        foreign_keys=[feature_id],
        back_populates="individual_targeting",
    )
