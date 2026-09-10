"""Unit tests for engine / session-factory construction (MASTER_SPEC.md §15, §16)."""

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.engine import (
    create_database_engine,
    create_session_factory,
    get_engine,
    get_session_factory,
)
from app.infrastructure.settings import get_settings


class TestCreateDatabaseEngine:
    def test_builds_a_sqlite_engine(self) -> None:
        engine = create_database_engine("sqlite://")
        assert isinstance(engine, Engine)
        assert engine.dialect.name == "sqlite"

    def test_in_memory_sqlite_uses_a_static_pool(self) -> None:
        engine = create_database_engine("sqlite://")
        assert isinstance(engine.pool, StaticPool)

    def test_file_sqlite_does_not_use_a_static_pool(self, tmp_path) -> None:
        engine = create_database_engine(f"sqlite:///{tmp_path / 'x.db'}")
        assert not isinstance(engine.pool, StaticPool)

    def test_in_memory_engine_shares_one_database_across_sessions(self) -> None:
        engine = create_database_engine("sqlite://")
        factory = create_session_factory(engine)

        with factory() as writer:
            writer.execute(text("CREATE TABLE t (id INTEGER)"))
            writer.execute(text("INSERT INTO t (id) VALUES (1)"))
            writer.commit()
        with factory() as reader:
            assert reader.execute(text("SELECT id FROM t")).scalar_one() == 1


class TestCreateSessionFactory:
    def test_returns_a_sessionmaker(self) -> None:
        factory = create_session_factory(create_database_engine("sqlite://"))
        assert isinstance(factory, sessionmaker)

    def test_sessions_do_not_autoflush(self) -> None:
        factory = create_session_factory(create_database_engine("sqlite://"))
        with factory() as session:
            assert session.autoflush is False


class TestCachedAccessors:
    def test_get_engine_is_a_cached_singleton(self) -> None:
        get_engine.cache_clear()
        try:
            assert get_engine() is get_engine()
        finally:
            get_engine.cache_clear()

    def test_get_engine_uses_the_configured_database_url(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        db_path = tmp_path / "configured.db"
        monkeypatch.setenv("MIZEMI_DATABASE_URL", f"sqlite:///{db_path}")
        get_settings.cache_clear()
        get_engine.cache_clear()
        try:
            assert str(get_engine().url) == f"sqlite:///{db_path}"
        finally:
            get_settings.cache_clear()
            get_engine.cache_clear()

    def test_get_session_factory_binds_to_the_cached_engine(self) -> None:
        get_settings.cache_clear()
        get_engine.cache_clear()
        get_session_factory.cache_clear()
        try:
            assert get_session_factory().kw["bind"] is get_engine()
        finally:
            get_settings.cache_clear()
            get_engine.cache_clear()
            get_session_factory.cache_clear()
