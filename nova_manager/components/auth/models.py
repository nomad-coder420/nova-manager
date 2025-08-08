from uuid import UUID as UUIDType
from sqlalchemy import UUID, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nova_manager.core.models import BaseModel


class Organisation(BaseModel):
    __tablename__ = "organisations"

    name: Mapped[str] = mapped_column(String, nullable=False)

    apps: Mapped[list["App"]] = relationship(
        "App",
        foreign_keys="App.organisation_id",
        back_populates="organisation",
        cascade="all, delete-orphan",
    )

    auth_users: Mapped[list["AuthUser"]] = relationship(
        "AuthUser",
        foreign_keys="AuthUser.organisation_id",
        back_populates="organisation",
        cascade="all, delete-orphan",
    )


class App(BaseModel):
    __tablename__ = "apps"

    name: Mapped[str] = mapped_column(String, nullable=False)
    organisation_id: Mapped[UUIDType] = mapped_column(UUID, ForeignKey("organisations.pid"), nullable=False)

    organisation = relationship(
        "Organisation",
        foreign_keys=[organisation_id],
        back_populates="apps",
    )


class AuthUser(BaseModel):
    __tablename__ = "auth_users"

    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)

    organisation_id: Mapped[UUIDType] = mapped_column(UUID, ForeignKey("organisations.pid"), nullable=False)

    organisation = relationship(
        "Organisation",
        foreign_keys=[organisation_id],
        back_populates="auth_users",
    )
