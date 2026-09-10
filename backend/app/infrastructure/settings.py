"""Typed application settings (MASTER_SPEC.md §16).

Infrastructure layer: the single place that reads the process environment.
Application code depends on a ``Settings`` instance; it never touches
``os.environ`` directly. Every variable is prefixed ``MIZEMI_`` and is loaded
once — from the environment, or an optional ``.env`` file — into this frozen,
validated object.

This module only *defines* the settings object. Wiring it into the FastAPI
app (bind host/port, CORS, logging) is the presentation layer's concern and
is intentionally left to that owner (§7).
"""

from collections.abc import Sequence
from enum import Enum
from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_DEFAULT_CORS_ORIGINS = ("http://localhost:5173",)


class Environment(str, Enum):
    """The three deployment environments named in §16 (``MIZEMI_ENV``)."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """The §16 variable set, with the spec's documented safe defaults.

    Frozen: settings are read once at startup and never mutated afterwards.
    Unknown ``MIZEMI_``-prefixed variables are ignored rather than rejected,
    so a variable added for one workstream does not break another that is
    still on an older settings object.
    """

    model_config = SettingsConfigDict(
        env_prefix="MIZEMI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    env: Environment = Environment.DEVELOPMENT
    database_url: str = "sqlite:///./mizemi.db"
    host: str = "127.0.0.1"
    port: int = 8000
    # NoDecode: the raw env value is a §16 comma-separated string, not JSON —
    # let _parse_cors_origins own the parsing instead of the settings source.
    cors_origins: Annotated[tuple[str, ...], NoDecode] = _DEFAULT_CORS_ORIGINS
    log_level: str = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        """Accept the §16 comma-separated string form as well as a sequence."""
        if isinstance(value, str):
            return tuple(origin.strip() for origin in value.split(",") if origin.strip())
        if isinstance(value, Sequence):
            return tuple(str(origin).strip() for origin in value if str(origin).strip())
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, constructed once and cached.

    Tests that need a specific configuration either construct ``Settings(...)``
    directly with explicit values, or set ``MIZEMI_`` environment variables
    and call ``get_settings.cache_clear()`` first.
    """
    return Settings()
