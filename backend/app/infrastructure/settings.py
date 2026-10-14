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

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_DEFAULT_CORS_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


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
        hide_input_in_errors=True,
        # Keep constructing Settings(database_url=...) by field name working
        # alongside the DATABASE_URL alias below.
        validate_by_name=True,
    )

    env: Environment = Field(default=Environment.DEVELOPMENT, validation_alias=AliasChoices("MIZEMI_ENV", "APP_ENV"))
    # MIZEMI_DATABASE_URL wins; the bare DATABASE_URL name that hosting
    # providers (Render, Neon) inject is accepted as a fallback.
    database_url: str = Field(
        default="sqlite:///./mizemi.db",
        repr=False,
        validation_alias=AliasChoices("MIZEMI_DATABASE_URL", "DATABASE_URL"),
    )
    host: str = Field(default="127.0.0.1", validation_alias=AliasChoices("MIZEMI_HOST", "HOST"))
    port: int = Field(default=8000, ge=1, le=65535, validation_alias=AliasChoices("MIZEMI_PORT", "PORT"))
    # NoDecode: the raw env value is a §16 comma-separated string, not JSON —
    # let _parse_cors_origins own the parsing instead of the settings source.
    cors_origins: Annotated[tuple[str, ...], NoDecode] = Field(default=_DEFAULT_CORS_ORIGINS, validation_alias=AliasChoices("MIZEMI_CORS_ORIGINS", "FRONTEND_ORIGIN"))
    log_level: str = "INFO"

    # Gameplay (§9.3, §12): the approved MVP defaults.
    questions_per_game: int = Field(default=20, ge=1, le=50)
    question_time_limit_seconds: int = Field(default=20, ge=1, le=300)
    # Abuse limits and lifetimes (§10, §15, §17).
    max_players_per_room: int = Field(default=50, ge=1, le=500)
    room_idle_ttl_minutes: int = Field(default=120, ge=1)
    retention_days: int = Field(default=7, ge=1)

    # ─── Optional AI question generation (§12.7) ────────────────────────────
    # Feature flag: when false, every ``question_source="ai"`` request is
    # rejected before any key is used and the toggle is not advertised on
    # ``/api/v1/features``.
    ai_enabled: bool = Field(default=False)
    # Bring-your-own key for Anthropic. Marked ``repr=False`` so Settings
    # instances never render it, and never serialized to disk/logs/DB.
    anthropic_api_key: str | None = Field(default=None, repr=False)
    anthropic_model: str = Field(default="claude-sonnet-5")
    # Global throttle, in-process. Each successful room-start with AI counts
    # once; a per-process counter resets every rolling hour.
    ai_max_games_per_hour: int = Field(default=20, ge=1, le=1000)
    ai_request_timeout_seconds: int = Field(default=90, ge=5, le=120)

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
