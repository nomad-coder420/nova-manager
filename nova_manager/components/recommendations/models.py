from uuid import UUID as UUIDType
from sqlalchemy import JSON, UUID, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from nova_manager.core.models import BaseOrganisationModel


class Recommendations(BaseOrganisationModel):
    __tablename__ = "recommendations"

    experience_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("experiences.pid"), nullable=False
    )
    personalisation_data: Mapped[dict] = mapped_column(
        JSON, default=func.json("{}"), nullable=False
    )
