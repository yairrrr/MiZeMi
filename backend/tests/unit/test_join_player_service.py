"""Unit tests for the join-player application service (MASTER_SPEC.md §9.1, §11, §13)."""

import pytest

from app.application.join_player import (
    InvalidDisplayNameError,
    JoinPlayerService,
    NameTakenError,
    RoomNotJoinableError,
)
from app.domain.game import Game, GameState, Player, PlayerProfile, ProfileField, Room
from app.infrastructure.rooms import RoomNotFoundError, RoomRegistry


def _registry_with_room(room_code: str = "ABC234") -> tuple[RoomRegistry, Room]:
    registry = RoomRegistry()
    room = Room(room_code=room_code, game=Game(game_id="g1"))
    registry.register(room)
    return registry, room


def _profile_for(player_id: str) -> PlayerProfile:
    return PlayerProfile(
        player_id=player_id,
        fields=(ProfileField(field_key="favorite_food", value="pizza", allow_question_usage=True),),
    )


class TestJoinPlayerService:
    def test_joins_player_to_lobby_room(self) -> None:
        registry, room = _registry_with_room()

        player = JoinPlayerService(registry).join("ABC234", "Dana")

        assert room.game.state is GameState.LOBBY
        assert room.game.get_player(player.player_id) is player

    def test_joins_player_during_profile_collection(self) -> None:
        registry, room = _registry_with_room()
        first = JoinPlayerService(registry).join("ABC234", "Dana")
        room.game.submit_initial_profile(first.player_id, _profile_for(first.player_id))
        assert room.game.state is GameState.PROFILE_COLLECTION

        second = JoinPlayerService(registry).join("ABC234", "Omer")

        assert room.game.get_player(second.player_id) is second

    def test_returned_player_is_the_stored_player(self) -> None:
        registry, room = _registry_with_room()

        player = JoinPlayerService(registry).join("ABC234", "Dana")

        assert room.game.players == (player,)

    def test_player_id_is_non_empty_opaque_string(self) -> None:
        registry, _ = _registry_with_room()

        player = JoinPlayerService(registry).join("ABC234", "Dana")

        assert isinstance(player.player_id, str) and player.player_id

    def test_player_id_generation_is_injectable(self) -> None:
        registry, _ = _registry_with_room()
        service = JoinPlayerService(registry, player_id_generator=lambda: "player-fixed")

        player = service.join("ABC234", "Dana")

        assert player.player_id == "player-fixed"

    def test_display_name_is_stored_trimmed(self) -> None:
        registry, _ = _registry_with_room()

        player = JoinPlayerService(registry).join("ABC234", "  Dana  ")

        assert player.display_name == "Dana"

    def test_empty_after_trim_rejected(self) -> None:
        registry, room = _registry_with_room()

        with pytest.raises(InvalidDisplayNameError):
            JoinPlayerService(registry).join("ABC234", "   ")

        assert room.game.players == ()

    def test_name_longer_than_twenty_characters_rejected(self) -> None:
        registry, room = _registry_with_room()

        with pytest.raises(InvalidDisplayNameError):
            JoinPlayerService(registry).join("ABC234", "A" * 21)

        assert room.game.players == ()

    def test_twenty_character_name_accepted(self) -> None:
        registry, _ = _registry_with_room()

        player = JoinPlayerService(registry).join("ABC234", "A" * 20)

        assert player.display_name == "A" * 20

    def test_duplicate_exact_name_rejected(self) -> None:
        registry, _ = _registry_with_room()
        JoinPlayerService(registry).join("ABC234", "Dana")

        with pytest.raises(NameTakenError):
            JoinPlayerService(registry).join("ABC234", "Dana")

    def test_duplicate_name_differing_only_by_case_rejected(self) -> None:
        registry, _ = _registry_with_room()
        JoinPlayerService(registry).join("ABC234", "Dana")

        with pytest.raises(NameTakenError):
            JoinPlayerService(registry).join("ABC234", "dANA")

    def test_duplicate_comparison_uses_trimmed_form(self) -> None:
        registry, _ = _registry_with_room()
        JoinPlayerService(registry).join("ABC234", "Dana")

        with pytest.raises(NameTakenError):
            JoinPlayerService(registry).join("ABC234", "  dana  ")

    def test_duplicate_rejection_leaves_existing_players_unchanged(self) -> None:
        registry, room = _registry_with_room()
        original = JoinPlayerService(registry).join("ABC234", "Dana")

        with pytest.raises(NameTakenError):
            JoinPlayerService(registry).join("ABC234", "dana")

        assert room.game.players == (original,)

    def test_unknown_room_raises_room_not_found(self) -> None:
        registry = RoomRegistry()

        with pytest.raises(RoomNotFoundError):
            JoinPlayerService(registry).join("ZZZZZ2", "Dana")

    def test_join_rejected_in_ready_state(self) -> None:
        registry, room = _registry_with_room()
        player = JoinPlayerService(registry).join("ABC234", "Dana")
        room.game.submit_initial_profile(player.player_id, _profile_for(player.player_id))
        room.game.mark_player_ready(player.player_id)
        assert room.game.state is GameState.READY

        with pytest.raises(RoomNotJoinableError):
            JoinPlayerService(registry).join("ABC234", "Omer")

        assert room.game.players == (player,)

    def test_join_rejected_in_question_active_state(self) -> None:
        registry, room = _registry_with_room()
        player = JoinPlayerService(registry).join("ABC234", "Dana")
        room.game.submit_initial_profile(player.player_id, _profile_for(player.player_id))
        room.game.mark_player_ready(player.player_id)
        room.game.transition_to(GameState.QUESTION_ACTIVE)

        with pytest.raises(RoomNotJoinableError) as exc_info:
            JoinPlayerService(registry).join("ABC234", "Omer")

        assert exc_info.value.state is GameState.QUESTION_ACTIVE
        assert room.game.players == (player,)
