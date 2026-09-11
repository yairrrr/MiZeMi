"""Unit tests for the typed settings object (MASTER_SPEC.md §16)."""

import pytest
from pydantic import ValidationError

from app.infrastructure.settings import Environment, Settings, get_settings


@pytest.fixture(autouse=True)
def _real_environment_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Undo the suite-wide in-memory database override for these tests."""
    monkeypatch.delenv("MIZEMI_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)


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
        assert settings.cors_origins == ("http://localhost:5173", "http://127.0.0.1:5173")
        assert settings.log_level == "INFO"

    def test_gameplay_defaults_are_the_approved_mvp_values(self) -> None:
        settings = _settings()

        assert settings.questions_per_game == 10
        assert settings.question_time_limit_seconds == 20
        assert settings.max_players_per_room == 50
        assert settings.room_idle_ttl_minutes == 120
        assert settings.retention_days == 7


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
        monkeypatch.setenv("HOST", "0.0.0.0")
        settings = _settings()
        assert settings.env is Environment.DEVELOPMENT
        assert settings.host == "127.0.0.1"

    def test_bare_database_url_is_accepted_as_a_fallback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("MIZEMI_DATABASE_URL", raising=False)
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pw@db.example/mizemi")
        assert _settings().database_url == "postgresql://user:pw@db.example/mizemi"

    def test_prefixed_database_url_wins_over_the_bare_name(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgresql://bare/db")
        monkeypatch.setenv("MIZEMI_DATABASE_URL", "sqlite:///./preferred.db")
        assert _settings().database_url == "sqlite:///./preferred.db"

    def test_database_url_can_be_set_by_field_name(self) -> None:
        assert _settings(database_url="sqlite://").database_url == "sqlite://"

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

    @pytest.mark.parametrize(
        ("variable", "value"),
        [
            ("MIZEMI_QUESTIONS_PER_GAME", "0"),
            ("MIZEMI_QUESTION_TIME_LIMIT_SECONDS", "0"),
            ("MIZEMI_MAX_PLAYERS_PER_ROOM", "0"),
        ],
    )
    def test_gameplay_limits_are_validated(
        self, monkeypatch: pytest.MonkeyPatch, variable: str, value: str
    ) -> None:
        monkeypatch.setenv(variable, value)
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
