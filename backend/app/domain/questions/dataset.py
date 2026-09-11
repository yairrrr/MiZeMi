"""Consent-safe input boundary for question generation (MASTER_SPEC.md §10, §12)."""

from collections.abc import Iterable
from functools import cached_property
from copy import copy

from app.domain.game import Player, ProfileField


class ProfileDataset:
    """An immutable snapshot of player data approved for question usage.

    The dataset copies identity and consented fields from ``Player`` objects;
    it never retains the players or their raw profiles. Question rules can
    therefore consume this object without a path around per-field consent.
    Input order is preserved to keep downstream algorithms deterministic.
    """

    def __init__(self, players: Iterable[Player], language: str = "en") -> None:
        if language not in ("en", "he"):
            raise ValueError("unsupported question language")
        self.language = language
        player_ids: list[str] = []
        display_names: dict[str, str] = {}
        fields_by_player: dict[str, tuple[ProfileField, ...]] = {}

        for player in players:
            if player.player_id in display_names:
                raise ValueError(f"duplicate player_id in dataset: {player.player_id}")

            player_ids.append(player.player_id)
            display_names[player.player_id] = player.display_name
            fields_by_player[player.player_id] = (
                player.profile.consented_fields() if player.profile is not None else ()
            )

        self._player_ids = tuple(player_ids)
        self._display_names = display_names
        self._fields_by_player = fields_by_player

    @property
    def player_ids(self) -> tuple[str, ...]:
        return self._player_ids

    @property
    def player_count(self) -> int:
        return len(self._player_ids)

    @property
    def field_keys(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                field.field_key
                for player_id in self._player_ids
                for field in self._fields_by_player[player_id]
            )
        )

    def display_name_for(self, player_id: str) -> str:
        return self._display_names[player_id]

    def fields_for(self, player_id: str) -> tuple[ProfileField, ...]:
        return self._fields_by_player[player_id]

    def values_for(self, field_key: str) -> tuple[tuple[str, str | int], ...]:
        """Return ``(player_id, value)`` pairs in deterministic player order."""
        return tuple(
            (player_id, field.value)
            for player_id in self._player_ids
            for field in self._fields_by_player[player_id]
            if field.field_key == field_key
        )

    def with_language(self, language: str) -> "ProfileDataset":
        if language not in ("en", "he"):
            raise ValueError("unsupported question language")
        if language == self.language:
            return self
        result = copy(self)
        result.language = language
        result.__dict__.pop("index", None)
        return result

    @cached_property
    def index(self):
        from app.domain.questions.index import DatasetIndex
        return DatasetIndex(self)
