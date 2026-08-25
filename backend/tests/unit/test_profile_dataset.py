"""Unit tests for the consent-safe ProfileDataset boundary."""

import pytest

from app.domain.game import Player, PlayerProfile, ProfileField
from app.domain.questions import ProfileDataset


def _player(
    player_id: str,
    display_name: str,
    *fields: ProfileField,
) -> Player:
    return Player(
        player_id=player_id,
        display_name=display_name,
        profile=PlayerProfile(player_id=player_id, fields=fields),
    )


class TestProfileDatasetConsentBoundary:
    def test_includes_only_consented_fields(self) -> None:
        player = _player(
            "p1",
            "Dana",
            ProfileField("favorite_food", "pizza", True),
            ProfileField("personal_fact", "secret", False),
        )

        dataset = ProfileDataset((player,))

        assert dataset.values_for("favorite_food") == (("p1", "pizza"),)
        assert dataset.values_for("personal_fact") == ()
        assert dataset.field_keys == ("favorite_food",)

    def test_non_consented_field_is_not_available_through_player_fields(self) -> None:
        player = _player(
            "p1",
            "Dana",
            ProfileField("city", "Haifa", True),
            ProfileField("personal_fact", "secret", False),
        )

        dataset = ProfileDataset((player,))

        assert tuple(field.field_key for field in dataset.fields_for("p1")) == ("city",)

    def test_dataset_does_not_retain_player_profile_changes(self) -> None:
        player = _player("p1", "Dana", ProfileField("city", "Haifa", True))
        dataset = ProfileDataset((player,))

        player.profile = PlayerProfile(
            player_id="p1",
            fields=(ProfileField("personal_fact", "new secret", False),),
        )

        assert dataset.values_for("city") == (("p1", "Haifa"),)
        assert dataset.values_for("personal_fact") == ()


class TestProfileDatasetQueries:
    def test_preserves_player_and_value_order(self) -> None:
        dataset = ProfileDataset(
            (
                _player("p2", "Omer", ProfileField("city", "Tel Aviv", True)),
                _player("p1", "Dana", ProfileField("city", "Haifa", True)),
            )
        )

        assert dataset.player_ids == ("p2", "p1")
        assert dataset.values_for("city") == (
            ("p2", "Tel Aviv"),
            ("p1", "Haifa"),
        )

    def test_player_without_profile_has_no_fields(self) -> None:
        dataset = ProfileDataset((Player(player_id="p1", display_name="Dana"),))

        assert dataset.player_count == 1
        assert dataset.fields_for("p1") == ()

    def test_empty_dataset_is_supported(self) -> None:
        dataset = ProfileDataset(())

        assert dataset.player_count == 0
        assert dataset.player_ids == ()
        assert dataset.field_keys == ()

    def test_exposes_display_name_without_exposing_player(self) -> None:
        dataset = ProfileDataset((_player("p1", "Dana"),))

        assert dataset.display_name_for("p1") == "Dana"

    def test_rejects_duplicate_player_ids(self) -> None:
        with pytest.raises(ValueError, match="duplicate player_id"):
            ProfileDataset((_player("p1", "Dana"), _player("p1", "Other")))

    def test_unknown_player_id_is_rejected(self) -> None:
        dataset = ProfileDataset(())

        with pytest.raises(KeyError):
            dataset.fields_for("missing")
