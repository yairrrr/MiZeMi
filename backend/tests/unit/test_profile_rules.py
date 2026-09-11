"""Unit tests for the MVP profile schema and validation (MASTER_SPEC.md §9.2, §10)."""

import pytest

from app.application.profile_rules import (
    MUSIC_STYLES,
    PRIVACY_MESSAGE,
    PROFILE_FIELD_SPECS,
    ProfileValidationError,
    build_validated_profile,
)

REQUIRED = [
    ("city", "Haifa", True),
    ("favorite_food", "pizza", True),
    ("hobby", "chess", True),
    ("favorite_music", "Rock", True),
]


def _build(extra: list[tuple[str, object, bool]] | None = None, base=None):
    return build_validated_profile("p1", list(base if base is not None else REQUIRED) + (extra or []))


def _message(submitted) -> str:
    with pytest.raises(ProfileValidationError) as exc_info:
        build_validated_profile("p1", submitted)
    return exc_info.value.message


class TestValidProfiles:
    def test_required_fields_only_is_valid(self) -> None:
        profile = _build()

        assert profile.player_id == "p1"
        assert [f.field_key for f in profile.fields] == [
            "city",
            "favorite_food",
            "hobby",
            "favorite_music",
        ]

    def test_fields_are_returned_in_canonical_order(self) -> None:
        submitted = list(reversed(REQUIRED)) + [
            ("personal_fact", "I juggle", False),
            ("age", 27, True),
        ]

        profile = build_validated_profile("p1", submitted)

        assert [f.field_key for f in profile.fields] == [
            "city",
            "favorite_food",
            "hobby",
            "favorite_music",
            "age",
            "personal_fact",
        ]

    def test_consent_flags_are_preserved_per_field(self) -> None:
        profile = _build([("personal_fact", "I juggle", False)])

        flags = {f.field_key: f.allow_question_usage for f in profile.fields}
        assert flags["personal_fact"] is False
        assert flags["city"] is True

    def test_text_is_trimmed_and_whitespace_collapsed(self) -> None:
        profile = _build(base=[("city", "  Tel   Aviv  ", True)] + REQUIRED[1:])

        assert profile.fields[0].value == "Tel Aviv"

    def test_age_is_kept_as_an_integer(self) -> None:
        profile = _build([("age", 31, True)])

        age = next(f for f in profile.fields if f.field_key == "age")
        assert age.value == 31 and isinstance(age.value, int)

    def test_every_music_style_is_accepted(self) -> None:
        for style in MUSIC_STYLES:
            base = [f for f in REQUIRED if f[0] != "favorite_music"] + [
                ("favorite_music", style, True)
            ]
            assert build_validated_profile("p1", base).fields

    def test_schema_lists_the_approved_categories(self) -> None:
        assert [spec.field_key for spec in PROFILE_FIELD_SPECS] == [
            "city",
            "favorite_food",
            "hobby",
            "favorite_music",
            "age",
            "favorite_movie",
            "personal_fact",
        ]


class TestRejectedProfiles:
    @pytest.mark.parametrize("missing", ["city", "favorite_food", "hobby", "favorite_music"])
    def test_missing_required_field(self, missing: str) -> None:
        submitted = [f for f in REQUIRED if f[0] != missing]

        assert "is required" in _message(submitted)

    def test_unknown_field(self) -> None:
        assert "unknown field" in _message(REQUIRED + [("password", "x", True)])

    def test_duplicate_field(self) -> None:
        assert "more than once" in _message(REQUIRED + [("city", "Eilat", True)])

    def test_empty_text(self) -> None:
        assert "cannot be empty" in _message([("city", "   ", True)] + REQUIRED[1:])

    def test_text_too_long(self) -> None:
        assert "at most 40" in _message([("city", "x" * 41, True)] + REQUIRED[1:])

    def test_text_field_rejects_numbers(self) -> None:
        assert "must be text" in _message([("city", 5, True)] + REQUIRED[1:])

    @pytest.mark.parametrize("age", [4, 121, -1])
    def test_age_out_of_range(self, age: int) -> None:
        assert "between 5 and 120" in _message(REQUIRED + [("age", age, True)])

    @pytest.mark.parametrize("age", ["27", 27.5, True])
    def test_age_must_be_a_whole_number(self, age: object) -> None:
        assert "whole number" in _message(REQUIRED + [("age", age, True)])

    def test_unknown_music_style(self) -> None:
        submitted = [f for f in REQUIRED if f[0] != "favorite_music"] + [
            ("favorite_music", "Polka", True)
        ]

        assert "listed options" in _message(submitted)

    @pytest.mark.parametrize(
        "value",
        [
            "mail me: dana@example.com",
            "see https://example.com",
            "www.example.com",
            "call 054-123-4567",
            "id 123456789",
        ],
    )
    def test_sensitive_looking_text_is_rejected(self, value: str) -> None:
        assert _message(REQUIRED + [("personal_fact", value, False)]) == PRIVACY_MESSAGE

    def test_short_numbers_are_allowed_in_text(self) -> None:
        profile = _build([("favorite_movie", "2001: A Space Odyssey", True)])

        assert any(f.value == "2001: A Space Odyssey" for f in profile.fields)

    def test_messages_never_echo_the_submitted_value(self) -> None:
        secret = "dana@example.com"

        assert secret not in _message(REQUIRED + [("personal_fact", secret, False)])
