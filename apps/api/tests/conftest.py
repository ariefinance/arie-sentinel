"""Pytest fixtures: an isolated migrated test database, truncated between tests."""

from __future__ import annotations

import os

# Point the whole app at the test database BEFORE importing app modules.
os.environ["ARIE_DATABASE_URL"] = os.environ.get(
    "ARIE_TEST_DATABASE_URL",
    "postgresql+psycopg://arie:arie@localhost:5432/arie_sentinel_test",
)
os.environ["ARIE_ENV"] = "test"
os.environ["ARIE_DEV_AUTH"] = "true"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from arie_sentinel.db import SessionLocal, engine  # noqa: E402
from arie_sentinel.main import app  # noqa: E402
from arie_sentinel.models import Base  # noqa: E402

_TABLES = [t.name for t in Base.metadata.sorted_tables]


@pytest.fixture(scope="session", autouse=True)
def _migrate() -> None:
    cfg = Config("alembic.ini")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


@pytest.fixture(autouse=True)
def _truncate() -> None:
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(_TABLES)} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def db() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
