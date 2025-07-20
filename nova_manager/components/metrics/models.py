from uuid import UUID as UUIDType
from sqlalchemy import JSON, UUID, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from nova_manager.core.models import BaseModel, BaseOrganisationModel


class Metrics(BaseOrganisationModel):
    __tablename__ = "metrics"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    type: Mapped[str] = mapped_column(String, nullable=False, default="")
    config: Mapped[dict] = mapped_column(
        JSON, nullable=False, server_default=func.json("{}")
    )

    __table_args__ = (
        # Index for common queries
        Index("idx_metrics_org_app", "organisation_id", "app_id"),
        Index("idx_metrics_name_org_app", "name", "organisation_id", "app_id"),
    )


class ExperienceMetrics(BaseModel):
    __tablename__ = "experience_metrics"

    experience_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiences.pid"),
        nullable=False,
        index=True,
    )

    metric_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metrics.pid"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        # Unique constraint: one experience metric pair
        UniqueConstraint(
            "experience_id", "metric_id", name="uq_experience_metrics_exp_metric"
        ),
    )


class TargetingRuleMetrics(BaseModel):
    __tablename__ = "targeting_rule_metrics"

    targeting_rule_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("targeting_rules.pid"),
        nullable=False,
        index=True,
    )

    metric_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metrics.pid"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        # Unique constraint: one experience segment metric pair
        UniqueConstraint(
            "targeting_rule_id",
            "metric_id",
            name="uq_experience_segment_metrics_tr_metric",
        ),
    )


class PersonalisationMetrics(BaseModel):
    __tablename__ = "personalisation_metrics"

    personalisation_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personalisations.pid"),
        nullable=False,
        index=True,
    )

    metric_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metrics.pid"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        # Unique constraint: one personalisation metric pair
        UniqueConstraint(
            "personalisation_id",
            "metric_id",
            name="uq_personalisation_metrics_pers_metric",
        ),
    )
