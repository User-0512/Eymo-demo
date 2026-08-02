"""
Shared pytest fixtures for the Eymo test suite.

This module solves the critical test-isolation bug where multiple test modules
overrode the global `app.dependency_overrides[get_db]` with their own SQLite
engines, causing "no such table" errors depending on test execution order.

The fix: a single, shared in-memory SQLite engine + ONE global get_db override,
plus an autouse fixture that creates/drops all tables per test function.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import models FIRST so their tables register on Base.metadata before create_all.
from services.database import Base, get_db
from services.user_db import User  # noqa: F401
from services.content_db import Content, UserInteraction  # noqa: F401
from services.moderation.human_review_queue import HumanReviewItem  # noqa: F401
from services.api.app.main import app

# Use a single shared SQLite database for the entire test session.
TEST_DATABASE_URL = "sqlite:///./test_eymo.db"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def override_get_db():
    """FastAPI dependency override that uses the shared test database."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# One global override for ALL tests — this is the key isolation fix.
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def create_test_schema():
    """Create all tables once for the session."""
    Base.metadata.create_all(bind=engine)
    yield
    # Drop all tables at the very end of the session.
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_tables(create_test_schema):
    """
    Clean all rows between tests to guarantee isolation.

    Drops and recreates all tables, ensuring no cross-test contamination.
    SQLite does not support `TRUNCATE`, so we recreate the schema.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def test_client():
    """Provides the shared TestClient."""
    return client

