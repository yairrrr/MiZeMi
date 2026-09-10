"""Shared database fixtures for tests (MASTER_SPEC.md §15, §19).

An isolated in-memory SQLite database per test: fast, no temp files, and torn
down completely afterwards so no test depends on state left by another (§22).
Integration tests that specifically need a real database file build their own
engine from ``tmp_path`` with ``create_database_engine``.

These are registered as fixtures by ``backend/tests/conftest.py``.
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.infrastructure.database import (
    Base,
    create_database_engine,
    create_session_factory,
)
from app.infrastructure.database import models  # noqa: F401 - registers ORM tables on Base


@pytest.fixture
def db_engine() -> Iterator[Engine]:
    """A fresh in-memory SQLite engine with the full schema created.

    ``Base.metadata`` is currently empty (no ORM models yet), so
    ``create_all`` is a no-op today; the fixture is ready for models the
    moment they land, with no test changes needed.
    """
    engine = create_database_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    """A session on the in-memory engine, closed after the test."""
    session = create_session_factory(db_engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sqlite_file_engine(tmp_path) -> Iterator[Engine]:
    """An engine on a real SQLite file, for tests that must exercise on-disk
    behaviour (persistence across engines, file creation). Schema created;
    engine disposed afterwards. The temp file is removed with ``tmp_path``.
    """
    engine = create_database_engine(f"sqlite:///{tmp_path / 'mizemi_test.db'}")
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()
