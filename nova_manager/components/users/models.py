from sqlalchemy import JSON, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


from nova_manager.core.models import BaseOrganisationModel


class Users(BaseOrganisationModel):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String, nullable=False)
    # TODO: Define this into proper tables / columns later
    user_profile: Mapped[dict] = mapped_column(
        JSON, server_default=func.json("{}"), nullable=False
    )

    # Unique constraint: user_id must be unique within organization + app
    __table_args__ = (
        UniqueConstraint(
            "user_id", "organisation_id", "app_id", name="uq_users_user_id_org_app"
        ),
        # Index for common queries
        Index("idx_users_user_id_org_app", "user_id", "organisation_id", "app_id"),
        Index("idx_users_org_app", "organisation_id", "app_id"),
    )

    # Relationships
    user_experiences = relationship(
        "UserExperience",
        foreign_keys="UserExperience.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
