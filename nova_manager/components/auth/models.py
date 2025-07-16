from fastapi_users.db import SQLAlchemyBaseUserTable
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from nova_manager.core.models import Base


class AuthUser(Base, SQLAlchemyBaseUserTable[int]):
    __tablename__ = "auth_user"
    id: Mapped[int] = mapped_column(primary_key=True)
    
