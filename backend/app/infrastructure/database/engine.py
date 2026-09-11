"""SQLAlchemy engine and session-factory construction (MASTER_SPEC.md §15, §16).

Infrastructure layer. The engine URL comes from the typed settings object
(``MIZEMI_DATABASE_URL``, §16) — this module never reads the environment
itself. Nothing is connected at import time: ``get_engine`` /
``get_session_factory`` build their objects lazily and cache them, mirroring
the settings module's ``get_settings`` pattern (clear the cache in tests via
``get_engine.cache_clear()``).
"""

from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.settings import get_settings

_IN_MEMORY_SQLITE_URLS = frozenset({"sqlite://", "sqlite:///:memory:"})


def normalize_database_url(database_url: str) -> str:
    """Point bare PostgreSQL URLs at the psycopg 3 driver.

    Hosting providers (Neon, Render) hand out ``postgres://`` or
    ``postgresql://`` URLs; SQLAlchemy needs ``postgresql+psycopg://`` to use
    the installed psycopg 3 driver. Other URLs are returned unchanged.
    """
    for prefix in ("postgres://", "postgresql://"):
        if database_url.startswith(prefix):
            return "postgresql+psycopg://" + database_url[len(prefix):]
    return database_url


def create_database_engine(database_url: str) -> Engine:
    """Build an ``Engine`` for ``database_url`` with backend-appropriate defaults.

    For SQLite, ``check_same_thread=False`` lets the connection be used from
    FastAPI's threadpool (a pysqlite driver arg, not a schema feature), and an
    in-memory URL additionally gets a ``StaticPool`` so every session in the
    process shares the one in-memory database. Server databases get
    ``pool_pre_ping`` and a short ``pool_recycle`` so connections dropped by a
    serverless provider (Neon suspends idle compute) are replaced
    transparently instead of failing a request.
    """
    url = normalize_database_url(database_url)
    kwargs: dict[str, object] = {"hide_parameters": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in _IN_MEMORY_SQLITE_URLS:
            kwargs["poolclass"] = StaticPool
    else:
        kwargs["pool_pre_ping"] = True
        kwargs["pool_recycle"] = 300
        kwargs["pool_size"] = 2
        kwargs["max_overflow"] = 1
        kwargs["connect_args"] = {"connect_timeout": 10}
    return create_engine(url, **kwargs)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """A ``sessionmaker`` bound to ``engine``.

    ``autoflush`` is off so a unit of work flushes only when it chooses to;
    ``expire_on_commit`` is off so objects stay usable after the application
    layer commits its transaction (§15 — the application owns transactions).
    """
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@lru_cache
def get_engine() -> Engine:
    """The process-wide engine, built once from settings."""
    return create_database_engine(get_settings().database_url)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """The process-wide session factory, bound to the cached engine."""
    return create_session_factory(get_engine())
