import psycopg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

ADMIN_DSN = "postgresql://inventory:inventory@localhost:5432/postgres"
TEST_DSN = "postgresql://inventory:inventory@localhost:5432/inventory_test"
TEST_SQLALCHEMY_URL = TEST_DSN.replace("postgresql://", "postgresql+psycopg://")


@pytest.fixture(scope="session")
def database():
    """Fresh test database migrated to head — validates the migrations themselves."""
    with psycopg.connect(ADMIN_DSN, autocommit=True) as conn:
        conn.execute("DROP DATABASE IF EXISTS inventory_test WITH (FORCE)")
        conn.execute("CREATE DATABASE inventory_test")

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_SQLALCHEMY_URL)
    command.upgrade(cfg, "head")

    yield

    with psycopg.connect(ADMIN_DSN, autocommit=True) as conn:
        conn.execute("DROP DATABASE IF EXISTS inventory_test WITH (FORCE)")


@pytest.fixture
def db_session(database) -> Session:
    engine = create_engine(TEST_SQLALCHEMY_URL)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session
        session.rollback()
    with engine.begin() as conn:
        # All FK-referencing tables must be truncated in one statement —
        # PostgreSQL refuses to truncate a table referenced by a foreign key
        # unless the referencing tables are listed too (no CASCADE: the
        # explicit list keeps every table consciously accounted for).
        conn.execute(
            text("TRUNCATE store_request, store_product, product, store RESTART IDENTITY")
        )
    engine.dispose()
