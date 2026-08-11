"""Unit tests for the Game aggregate (MASTER_SPEC.md §8, §11).

Structural behavior only — deferred policies (capacity, name uniqueness,
joining states, host, readiness) are deliberately untested because the
aggregate deliberately does not enforce them.
"""

import pytest

from app.domain.game import (
    Game,
    GameState,
    InvalidStateTransitionError,
    Player,
    PlayerProfile,
    ProfileField,
)


def _profile_for(player_id: str) -> PlayerProfile:
    return PlayerProfile(
        player_id=player_id,
        fields=(ProfileField(field_key="favorite_food", value="pizza", allow_question_usage=True),),
    )


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


class TestSubmitInitialProfile:
    def _game_with_players(self) -> Game:
        game = Game(game_id="g1")
        game.add_player(Player(player_id="p1", display_name="Dana"))
        game.add_player(Player(player_id="p2", display_name="Omer"))
        return game

    def test_submission_in_lobby_assigns_profile_and_transitions(self) -> None:
        game = self._game_with_players()
        profile = _profile_for("p1")

        game.submit_initial_profile("p1", profile)

        assert game.get_player("p1").profile is profile
        assert game.state is GameState.PROFILE_COLLECTION

    def test_second_players_first_submission_keeps_profile_collection(self) -> None:
        game = self._game_with_players()
        game.submit_initial_profile("p1", _profile_for("p1"))
        profile = _profile_for("p2")

        game.submit_initial_profile("p2", profile)

        assert game.get_player("p2").profile is profile
        assert game.state is GameState.PROFILE_COLLECTION

    def test_unknown_player_id_rejected_without_mutation(self) -> None:
        game = self._game_with_players()

        with pytest.raises(ValueError):
            game.submit_initial_profile("missing", _profile_for("missing"))

        assert game.state is GameState.LOBBY
        assert all(player.profile is None for player in game.players)

    def test_ownership_mismatch_rejected_without_mutation(self) -> None:
        game = self._game_with_players()

        with pytest.raises(ValueError):
            game.submit_initial_profile("p1", _profile_for("p2"))

        assert game.state is GameState.LOBBY
        assert game.get_player("p1").profile is None

    def test_second_initial_submission_for_same_player_rejected(self) -> None:
        game = self._game_with_players()
        original = _profile_for("p1")
        game.submit_initial_profile("p1", original)

        with pytest.raises(ValueError):
            game.submit_initial_profile("p1", _profile_for("p1"))

        assert game.get_player("p1").profile is original
        assert game.state is GameState.PROFILE_COLLECTION

    def test_submission_in_ready_rejected(self) -> None:
        game = self._game_with_players()
        game.submit_initial_profile("p1", _profile_for("p1"))
        game.transition_to(GameState.READY)

        with pytest.raises(ValueError):
            game.submit_initial_profile("p2", _profile_for("p2"))

        assert game.state is GameState.READY
        assert game.get_player("p2").profile is None

    def test_submission_in_finished_rejected(self) -> None:
        game = self._game_with_players()
        game.submit_initial_profile("p1", _profile_for("p1"))
        for target in (
            GameState.READY,
            GameState.QUESTION_ACTIVE,
            GameState.QUESTION_RESULTS,
            GameState.LEADERBOARD,
            GameState.FINISHED,
        ):
            game.transition_to(target)

        with pytest.raises(ValueError):
            game.submit_initial_profile("p2", _profile_for("p2"))

        assert game.state is GameState.FINISHED
        assert game.get_player("p2").profile is None
