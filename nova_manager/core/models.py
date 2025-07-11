from uuid import UUID as UUIDType, uuid4
from datetime import datetime
from sqlalchemy import UUID, Integer, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(
        Integer,
        autoincrement=True,
        unique=True,
        index=True,
        primary_key=True,
        nullable=False,
    )
    pid: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        default=uuid4,
        index=True,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BaseOrganisationModel(BaseModel):
    __abstract__ = True

    organisation_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    app_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
