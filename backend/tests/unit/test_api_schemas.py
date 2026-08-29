"""Contract-pinning tests for the Player/Profile wire schemas (MASTER_SPEC.md §9.1, §9.2)."""

import pytest
from pydantic import ValidationError

from app.api.schemas import PlayerProfileSchema, PlayerSchema, ProfileFieldSchema
from app.domain.game import Player, PlayerProfile, ProfileField

PLAYER_WIRE_KEYS = {
    "player_id",
    "display_name",
    "is_host",
    "connected",
    "has_profile",
    "is_ready",
    "score",
}


def _profile() -> PlayerProfile:
    return PlayerProfile(
        player_id="p1",
        fields=(
            ProfileField(field_key="favorite_food", value="pizza", allow_question_usage=True),
            ProfileField(field_key="age", value=27, allow_question_usage=True),
            ProfileField(field_key="personal_fact", value="afraid of pigeons", allow_question_usage=False),
        ),
    )


class TestPlayerSchema:
    def test_player_without_profile_maps_correctly(self) -> None:
        player = Player(player_id="p1", display_name="Dana")

        schema = PlayerSchema.from_domain(player, score=0)

        assert schema.player_id == "p1"
        assert schema.display_name == "Dana"
        assert schema.is_host is False
        assert schema.connected is True
        assert schema.has_profile is False
        assert schema.is_ready is False
        assert schema.score == 0

    def test_player_with_profile_maps_has_profile_true(self) -> None:
        player = Player(player_id="p1", display_name="Dana")
        player.assign_initial_profile(_profile())

        schema = PlayerSchema.from_domain(player, score=0)

        assert schema.has_profile is True

    def test_connected_state_is_mapped_from_domain(self) -> None:
        player = Player(player_id="p1", display_name="Dana", connected=False)

        schema = PlayerSchema.from_domain(player, score=0)

        assert schema.connected is False

    def test_ready_state_is_mapped_from_domain(self) -> None:
        player = Player(player_id="p1", display_name="Dana", is_ready=True)

        schema = PlayerSchema.from_domain(player, score=0)

        assert schema.is_ready is True

    def test_explicit_score_is_preserved_exactly(self) -> None:
        player = Player(player_id="p1", display_name="Dana")

        schema = PlayerSchema.from_domain(player, score=1730)

        assert schema.score == 1730

    def test_from_domain_requires_score(self) -> None:
        player = Player(player_id="p1", display_name="Dana")

        with pytest.raises(TypeError):
            PlayerSchema.from_domain(player)  # type: ignore[call-arg]

    def test_serialized_player_has_exact_wire_keys(self) -> None:
        player = Player(player_id="p1", display_name="Dana")

        dumped = PlayerSchema.from_domain(player, score=0).model_dump(mode="json")

        assert set(dumped.keys()) == PLAYER_WIRE_KEYS

    def test_extra_player_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PlayerSchema.model_validate(
                {
                    "player_id": "p1",
                    "display_name": "Dana",
                    "is_host": False,
                    "connected": True,
                    "has_profile": False,
                    "is_ready": False,
                    "score": 0,
                    "email": "dana@example.com",
                }
            )

    def test_mapping_does_not_mutate_domain_player(self) -> None:
        player = Player(player_id="p1", display_name="Dana")

        PlayerSchema.from_domain(player, score=999)

        assert player.player_id == "p1"
        assert player.display_name == "Dana"
        assert player.connected is True
        assert player.is_ready is False
        assert player.profile is None


class TestProfileSchemas:
    def test_profile_maps_player_id_and_fields(self) -> None:
        schema = PlayerProfileSchema.from_domain(_profile())

        assert schema.player_id == "p1"
        assert len(schema.fields) == 3

    def test_field_order_is_preserved(self) -> None:
        schema = PlayerProfileSchema.from_domain(_profile())

        assert [field.field_key for field in schema.fields] == [
            "favorite_food",
            "age",
            "personal_fact",
        ]

    def test_str_values_preserved_exactly(self) -> None:
        schema = PlayerProfileSchema.from_domain(_profile())

        assert schema.fields[0].value == "pizza"
        assert isinstance(schema.fields[0].value, str)

    def test_int_values_preserved_exactly(self) -> None:
        schema = PlayerProfileSchema.from_domain(_profile())

        assert schema.fields[1].value == 27
        assert isinstance(schema.fields[1].value, int)

    def test_allow_question_usage_preserved(self) -> None:
        schema = PlayerProfileSchema.from_domain(_profile())

        assert [field.allow_question_usage for field in schema.fields] == [True, True, False]

    def test_serialized_profile_has_exact_wire_keys(self) -> None:
        dumped = PlayerProfileSchema.from_domain(_profile()).model_dump(mode="json")

        assert set(dumped.keys()) == {"player_id", "fields"}
        assert all(
            set(field.keys()) == {"field_key", "value", "allow_question_usage"}
            for field in dumped["fields"]
        )

    def test_extra_profile_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PlayerProfileSchema.model_validate(
                {"player_id": "p1", "fields": [], "nickname": "D"}
            )

    def test_extra_profile_field_keys_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProfileFieldSchema.model_validate(
                {
                    "field_key": "city",
                    "value": "Haifa",
                    "allow_question_usage": True,
                    "hint": "north",
                }
            )

    def test_mapping_does_not_mutate_domain_profile(self) -> None:
        profile = _profile()
        original_fields = profile.fields

        PlayerProfileSchema.from_domain(profile)

        assert profile.fields == original_fields
        assert profile.fields[1].value == 27
