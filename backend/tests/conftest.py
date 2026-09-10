"""Pytest configuration for the backend suite.

Re-exports the shared fixtures from ``tests/fixtures/`` so every test under
``backend/tests/`` can request them by name. Keep this file thin: fixture
implementations belong in ``tests/fixtures/``.
"""

from tests.fixtures.database import db_engine, db_session

__all__ = ["db_engine", "db_session"]
