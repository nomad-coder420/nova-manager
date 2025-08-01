from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from nova_manager.core.config import DATABASE_URL
from nova_manager.core.log import logger


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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