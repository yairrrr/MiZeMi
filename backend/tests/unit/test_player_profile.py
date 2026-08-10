"""Unit tests for the Player/Profile domain models (MASTER_SPEC.md §9.1, §9.2, §10).

Pure domain tests: no IO, no network, no database.
"""

from dataclasses import fields

from app.domain.game import Player, PlayerProfile, ProfileField


def _profile_with_mixed_consent() -> PlayerProfile:
    return PlayerProfile(
        player_id="p1",
        fields=(
            ProfileField(field_key="favorite_food", value="pizza", allow_question_usage=True),
            ProfileField(field_key="age", value=27, allow_question_usage=True),
            ProfileField(field_key="personal_fact", value="afraid of pigeons", allow_question_usage=False),
        ),
    )


class TestProfileField:
    def test_profile_field_stores_str_value(self) -> None:
        field = ProfileField(field_key="city", value="Haifa", allow_question_usage=True)

        assert field.field_key == "city"
        assert field.value == "Haifa"
        assert field.allow_question_usage is True

    def test_profile_field_stores_int_value(self) -> None:
        field = ProfileField(field_key="age", value=30, allow_question_usage=False)

        assert field.field_key == "age"
        assert field.value == 30
        assert field.allow_question_usage is False


class TestPlayerProfileConsentBoundary:
    def test_consented_fields_returns_fields_with_consent(self) -> None:
        profile = _profile_with_mixed_consent()

        consented_keys = [field.field_key for field in profile.consented_fields()]

        assert consented_keys == ["favorite_food", "age"]

    def test_consented_fields_excludes_fields_without_consent(self) -> None:
        profile = _profile_with_mixed_consent()

        consented_keys = {field.field_key for field in profile.consented_fields()}

        assert "personal_fact" not in consented_keys

    def test_consented_fields_does_not_modify_original_fields(self) -> None:
        profile = _profile_with_mixed_consent()
        original = profile.fields

        profile.consented_fields()

        assert profile.fields == original
        assert len(profile.fields) == 3


class TestPlayer:
    def test_player_creation_with_id_and_display_name(self) -> None:
        player = Player(player_id="p1", display_name="Dana")

        assert player.player_id == "p1"
        assert player.display_name == "Dana"

    def test_player_defaults_match_contract(self) -> None:
        player = Player(player_id="p1", display_name="Dana")

        assert player.connected is True
        assert player.is_ready is False
        assert player.profile is None

    def test_player_has_profile_false_without_profile(self) -> None:
        player = Player(player_id="p1", display_name="Dana")

        assert player.has_profile is False

    def test_player_has_profile_true_after_profile_assigned(self) -> None:
        player = Player(player_id="p1", display_name="Dana")

        player.profile = _profile_with_mixed_consent()

        assert player.has_profile is True

    def test_player_has_no_is_host_or_score_domain_fields(self) -> None:
        field_names = {field.name for field in fields(Player)}

        assert "is_host" not in field_names
        assert "score" not in field_names
