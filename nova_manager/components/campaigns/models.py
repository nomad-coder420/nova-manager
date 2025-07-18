from datetime import datetime
from nova_manager.core.models import BaseOrganisationModel
from sqlalchemy import JSON, DateTime, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Campaigns(BaseOrganisationModel):
    __tablename__ = "campaigns"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    status: Mapped[str] = mapped_column(String, nullable=False)

    # TODO: Define this into proper columns later
    rule_config: Mapped[dict] = mapped_column(
        JSON, server_default=func.json("{}"), nullable=False
    )

    launched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        # Unique constraint: campaign name must be unique within organization + app
        UniqueConstraint(
            "name", "organisation_id", "app_id", name="uq_campaigns_name_org_app"
        ),
        # Index for common queries
        Index("idx_campaigns_org_app", "organisation_id", "app_id"),
    )
