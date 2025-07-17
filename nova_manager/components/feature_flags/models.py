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

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    keys_config: Mapped[dict] = mapped_column(
        JSON, server_default=func.json("{}"), nullable=False
    )
    type: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    experience_id: Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiences.pid"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        # Unique constraint: feature flag name must be unique within organization + app
        UniqueConstraint(
            "name", "organisation_id", "app_id", name="uq_feature_flags_name_org_app"
        ),
        # Index for common queries
        Index(
            "idx_feature_flags_active_org_app", "is_active", "organisation_id", "app_id"
        ),
        Index("idx_feature_flags_org_app", "organisation_id", "app_id"),
    )

    # Relationships
    experience = relationship(
        "Experiences", foreign_keys=[experience_id], back_populates="feature_flags"
    )

    variants = relationship(
        "FeatureVariants",
        foreign_keys="FeatureVariants.feature_id",
        back_populates="feature_flag",
        cascade="all, delete-orphan",
    )

    variant_templates = relationship(
        "FeatureVariantsTemplates",
        foreign_keys="FeatureVariantsTemplates.feature_id",
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
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    config: Mapped[dict] = mapped_column(
        JSON, server_default=func.json("{}"), nullable=False
    )

    # Unique constraint: variant name must be unique within a feature flag
    __table_args__ = (
        UniqueConstraint("name", "feature_id", name="uq_feature_variants_name_feature"),
        # Index for common queries
        Index("idx_feature_variants_feature_id", "feature_id"),
    )

    # Relationships
    feature_flag = relationship(
        "FeatureFlags", foreign_keys=[feature_id], back_populates="variants"
    )

    personalisation_feature_variants = relationship(
        "PersonalisationFeatureVariants",
        foreign_keys="PersonalisationFeatureVariants.feature_variant_id",
        back_populates="feature_variant",
        cascade="all, delete-orphan",
    )


class FeatureVariantsTemplates(BaseModel):
    __tablename__ = "feature_variants_templates"

    feature_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("feature_flags.pid"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    config: Mapped[dict] = mapped_column(
        JSON, server_default=func.json("{}"), nullable=False
    )

    # Unique constraint: template name must be unique within a feature flag
    __table_args__ = (
        UniqueConstraint(
            "name", "feature_id", name="uq_feature_variants_templates_name_feature"
        ),
        # Index for common queries
        Index("idx_feature_variants_templates_feature_id", "feature_id"),
    )

    # Relationships
    feature_flag = relationship(
        "FeatureFlags", foreign_keys=[feature_id], back_populates="variant_templates"
    )
