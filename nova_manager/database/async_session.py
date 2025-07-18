from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from nova_manager.core.config import DATABASE_URL
from nova_manager.core.log import logger

# Create async version of DATABASE_URL (replace postgresql:// with postgresql+asyncpg://)
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine
async_engine = create_async_engine(ASYNC_DATABASE_URL)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # await session.commit()
        except Exception as e:
            logger.error(f"Error committing async database transaction: {e}")
            await session.rollback()
            raise e
        finally:
            # await session.close()
            pass
