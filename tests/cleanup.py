import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="function")
def clean_db():
    """Truncate all tables before each test."""
    engine = create_engine("postgresql://postgres@localhost:5432/nova_manager")
    with engine.connect() as conn:
        # Get all table names
        result = conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """))
        tables = [row[0] for row in result]
        
        if tables:
            # Truncate all tables with CASCADE to handle foreign keys
            table_list = ', '.join(f'"{table}"' for table in tables)
            conn.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE"))
            conn.commit()
    
    yield
    # Optional: cleanup after test if needed
