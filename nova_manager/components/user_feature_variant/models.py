from uuid import UUID as UUIDType
from sqlalchemy import UUID, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nova_manager.core.models import BaseOrganisationModel
from nova_manager.components.users.models import Users


class UserFeatureVariants(BaseOrganisationModel):
    __tablename__ = "user_feature_variants"

    user_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.pid"), nullable=False, index=True
    )
    feature_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("feature_flags.pid"), nullable=False, index=True
    )
    variant_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("feature_variants.pid"),
        nullable=False,
        index=True,
    )
    # variant_name: Mapped[UUIDType] = mapped_column(
    #     UUID(as_uuid=True),
    #     ForeignKey("feature_variants.pid"),
    #     nullable=False,
    #     index=True,
    # )
    # variant_config: Mapped[dict] = mapped_column(
    #     JSON, server_default=func.json("{}"), nullable=False
    # )

    # Unique constraint: one user can have only one variant assignment per feature
    __table_args__ = (
        UniqueConstraint(
            "user_id", "feature_id", name="uq_user_feature_variants_user_feature"
        ),
        # Composite indexes for common queries
        Index("idx_user_feature_variants_user_id", "user_id"),
        Index("idx_user_feature_variants_feature_id", "feature_id"),
        Index("idx_user_feature_variants_variant_id", "variant_id"),
        Index("idx_user_feature_variants_org_app", "organisation_id", "app_id"),
    )

    # Relationships
    user = relationship(
        "Users", foreign_keys=[user_id], back_populates="user_feature_variants"
    )

    feature_flag = relationship(
        "FeatureFlags",
        foreign_keys=[feature_id],
        back_populates="user_feature_variants",
    )

    variant = relationship(
        "FeatureVariants",
        foreign_keys=[variant_id],
        back_populates="user_feature_variants",
    )
