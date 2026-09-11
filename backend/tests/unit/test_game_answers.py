"""Unit tests for answers, round closing and scores on the Game aggregate (§9.4, §9.5, §11)."""

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.game import (
    AnswerRejectedError,
    AnswerRejection,
    Game,
    GameState,
    InvalidStateTransitionError,
)
from app.domain.scoring import SpeedBonusScoringPolicy
from tests.fixtures.factories import make_game, make_question, make_ready_game

OPENED = datetime(2026, 9, 11, 10, 0, 0, tzinfo=UTC)
SCORING = SpeedBonusScoringPolicy()


def _active_game(question_count: int = 2, player_count: int = 3) -> Game:
    from tests.fixtures.factories import make_players

    game = make_ready_game(players=make_players(player_count))
    questions = tuple(
        make_question(
            f"q{i + 1}",
            index=i,
            total_questions=question_count,
            correct_option_id="b",
            time_limit_seconds=20,
        )
        for i in range(question_count)
    )
    game.start(questions, opened_at=OPENED)
    return game


def _at(ms: int) -> datetime:
    return OPENED + timedelta(milliseconds=ms)


class TestQuestionTiming:
    def test_start_records_opening_time_and_deadline(self) -> None:
        game = _active_game()

        assert game.question_opened_at == OPENED
        assert game.question_deadline == OPENED + timedelta(seconds=20)

    def test_start_without_opening_time_has_no_deadline(self) -> None:
        game = make_ready_game()
        game.start((make_question(),))

        assert game.question_deadline is None

    def test_naive_opening_time_rejected_before_mutation(self) -> None:
        game = make_ready_game()

        with pytest.raises(ValueError):
            game.start((make_question(),), opened_at=datetime(2026, 9, 11, 10, 0))

        assert game.state is GameState.READY


class TestSubmitAnswer:
    def test_valid_answer_is_recorded(self) -> None:
        game = _active_game()

        answer = game.submit_answer("p1", "q1", "b", _at(1_000))

        assert answer.option_id == "b"
        assert game.answer_for("q1", "p1") == answer
        assert game.answers_for("q1") == (answer,)

    @pytest.mark.parametrize(
        ("player_id", "question_id", "option_id", "reason"),
        [
            ("p1", "q2", "b", AnswerRejection.WRONG_QUESTION),
            ("ghost", "q1", "b", AnswerRejection.UNKNOWN_PLAYER),
            ("p1", "q1", "z", AnswerRejection.INVALID_OPTION),
        ],
    )
    def test_invalid_answers_are_rejected(
        self, player_id: str, question_id: str, option_id: str, reason: AnswerRejection
    ) -> None:
        game = _active_game()

        with pytest.raises(AnswerRejectedError) as exc_info:
            game.submit_answer(player_id, question_id, option_id, _at(1_000))

        assert exc_info.value.reason is reason
        assert game.answers_for("q1") == ()

    def test_duplicate_answer_rejected_and_first_kept(self) -> None:
        game = _active_game()
        first = game.submit_answer("p1", "q1", "b", _at(1_000))

        with pytest.raises(AnswerRejectedError) as exc_info:
            game.submit_answer("p1", "q1", "a", _at(2_000))

        assert exc_info.value.reason is AnswerRejection.ALREADY_ANSWERED
        assert game.answer_for("q1", "p1") == first

    def test_answer_after_deadline_rejected(self) -> None:
        game = _active_game()

        with pytest.raises(AnswerRejectedError) as exc_info:
            game.submit_answer("p1", "q1", "b", _at(20_001))

        assert exc_info.value.reason is AnswerRejection.DEADLINE_PASSED

    def test_answer_exactly_at_deadline_accepted(self) -> None:
        game = _active_game()

        game.submit_answer("p1", "q1", "b", _at(20_000))

        assert game.answer_for("q1", "p1") is not None

    def test_answer_outside_question_active_rejected(self) -> None:
        game = make_ready_game()

        with pytest.raises(AnswerRejectedError) as exc_info:
            game.submit_answer("p1", "q1", "b", _at(0))

        assert exc_info.value.reason is AnswerRejection.QUESTION_NOT_ACTIVE

    def test_answer_after_question_closed_rejected(self) -> None:
        game = _active_game()
        game.close_question(SCORING)

        with pytest.raises(AnswerRejectedError) as exc_info:
            game.submit_answer("p1", "q1", "b", _at(1_000))

        assert exc_info.value.reason is AnswerRejection.QUESTION_NOT_ACTIVE

    def test_naive_answer_time_rejected(self) -> None:
        game = _active_game()

        with pytest.raises(ValueError):
            game.submit_answer("p1", "q1", "b", datetime(2026, 9, 11, 10, 0, 1))

    def test_all_players_answered(self) -> None:
        game = _active_game(player_count=2)
        assert game.all_players_answered() is False

        game.submit_answer("p1", "q1", "b", _at(1_000))
        assert game.all_players_answered() is False

        game.submit_answer("p2", "q1", "a", _at(2_000))
        assert game.all_players_answered() is True


class TestCloseQuestion:
    def test_close_transitions_and_scores_every_player(self) -> None:
        game = _active_game(player_count=3)
        game.submit_answer("p1", "q1", "b", _at(0))       # correct, instant
        game.submit_answer("p2", "q1", "a", _at(1_000))   # wrong
        # p3 does not answer

        result = game.close_question(SCORING)

        assert game.state is GameState.QUESTION_RESULTS
        by_player = {r.player_id: r for r in result.player_results}
        assert by_player["p1"].is_correct is True
        assert by_player["p1"].points_awarded == 1000
        assert by_player["p2"].is_correct is False
        assert by_player["p2"].points_awarded == 0
        assert by_player["p3"].option_id is None
        assert by_player["p3"].points_awarded == 0
        assert game.scores == {"p1": 1000, "p2": 0, "p3": 0}

    def test_scores_accumulate_across_questions(self) -> None:
        game = _active_game(question_count=2, player_count=2)
        game.submit_answer("p1", "q1", "b", _at(10_000))  # 750
        game.close_question(SCORING)
        game.show_leaderboard()
        second_open = OPENED + timedelta(minutes=1)
        game.advance_to_next_question(opened_at=second_open)
        game.submit_answer("p1", "q2", "b", second_open)  # 1000

        game.close_question(SCORING)

        assert game.score_of("p1") == 1750
        assert game.score_of("p2") == 0

    def test_player_results_follow_join_order(self) -> None:
        game = _active_game(player_count=3)
        game.submit_answer("p3", "q1", "b", _at(0))
        game.submit_answer("p1", "q1", "b", _at(0))

        result = game.close_question(SCORING)

        assert [r.player_id for r in result.player_results] == ["p1", "p2", "p3"]
        assert [a.player_id for a in result.answers] == ["p3", "p1"]

    def test_last_round_is_exposed(self) -> None:
        game = _active_game()
        result = game.close_question(SCORING)

        assert game.last_round is result
        assert result.result_for("p1") is not None
        assert result.result_for("ghost") is None

    def test_close_outside_question_active_is_rejected_without_changes(self) -> None:
        game = make_ready_game()

        with pytest.raises(InvalidStateTransitionError):
            game.close_question(SCORING)

        assert game.state is GameState.READY
        assert game.scores == {"p1": 0, "p2": 0, "p3": 0}

    def test_double_close_is_rejected(self) -> None:
        game = _active_game()
        game.submit_answer("p1", "q1", "b", _at(0))
        game.close_question(SCORING)

        with pytest.raises(InvalidStateTransitionError):
            game.close_question(SCORING)

        assert game.score_of("p1") == 1000  # not double-counted

    def test_close_without_known_opening_time_still_scores(self) -> None:
        game = make_ready_game()
        game.start((make_question(correct_option_id="a"),))
        game.submit_answer("p1", "q1", "a", _at(0))

        game.close_question(SCORING)

        assert game.score_of("p1") == 1000


class TestLeaderboardAndProgression:
    def test_show_leaderboard_transition(self) -> None:
        game = _active_game()
        game.close_question(SCORING)

        game.show_leaderboard()

        assert game.state is GameState.LEADERBOARD

    def test_show_leaderboard_rejected_while_question_active(self) -> None:
        game = _active_game()

        with pytest.raises(InvalidStateTransitionError):
            game.show_leaderboard()

    def test_advance_sets_new_opening_time(self) -> None:
        game = _active_game(question_count=2)
        game.close_question(SCORING)
        game.show_leaderboard()
        later = OPENED + timedelta(minutes=2)

        game.advance_to_next_question(opened_at=later)

        assert game.current_question.question_id == "q2"
        assert game.question_opened_at == later
        assert game.answers_for("q2") == ()

    def test_finishing_clears_timing(self) -> None:
        game = _active_game(question_count=1)
        game.close_question(SCORING)
        game.show_leaderboard()

        game.advance_to_next_question(opened_at=OPENED)

        assert game.state is GameState.FINISHED
        assert game.question_opened_at is None
        assert game.question_deadline is None


class TestRemovePlayer:
    def test_remove_player_in_lobby(self) -> None:
        game = make_game()

        game.remove_player("p2")

        assert [p.player_id for p in game.players] == ["p1", "p3"]
        assert "p2" not in game.scores

    def test_removing_the_last_unready_player_completes_readiness(self) -> None:
        from tests.fixtures.factories import collect_profiles

        game = collect_profiles(make_game())
        game.mark_player_ready("p1")
        game.mark_player_ready("p2")
        assert game.state is GameState.PROFILE_COLLECTION

        game.remove_player("p3")

        assert game.state is GameState.READY

    def test_removal_rejected_after_start(self) -> None:
        game = _active_game()

        with pytest.raises(ValueError):
            game.remove_player("p1")

        assert len(game.players) == 3

    def test_unknown_player_removal_rejected(self) -> None:
        with pytest.raises(ValueError):
            make_game().remove_player("ghost")
