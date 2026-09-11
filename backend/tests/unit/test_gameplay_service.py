"""Unit tests for GameplayService orchestration (MASTER_SPEC.md §9.4–§9.7, §11)."""

from datetime import UTC, datetime, timedelta

import pytest

from app.application.gameplay import (
    GameplayConfig,
    GameplayService,
    NextStep,
    seed_for_game,
)
from app.application.start_game import GameNotStartableError
from app.domain.game.config import GameConfig
from app.domain.game import AnswerRejectedError, GameState, InvalidStateTransitionError
from tests.fixtures.factories import make_ready_game

START = datetime(2026, 9, 11, 10, 0, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self, start: datetime = START) -> None:
        self.current = start

    def __call__(self) -> datetime:
        return self.current

    def advance(self, **delta: float) -> None:
        self.current = self.current + timedelta(**delta)


def _service(clock: FakeClock, *, count: int = 3, limit: int = 20) -> GameplayService:
    return GameplayService(
        GameplayConfig(questions_per_game=count, time_limit_seconds=limit), clock=clock
    )


def _answer_correct(service: GameplayService, game, player_id: str):
    question = game.current_question
    return service.submit_answer(game, player_id, question.question_id, question.correct_option_id)


class TestStartGame:
    def test_start_uses_configured_count_limit_and_server_clock(self) -> None:
        clock = FakeClock()
        game = make_ready_game(config=GameConfig(question_count=2))

        questions = _service(clock, count=2, limit=15).start_game(game)

        assert 0 < len(questions) <= 2
        assert all(q.time_limit_seconds == 15 for q in questions)
        assert game.state is GameState.QUESTION_ACTIVE
        assert game.question_opened_at == START
        assert game.question_deadline == START + timedelta(seconds=15)

    def test_question_set_is_reproducible_per_game(self) -> None:
        first = _service(FakeClock()).start_game(make_ready_game("game-x"))
        second = _service(FakeClock()).start_game(make_ready_game("game-x"))

        assert first == second
        assert seed_for_game("game-x") == seed_for_game("game-x")
        assert seed_for_game("game-x") != seed_for_game("game-y")

    def test_start_rejected_when_not_ready(self) -> None:
        game = make_ready_game(config=GameConfig(question_count=2))
        _service(FakeClock()).start_game(game)

        with pytest.raises(GameNotStartableError):
            _service(FakeClock()).start_game(game)


class TestAnswers:
    def test_answer_is_stamped_with_server_time(self) -> None:
        clock = FakeClock()
        service = _service(clock)
        game = make_ready_game(config=GameConfig(question_count=2))
        service.start_game(game)
        clock.advance(seconds=3)

        outcome = _answer_correct(service, game, "p1")

        assert outcome.answer.answered_at == START + timedelta(seconds=3)
        assert outcome.all_answered is False

    def test_all_answered_reported_on_last_answer(self) -> None:
        service = _service(FakeClock())
        game = make_ready_game(config=GameConfig(question_count=2))
        service.start_game(game)
        _answer_correct(service, game, "p1")
        _answer_correct(service, game, "p2")

        outcome = _answer_correct(service, game, "p3")

        assert outcome.all_answered is True

    def test_answer_after_deadline_uses_server_clock(self) -> None:
        clock = FakeClock()
        service = _service(clock, limit=10)
        game = make_ready_game(config=GameConfig(question_count=2))
        service.start_game(game)
        clock.advance(seconds=10, milliseconds=1)

        with pytest.raises(AnswerRejectedError):
            _answer_correct(service, game, "p1")


class TestRoundFlow:
    def test_close_scores_and_leaderboard_ranks(self) -> None:
        clock = FakeClock()
        service = _service(clock)
        game = make_ready_game(config=GameConfig(question_count=2))
        service.start_game(game)
        _answer_correct(service, game, "p2")  # instant -> 1000
        clock.advance(seconds=10)
        _answer_correct(service, game, "p1")  # halfway -> 750

        result = service.close_question(game)
        board = service.leaderboard(game)

        assert game.state is GameState.QUESTION_RESULTS
        assert result.result_for("p2").points_awarded == 1000
        assert result.result_for("p1").points_awarded == 750
        assert [(e.player_id, e.rank, e.total_score) for e in board] == [
            ("p2", 1, 1000),
            ("p1", 2, 750),
            ("p3", 3, 0),
        ]

    def test_statistics_count_every_answer(self) -> None:
        service = _service(FakeClock())
        game = make_ready_game(config=GameConfig(question_count=2))
        service.start_game(game)
        _answer_correct(service, game, "p1")
        _answer_correct(service, game, "p2")

        stats = service.question_statistics(game, service.close_question(game))

        assert stats.answered_count == 2
        assert stats.player_count == 3
        assert sum(entry.count for entry in stats.answer_distribution) == 2

    def test_next_walks_results_leaderboard_question_and_finish(self) -> None:
        clock = FakeClock()
        service = _service(clock, count=2)
        game = make_ready_game(config=GameConfig(question_count=2))
        questions = service.start_game(game)
        assert len(questions) == 2

        service.close_question(game)
        assert service.next(game).step is NextStep.LEADERBOARD
        assert game.state is GameState.LEADERBOARD

        clock.advance(minutes=1)
        outcome = service.next(game)
        assert outcome.step is NextStep.QUESTION
        assert outcome.question is questions[1]
        assert game.question_opened_at == START + timedelta(minutes=1)

        service.close_question(game)
        service.next(game)
        assert service.next(game).step is NextStep.FINISHED
        assert game.state is GameState.FINISHED

    def test_next_rejected_while_question_active(self) -> None:
        service = _service(FakeClock())
        game = make_ready_game(config=GameConfig(question_count=2))
        service.start_game(game)

        with pytest.raises(InvalidStateTransitionError):
            service.next(game)

        assert game.state is GameState.QUESTION_ACTIVE
