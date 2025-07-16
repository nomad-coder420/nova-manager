from enum import Enum
from uuid import uuid4
from fastapi_users.db import SQLAlchemyBaseUserTable
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Integer, Enum as SAEnum
from nova_manager.components.auth.enums import OrganisationRole, AppRole
from nova_manager.core.models import Base, BaseModel

# Enums for roles defined in components/auth/enums.py


class AuthUser(Base, SQLAlchemyBaseUserTable[int]):
    __tablename__ = "auth_user"
    id: Mapped[int] = mapped_column(primary_key=True)
    organisation_memberships = relationship(
        "UserOrganisationMembership", back_populates="user", cascade="all, delete-orphan"
    )
    app_memberships = relationship(
        "UserAppMembership", back_populates="user", cascade="all, delete-orphan"
    )


class Organisation(BaseModel):
    __tablename__ = "organisations"
    # Override pid to string UUID so FKs align
    pid: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=lambda: str(uuid4()),
        index=True,
        unique=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    apps = relationship("App", back_populates="organisation", cascade="all, delete-orphan")
    user_memberships = relationship(
        "UserOrganisationMembership", back_populates="organisation", cascade="all, delete-orphan"
    )


class App(BaseModel):
    __tablename__ = "apps"
    # Override pid to string UUID so FKs align
    pid: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=lambda: str(uuid4()),
        index=True,
        unique=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    organisation_id: Mapped[str] = mapped_column(String, ForeignKey("organisations.pid"), nullable=False)
    organisation = relationship("Organisation", back_populates="apps")
    user_memberships = relationship("UserAppMembership", back_populates="app", cascade="all, delete-orphan")


class UserOrganisationMembership(BaseModel):
    __tablename__ = "user_organisation_membership"
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth_user.id"), nullable=False)
    organisation_id: Mapped[str] = mapped_column(String, ForeignKey("organisations.pid"), nullable=False)
    role: Mapped["OrganisationRole"] = mapped_column(SAEnum(OrganisationRole), nullable=False)
    user = relationship("AuthUser", back_populates="organisation_memberships")
    organisation = relationship("Organisation", back_populates="user_memberships")


class UserAppMembership(BaseModel):
    __tablename__ = "user_app_membership"
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth_user.id"), nullable=False)
    app_id: Mapped[str] = mapped_column(String, ForeignKey("apps.pid"), nullable=False)
    role: Mapped["AppRole"] = mapped_column(SAEnum(AppRole), nullable=False)
    user = relationship("AuthUser", back_populates="app_memberships")
    app = relationship("App", back_populates="user_memberships")

