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
from sqlalchemy.orm import Mapped, mapped_column


from nova_manager.core.models import BaseOrganisationModel


class Segments(BaseOrganisationModel):
    __tablename__ = "segments"

    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String, nullable=False, server_default="")

    # TODO: Define this into proper columns later
    rule_config: Mapped[dict] = mapped_column(
        JSON, server_default=func.json("{}"), nullable=False
    )
