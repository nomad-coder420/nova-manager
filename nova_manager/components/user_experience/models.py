from datetime import datetime
from uuid import UUID as UUIDType
from nova_manager.components.user_experience.schemas import (
    ExperienceFeatureAssignment,
)
from sqlalchemy import (
    JSON,
    UUID,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nova_manager.core.models import BaseOrganisationModel
from nova_manager.components.users.models import Users
from nova_manager.components.experiences.models import Experiences
from nova_manager.components.personalisations.models import Personalisations


class UserExperience(BaseOrganisationModel):
    __tablename__ = "user_experience"

    user_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.pid"),
        nullable=False,
    )
    experience_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiences.pid"),
        nullable=False,
    )
    personalisation_id: Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personalisations.pid"),
        nullable=True,
    )
    personalisation_name: Mapped[str | None] = mapped_column(String, nullable=True)
    experience_variant_id: Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    features: Mapped[dict[str, ExperienceFeatureAssignment]] = mapped_column(
        JSON, server_default=func.json("{}"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    evaluation_reason: Mapped[str] = mapped_column(String, nullable=False)

    # TODO: Review these table args
    __table_args__ = (
        # If personalisation is reassigned for an experience, we add a new row to this table.
        # Active personalisation for experience is the last entry in the table.
        # UniqueConstraint(
        #     "user_id",
        #     "experience_id",
        #     "organisation_id",
        #     "app_id",
        #     name="uq_user_experience_user_exp_org_app",
        # ),
        # PRIMARY COMPOSITE INDEX: Covers ALL main query patterns efficiently
        # Supports: 1) WHERE user_id = ? AND organisation_id = ? AND app_id = ? AND experience_id IN (?)
        #           2) WHERE user_id = ? AND organisation_id = ? AND app_id = ?
        #           3) ORDER BY experience_id, id DESC for DISTINCT ON (experience_id)
        #           4) Any prefix combination of these columns
        Index(
            "idx_user_experience_user_org_app_exp_id",
            "user_id",
            "organisation_id",
            "app_id",
            "experience_id",
            "id",
        ),
        # EXPERIENCE-BASED QUERIES: For queries filtering by experience within org/app
        Index(
            "idx_user_experience_experience_org_app",
            "experience_id",
            "organisation_id",
            "app_id",
        ),
        # TIME-BASED QUERIES: For analytics and reporting by assignment time
        Index(
            "idx_user_experience_assigned_org_app",
            "assigned_at",
            "organisation_id",
            "app_id",
        ),
        # USER-TIME QUERIES: User experiences ordered by assignment time (common analytics pattern)
        Index("idx_user_experience_user_assigned", "user_id", "assigned_at"),
    )

    # Relationships
    user: Mapped[Users] = relationship(
        "Users",
        foreign_keys=[user_id],
        back_populates="user_experience_personalisations",
    )
    experience: Mapped[Experiences] = relationship(
        "Experiences",
        foreign_keys=[experience_id],
        back_populates="user_experience_personalisations",
    )
    personalisation: Mapped[Personalisations] = relationship(
        "Personalisations",
        foreign_keys=[personalisation_id],
        back_populates="user_experience_personalisations",
    )
