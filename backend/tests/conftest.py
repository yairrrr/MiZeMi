"""Pytest configuration for the backend suite.

Re-exports the shared fixtures from ``tests/fixtures/`` so every test under
``backend/tests/`` can request them by name. Keep this file thin: fixture
implementations belong in ``tests/fixtures/``, and the plain object builders
in ``tests/fixtures/factories.py`` / ``tests/fixtures/live.py`` are imported
directly by the tests that use them (they are not fixtures).
"""

from collections.abc import Iterator

import pytest

from app.infrastructure.database.engine import get_engine, get_session_factory
from app.infrastructure.settings import get_settings
from tests.fixtures.database import db_engine, db_session, sqlite_file_engine

__all__ = ["db_engine", "db_session", "sqlite_file_engine"]


@pytest.fixture(autouse=True)
def _isolated_app_database(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Apps built with ``create_app()`` use a private in-memory database.

    Keeps tests from writing ``mizemi.db`` into the working tree and from
    sharing state through a file. Tests that inspect settings defaults undo
    this with ``monkeypatch.delenv`` (see ``test_settings.py``).
    """
    monkeypatch.setenv("MIZEMI_DATABASE_URL", "sqlite://")
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    yield
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
