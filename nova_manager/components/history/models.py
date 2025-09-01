from uuid import UUID as UUIDType
from datetime import datetime
from sqlalchemy import String, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from nova_manager.core.models import BaseModel


class HistoryLog(BaseModel):
    """
    Central history log for tracking object changes.
    """
    __tablename__ = "history_log"

    action: Mapped[str] = mapped_column(String, nullable=False)
    object_type: Mapped[str] = mapped_column(String, nullable=False)
    object_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
