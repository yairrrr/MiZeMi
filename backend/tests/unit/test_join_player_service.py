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

        result = JoinPlayerService(registry).join("ABC234", "Dana")

        assert room.game.state is GameState.LOBBY
        assert room.game.get_player(result.player.player_id) is result.player
        assert result.game_id == room.game.game_id

    def test_joins_player_during_profile_collection(self) -> None:
        registry, room = _registry_with_room()
        first = JoinPlayerService(registry).join("ABC234", "Dana").player
        room.game.submit_initial_profile(first.player_id, _profile_for(first.player_id))
        assert room.game.state is GameState.PROFILE_COLLECTION

        second = JoinPlayerService(registry).join("ABC234", "Omer").player

        assert room.game.get_player(second.player_id) is second

    def test_returned_player_is_the_stored_player(self) -> None:
        registry, room = _registry_with_room()

        player = JoinPlayerService(registry).join("ABC234", "Dana").player

        assert room.game.players == (player,)

    def test_player_id_is_non_empty_opaque_string(self) -> None:
        registry, _ = _registry_with_room()

        player = JoinPlayerService(registry).join("ABC234", "Dana").player

        assert isinstance(player.player_id, str) and player.player_id

    def test_player_id_generation_is_injectable(self) -> None:
        registry, _ = _registry_with_room()
        service = JoinPlayerService(registry, player_id_generator=lambda: "player-fixed")

        player = service.join("ABC234", "Dana").player

        assert player.player_id == "player-fixed"

    def test_display_name_is_stored_trimmed(self) -> None:
        registry, _ = _registry_with_room()

        player = JoinPlayerService(registry).join("ABC234", "  Dana  ").player

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

        player = JoinPlayerService(registry).join("ABC234", "A" * 20).player

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
        original = JoinPlayerService(registry).join("ABC234", "Dana").player

        with pytest.raises(NameTakenError):
            JoinPlayerService(registry).join("ABC234", "dana")

        assert room.game.players == (original,)

    def test_unknown_room_raises_room_not_found(self) -> None:
        registry = RoomRegistry()

        with pytest.raises(RoomNotFoundError):
            JoinPlayerService(registry).join("ZZZZZ2", "Dana")

    def test_join_in_ready_reopens_profile_collection(self) -> None:
        registry, room = _registry_with_room()
        player = JoinPlayerService(registry).join("ABC234", "Dana").player
        room.game.submit_initial_profile(player.player_id, _profile_for(player.player_id))
        room.game.mark_player_ready(player.player_id)
        assert room.game.state is GameState.READY

        newcomer = JoinPlayerService(registry).join("ABC234", "Omer").player
        assert room.game.players == (player, newcomer)
        assert room.game.state is GameState.PROFILE_COLLECTION
        assert player.is_ready and not newcomer.is_ready
        room.game.submit_initial_profile(newcomer.player_id, _profile_for(newcomer.player_id))
        room.game.mark_player_ready(newcomer.player_id)
        assert room.game.state is GameState.READY

    def test_join_rejected_in_question_active_state(self) -> None:
        registry, room = _registry_with_room()
        player = JoinPlayerService(registry).join("ABC234", "Dana").player
        room.game.submit_initial_profile(player.player_id, _profile_for(player.player_id))
        room.game.mark_player_ready(player.player_id)
        room.game.transition_to(GameState.QUESTION_ACTIVE)

        with pytest.raises(RoomNotJoinableError) as exc_info:
            JoinPlayerService(registry).join("ABC234", "Omer")

        assert exc_info.value.state is GameState.QUESTION_ACTIVE
        assert room.game.players == (player,)


class TestJoinCredentialsAndCapacity:
    def test_join_issues_a_player_token_bound_to_that_player(self) -> None:
        from app.infrastructure.credentials import CredentialStore

        registry, _ = _registry_with_room()
        credentials = CredentialStore()
        service = JoinPlayerService(
            registry, credentials=credentials, token_generator=lambda: "player-token-1"
        )

        result = service.join("ABC234", "Dana")

        assert result.player_token == "player-token-1"
        assert credentials.verify_player("ABC234", result.player.player_id, "player-token-1")

    def test_join_without_credential_store_returns_no_token(self) -> None:
        registry, _ = _registry_with_room()

        assert JoinPlayerService(registry).join("ABC234", "Dana").player_token is None

    def test_full_room_rejects_new_players_without_mutation(self) -> None:
        from app.application.join_player import RoomFullError

        registry, room = _registry_with_room()
        service = JoinPlayerService(registry, max_players=2)
        service.join("ABC234", "Dana")
        service.join("ABC234", "Omer")

        with pytest.raises(RoomFullError):
            service.join("ABC234", "Noa")

        assert len(room.game.players) == 2
