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
from app.domain.questions.question import Question, QuestionOption, QuestionType


def _profile_for(player_id: str) -> PlayerProfile:
    return PlayerProfile(
        player_id=player_id,
        fields=(ProfileField(field_key="favorite_food", value="pizza", allow_question_usage=True),),
    )


def _question(index: int, total: int) -> Question:
    return Question(
        question_id=f"q{index}",
        index=index,
        total_questions=total,
        question_type=QuestionType.MULTIPLE_CHOICE,
        text=f"Question {index}?",
        options=(
            QuestionOption(option_id="a", text="Option A"),
            QuestionOption(option_id="b", text="Option B"),
        ),
        correct_option_id="a",
        time_limit_seconds=20,
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


class TestMarkPlayerReady:
    def _collecting_game(self) -> Game:
        """Two players, both with profiles, game in PROFILE_COLLECTION."""
        game = Game(game_id="g1")
        game.add_player(Player(player_id="p1", display_name="Dana"))
        game.add_player(Player(player_id="p2", display_name="Omer"))
        game.submit_initial_profile("p1", _profile_for("p1"))
        game.submit_initial_profile("p2", _profile_for("p2"))
        return game

    def test_player_with_profile_can_be_marked_ready(self) -> None:
        game = self._collecting_game()

        game.mark_player_ready("p1")

        assert game.get_player("p1").is_ready is True

    def test_player_without_profile_cannot_be_marked_ready(self) -> None:
        game = Game(game_id="g1")
        game.add_player(Player(player_id="p1", display_name="Dana"))
        game.add_player(Player(player_id="p2", display_name="Omer"))
        game.submit_initial_profile("p1", _profile_for("p1"))

        with pytest.raises(ValueError):
            game.mark_player_ready("p2")

        assert game.get_player("p2").is_ready is False
        assert game.state is GameState.PROFILE_COLLECTION

    def test_unknown_player_id_rejected(self) -> None:
        game = self._collecting_game()

        with pytest.raises(ValueError):
            game.mark_player_ready("missing")

        assert game.state is GameState.PROFILE_COLLECTION
        assert all(player.is_ready is False for player in game.players)

    def test_marking_ready_in_lobby_rejected(self) -> None:
        game = Game(game_id="g1")
        game.add_player(Player(player_id="p1", display_name="Dana"))

        with pytest.raises(ValueError):
            game.mark_player_ready("p1")

        assert game.state is GameState.LOBBY
        assert game.get_player("p1").is_ready is False

    def test_marking_ready_in_ready_state_rejected(self) -> None:
        game = self._collecting_game()
        game.mark_player_ready("p1")
        game.mark_player_ready("p2")
        assert game.state is GameState.READY

        with pytest.raises(ValueError):
            game.mark_player_ready("p1")

        assert game.state is GameState.READY

    def test_marking_same_player_twice_is_idempotent(self) -> None:
        game = self._collecting_game()
        game.mark_player_ready("p1")

        game.mark_player_ready("p1")

        assert game.get_player("p1").is_ready is True
        assert game.state is GameState.PROFILE_COLLECTION

    def test_partial_readiness_keeps_profile_collection(self) -> None:
        game = self._collecting_game()

        game.mark_player_ready("p1")

        assert game.state is GameState.PROFILE_COLLECTION

    def test_final_player_ready_transitions_to_ready(self) -> None:
        game = self._collecting_game()
        game.mark_player_ready("p1")

        game.mark_player_ready("p2")

        assert game.state is GameState.READY

    def test_single_player_game_transitions_when_ready(self) -> None:
        game = Game(game_id="g1")
        game.add_player(Player(player_id="p1", display_name="Dana"))
        game.submit_initial_profile("p1", _profile_for("p1"))

        game.mark_player_ready("p1")

        assert game.state is GameState.READY

    def test_connected_flag_does_not_affect_all_ready(self) -> None:
        game = self._collecting_game()
        game.get_player("p2").connected = False

        game.mark_player_ready("p1")
        assert game.state is GameState.PROFILE_COLLECTION  # disconnected p2 still counts

        game.mark_player_ready("p2")
        assert game.state is GameState.READY  # and may still be marked ready

    def test_no_unready_behavior_exists(self) -> None:
        assert not any("unready" in name.lower() for name in dir(Game))
        assert not any("unready" in name.lower() for name in dir(Player))


class TestGameStart:
    def _ready_game(self) -> Game:
        """Single-player game brought to READY through the real pre-game flow."""
        game = Game(game_id="g1")
        game.add_player(Player(player_id="p1", display_name="Dana"))
        game.submit_initial_profile("p1", _profile_for("p1"))
        game.mark_player_ready("p1")
        assert game.state is GameState.READY
        return game

    def test_questions_and_current_question_empty_before_start(self) -> None:
        game = Game(game_id="g1")

        assert game.questions == ()
        assert game.current_question is None

    def test_successful_start_from_ready(self) -> None:
        game = self._ready_game()
        supplied = [_question(0, 2), _question(1, 2)]  # a list: start normalizes

        game.start(supplied)

        assert game.state is GameState.QUESTION_ACTIVE
        assert game.questions == tuple(supplied)
        assert game.current_question is game.questions[0]

    def test_empty_sequence_rejected_without_mutation(self) -> None:
        game = self._ready_game()

        with pytest.raises(ValueError):
            game.start([])

        assert game.state is GameState.READY
        assert game.questions == ()
        assert game.current_question is None

    def test_start_from_lobby_rejected_without_mutation(self) -> None:
        game = Game(game_id="g1")

        with pytest.raises(InvalidStateTransitionError):
            game.start([_question(0, 1)])

        assert game.state is GameState.LOBBY
        assert game.questions == ()
        assert game.current_question is None

    def test_start_from_profile_collection_rejected_without_mutation(self) -> None:
        game = Game(game_id="g1")
        game.add_player(Player(player_id="p1", display_name="Dana"))
        game.submit_initial_profile("p1", _profile_for("p1"))

        with pytest.raises(InvalidStateTransitionError):
            game.start([_question(0, 1)])

        assert game.state is GameState.PROFILE_COLLECTION
        assert game.questions == ()
        assert game.current_question is None

    def test_double_start_rejected_and_original_questions_kept(self) -> None:
        game = self._ready_game()
        original = [_question(0, 1)]
        game.start(original)

        with pytest.raises(InvalidStateTransitionError):
            game.start([_question(0, 2), _question(1, 2)])

        assert game.state is GameState.QUESTION_ACTIVE
        assert game.questions == tuple(original)
        assert game.current_question is game.questions[0]

    def test_start_from_finished_rejected_without_mutation(self) -> None:
        game = self._ready_game()
        for target in (
            GameState.QUESTION_ACTIVE,
            GameState.QUESTION_RESULTS,
            GameState.LEADERBOARD,
            GameState.FINISHED,
        ):
            game.transition_to(target)

        with pytest.raises(InvalidStateTransitionError):
            game.start([_question(0, 1)])

        assert game.state is GameState.FINISHED
        assert game.questions == ()
        assert game.current_question is None


class TestAdvanceToNextQuestion:
    def _started_game(self, question_count: int) -> Game:
        """Game started from READY with ``question_count`` questions."""
        game = Game(game_id="g1")
        game.add_player(Player(player_id="p1", display_name="Dana"))
        game.submit_initial_profile("p1", _profile_for("p1"))
        game.mark_player_ready("p1")
        game.start([_question(i, question_count) for i in range(question_count)])
        return game

    def _at_leaderboard(self, question_count: int) -> Game:
        """Started game driven to LEADERBOARD after its first question.

        Uses transition_to for QUESTION_ACTIVE -> QUESTION_RESULTS ->
        LEADERBOARD deliberately: those transitions are not owned by any
        production method yet.
        """
        game = self._started_game(question_count)
        game.transition_to(GameState.QUESTION_RESULTS)
        game.transition_to(GameState.LEADERBOARD)
        return game

    def test_advance_with_remaining_question_activates_next_question(self) -> None:
        game = self._at_leaderboard(question_count=2)
        original_questions = game.questions

        game.advance_to_next_question()

        assert game.state is GameState.QUESTION_ACTIVE
        assert game.current_question is original_questions[1]
        assert game.questions == original_questions

    def test_advance_on_final_question_finishes_game(self) -> None:
        game = self._at_leaderboard(question_count=1)
        original_questions = game.questions

        game.advance_to_next_question()

        assert game.state is GameState.FINISHED
        assert game.current_question is None
        assert game.questions == original_questions

    def test_advance_from_lobby_rejected(self) -> None:
        game = Game(game_id="g1")

        with pytest.raises(ValueError):
            game.advance_to_next_question()

        assert game.state is GameState.LOBBY
        assert game.questions == ()
        assert game.current_question is None

    def test_advance_from_profile_collection_rejected(self) -> None:
        game = Game(game_id="g1")
        game.add_player(Player(player_id="p1", display_name="Dana"))
        game.submit_initial_profile("p1", _profile_for("p1"))

        with pytest.raises(ValueError):
            game.advance_to_next_question()

        assert game.state is GameState.PROFILE_COLLECTION
        assert game.questions == ()
        assert game.current_question is None

    def test_advance_from_ready_rejected(self) -> None:
        game = Game(game_id="g1")
        game.add_player(Player(player_id="p1", display_name="Dana"))
        game.submit_initial_profile("p1", _profile_for("p1"))
        game.mark_player_ready("p1")

        with pytest.raises(ValueError):
            game.advance_to_next_question()

        assert game.state is GameState.READY
        assert game.questions == ()
        assert game.current_question is None

    def test_advance_from_question_active_rejected(self) -> None:
        game = self._started_game(question_count=2)

        with pytest.raises(ValueError):
            game.advance_to_next_question()

        assert game.state is GameState.QUESTION_ACTIVE
        assert game.current_question is game.questions[0]

    def test_advance_from_question_results_rejected(self) -> None:
        game = self._started_game(question_count=2)
        game.transition_to(GameState.QUESTION_RESULTS)

        with pytest.raises(ValueError):
            game.advance_to_next_question()

        assert game.state is GameState.QUESTION_RESULTS
        assert game.current_question is game.questions[0]

    def test_advance_from_finished_rejected(self) -> None:
        game = self._at_leaderboard(question_count=1)
        game.advance_to_next_question()
        original_questions = game.questions

        with pytest.raises(ValueError):
            game.advance_to_next_question()

        assert game.state is GameState.FINISHED
        assert game.current_question is None
        assert game.questions == original_questions

    def test_advance_without_started_sequence_rejected(self) -> None:
        """LEADERBOARD reached by raw transitions (no start): guard must reject."""
        game = Game(game_id="g1")
        for target in (
            GameState.PROFILE_COLLECTION,
            GameState.READY,
            GameState.QUESTION_ACTIVE,
            GameState.QUESTION_RESULTS,
            GameState.LEADERBOARD,
        ):
            game.transition_to(target)
        assert game.questions == ()
        assert game.current_question is None

        with pytest.raises(ValueError):
            game.advance_to_next_question()

        assert game.state is GameState.LEADERBOARD
        assert game.questions == ()
        assert game.current_question is None

    def test_full_two_question_progression(self) -> None:
        game = self._started_game(question_count=2)
        first, second = game.questions
        assert game.state is GameState.QUESTION_ACTIVE
        assert game.current_question is first

        game.transition_to(GameState.QUESTION_RESULTS)
        game.transition_to(GameState.LEADERBOARD)
        game.advance_to_next_question()

        assert game.state is GameState.QUESTION_ACTIVE
        assert game.current_question is second

        game.transition_to(GameState.QUESTION_RESULTS)
        game.transition_to(GameState.LEADERBOARD)
        game.advance_to_next_question()

        assert game.state is GameState.FINISHED
        assert game.current_question is None
        assert game.questions == (first, second)
