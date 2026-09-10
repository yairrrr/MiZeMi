"""Unit tests for the typed settings object (MASTER_SPEC.md §16)."""

import pytest
from pydantic import ValidationError

from app.infrastructure.settings import Environment, Settings, get_settings


def _settings(**overrides: object) -> Settings:
    """Build Settings without reading any real .env file on the machine."""
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


class TestDefaults:
    def test_defaults_match_the_spec_table(self) -> None:
        settings = _settings()

        assert settings.env is Environment.DEVELOPMENT
        assert settings.database_url == "sqlite:///./mizemi.db"
        assert settings.host == "127.0.0.1"
        assert settings.port == 8000
        assert settings.cors_origins == ("http://localhost:5173",)
        assert settings.log_level == "INFO"


class TestEnvironmentLoading:
    def test_reads_prefixed_variables_from_the_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MIZEMI_ENV", "production")
        monkeypatch.setenv("MIZEMI_DATABASE_URL", "sqlite:///./other.db")
        monkeypatch.setenv("MIZEMI_HOST", "0.0.0.0")
        monkeypatch.setenv("MIZEMI_PORT", "9001")

        settings = _settings()

        assert settings.env is Environment.PRODUCTION
        assert settings.database_url == "sqlite:///./other.db"
        assert settings.host == "0.0.0.0"
        assert settings.port == 9001

    def test_port_is_coerced_to_int(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MIZEMI_PORT", "8123")
        assert _settings().port == 8123

    def test_unprefixed_variables_are_ignored(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ENV", "production")
        monkeypatch.setenv("DATABASE_URL", "postgres://nope")
        assert _settings().env is Environment.DEVELOPMENT

    def test_unknown_prefixed_variables_are_ignored(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MIZEMI_FUTURE_FLAG", "on")
        assert _settings().env is Environment.DEVELOPMENT


class TestCorsOrigins:
    def test_comma_separated_string_is_split_and_trimmed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            "MIZEMI_CORS_ORIGINS",
            "http://localhost:5173, https://mizemi.example ,http://127.0.0.1:5173",
        )

        assert _settings().cors_origins == (
            "http://localhost:5173",
            "https://mizemi.example",
            "http://127.0.0.1:5173",
        )

    def test_blank_entries_are_dropped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MIZEMI_CORS_ORIGINS", "http://a.example,,  ,http://b.example")
        assert _settings().cors_origins == ("http://a.example", "http://b.example")

    def test_sequence_form_is_accepted(self) -> None:
        settings = _settings(cors_origins=["http://a.example", "http://b.example"])
        assert settings.cors_origins == ("http://a.example", "http://b.example")


class TestLogLevel:
    def test_value_is_normalized_to_upper_case(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MIZEMI_LOG_LEVEL", "debug")
        assert _settings().log_level == "DEBUG"


class TestValidationAndImmutability:
    def test_invalid_environment_value_is_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MIZEMI_ENV", "staging")
        with pytest.raises(ValidationError):
            _settings()

    def test_non_numeric_port_is_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MIZEMI_PORT", "not-a-port")
        with pytest.raises(ValidationError):
            _settings()

    def test_settings_object_is_frozen(self) -> None:
        settings = _settings()
        with pytest.raises(ValidationError):
            settings.port = 1234  # type: ignore[misc]


class TestGetSettings:
    def test_returns_a_cached_singleton(self) -> None:
        get_settings.cache_clear()
        try:
            assert get_settings() is get_settings()
        finally:
            get_settings.cache_clear()

    def test_cache_clear_picks_up_a_changed_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        get_settings.cache_clear()
        try:
            monkeypatch.setenv("MIZEMI_PORT", "8055")
            assert get_settings().port == 8055
        finally:
            get_settings.cache_clear()
