"""Unit tests for the Game aggregate (MASTER_SPEC.md §8, §11).

Structural behavior only — deferred policies (capacity, name uniqueness,
joining states, host, readiness) are deliberately untested because the
aggregate deliberately does not enforce them.
"""

import pytest

from app.domain.game import Game, GameState, InvalidStateTransitionError, Player


class TestNewGame:
    def test_new_game_stores_game_id(self) -> None:
        game = Game(game_id="g1")

        assert game.game_id == "g1"

    def test_new_game_starts_in_lobby(self) -> None:
        game = Game(game_id="g1")

        assert game.state is GameState.LOBBY

    def test_new_game_starts_with_no_players(self) -> None:
        game = Game(game_id="g1")

        assert game.players == ()


class TestPlayerOwnership:
    def test_add_player_adds_a_player(self) -> None:
        game = Game(game_id="g1")
        player = Player(player_id="p1", display_name="Dana")

        game.add_player(player)

        assert game.players == (player,)

    def test_get_player_returns_the_correct_player(self) -> None:
        game = Game(game_id="g1")
        dana = Player(player_id="p1", display_name="Dana")
        omer = Player(player_id="p2", display_name="Omer")
        game.add_player(dana)
        game.add_player(omer)

        assert game.get_player("p2") is omer

    def test_get_player_returns_none_for_unknown_id(self) -> None:
        game = Game(game_id="g1")

        assert game.get_player("missing") is None

    def test_add_player_rejects_duplicate_player_id(self) -> None:
        game = Game(game_id="g1")
        game.add_player(Player(player_id="p1", display_name="Dana"))

        with pytest.raises(ValueError):
            game.add_player(Player(player_id="p1", display_name="Someone Else"))

    def test_duplicate_rejection_does_not_alter_player_collection(self) -> None:
        game = Game(game_id="g1")
        original = Player(player_id="p1", display_name="Dana")
        game.add_player(original)

        with pytest.raises(ValueError):
            game.add_player(Player(player_id="p1", display_name="Someone Else"))

        assert game.players == (original,)
        assert game.get_player("p1") is original

    def test_players_returns_read_only_snapshot(self) -> None:
        game = Game(game_id="g1")
        game.add_player(Player(player_id="p1", display_name="Dana"))

        snapshot = game.players

        assert isinstance(snapshot, tuple)
        assert snapshot is not game.players or isinstance(game.players, tuple)
        # A snapshot taken before a change does not track later additions.
        game.add_player(Player(player_id="p2", display_name="Omer"))
        assert len(snapshot) == 1
        assert len(game.players) == 2


class TestStateTransitions:
    def test_approved_transition_changes_state(self) -> None:
        game = Game(game_id="g1")

        game.transition_to(GameState.PROFILE_COLLECTION)

        assert game.state is GameState.PROFILE_COLLECTION

    def test_invalid_transition_raises_invalid_state_transition_error(self) -> None:
        game = Game(game_id="g1")

        with pytest.raises(InvalidStateTransitionError):
            game.transition_to(GameState.QUESTION_ACTIVE)

    def test_error_exposes_current_and_target_states(self) -> None:
        game = Game(game_id="g1")

        with pytest.raises(InvalidStateTransitionError) as exc_info:
            game.transition_to(GameState.FINISHED)

        assert exc_info.value.current is GameState.LOBBY
        assert exc_info.value.target is GameState.FINISHED

    def test_state_unchanged_after_invalid_transition(self) -> None:
        game = Game(game_id="g1")
        game.transition_to(GameState.PROFILE_COLLECTION)

        with pytest.raises(InvalidStateTransitionError):
            game.transition_to(GameState.LEADERBOARD)

        assert game.state is GameState.PROFILE_COLLECTION
