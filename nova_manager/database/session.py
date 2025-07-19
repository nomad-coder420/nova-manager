from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker

from nova_manager.core.config import DATABASE_URL
from nova_manager.core.log import logger
from typing import AsyncGenerator

# Synchronous engine for existing parts of the app and Alembic migrations
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Asynchronous engine for fastapi-users and new features
async_engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
AsyncSessionLocal = async_sessionmaker(bind=async_engine, autocommit=False, autoflush=False)


def get_db():
    db = SessionLocal()

    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Error committing database transaction: {e}")
        db.rollback()
        raise e
    finally:
        db.close()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            # Provide a transactional session to endpoints
            yield session
            # Commit at the end of request processing
            await session.commit()
        except Exception:
            # Rollback if any exception occurs
            await session.rollback()
            raise
