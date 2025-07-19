from sqlalchemy import JSON, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


from nova_manager.core.models import BaseOrganisationModel


class Segments(BaseOrganisationModel):
    __tablename__ = "segments"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")

    # TODO: Define this into proper columns later
    rule_config: Mapped[dict] = mapped_column(
        JSON, server_default=func.json("{}"), nullable=False
    )

    __table_args__ = (
        # Unique constraint: segment name must be unique within organization + app
        UniqueConstraint(
            "name", "organisation_id", "app_id", name="uq_segments_name_org_app"
        ),
        # Index for common queries
        Index("idx_segments_org_app", "organisation_id", "app_id"),
    )

    # Relationships
    experience_segments = relationship(
        "ExperienceSegments",
        foreign_keys="ExperienceSegments.segment_id",
        back_populates="segment",
        cascade="all, delete-orphan",
    )

    @property
    def experience_count(self):
        return len(self.experience_segments)
