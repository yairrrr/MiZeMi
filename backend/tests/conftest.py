"""Pytest configuration for the backend suite.

Re-exports the shared fixtures from ``tests/fixtures/`` so every test under
``backend/tests/`` can request them by name. Keep this file thin: fixture
implementations belong in ``tests/fixtures/``, and the plain object builders
in ``tests/fixtures/factories.py`` are imported directly by the tests that
use them (they are not fixtures).
"""

from tests.fixtures.database import db_engine, db_session, sqlite_file_engine

__all__ = ["db_engine", "db_session", "sqlite_file_engine"]
