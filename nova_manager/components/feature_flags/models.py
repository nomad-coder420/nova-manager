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
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    keys_config: Mapped[dict] = mapped_column(
        JSON, server_default=func.json("{}"), nullable=False
    )
    type: Mapped[str] = mapped_column(String, nullable=False, default="")
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
    experiences = relationship(
        "ExperienceFeatures",
        foreign_keys="ExperienceFeatures.feature_id",
        back_populates="feature_flag",
        cascade="all, delete-orphan",
    )

    @property
    def default_variant(self):
        return {key: self.keys_config[key].get("default") for key in self.keys_config}
