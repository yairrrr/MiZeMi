"""Unit tests for AdvanceQuestionService (MASTER_SPEC.md §11)."""

import pytest

from app.application.advance_question import (
    AdvanceQuestionService,
    GameNotAdvanceableError,
)
from app.application.start_game import QuestionGenerationConfig, StartGameService
from app.domain.game import Game, GameState, Player, PlayerProfile, ProfileField

CONFIG = QuestionGenerationConfig(question_count=3, time_limit_seconds=20, seed=42)


def _started_game() -> Game:
    """A real game driven through profiles and readiness into QUESTION_ACTIVE."""
    game = Game(game_id="g1")
    profiles = {
        "p1": ("Dana", [("favorite_food", "pizza"), ("city", "Haifa"), ("hobby", "chess")]),
        "p2": ("Omer", [("favorite_food", "pizza"), ("city", "Tel Aviv"), ("hobby", "running")]),
        "p3": ("Noa", [("favorite_food", "sushi"), ("city", "Haifa"), ("hobby", "chess")]),
    }
    for player_id, (name, _) in profiles.items():
        game.add_player(Player(player_id=player_id, display_name=name))
    for player_id, (_, fields) in profiles.items():
        game.submit_initial_profile(
            player_id,
            PlayerProfile(
                player_id=player_id,
                fields=tuple(
                    ProfileField(field_key=k, value=v, allow_question_usage=True)
                    for k, v in fields
                ),
            ),
        )
    for player_id in profiles:
        game.mark_player_ready(player_id)
    StartGameService().start(game, CONFIG)
    return game


def _to_leaderboard(game: Game) -> None:
    """Drive the round to LEADERBOARD using domain transitions.

    QUESTION_ACTIVE → QUESTION_RESULTS → LEADERBOARD have no application
    owner yet (they depend on the answer/results flow), so tests use the
    domain transitions directly.
    """
    game.transition_to(GameState.QUESTION_RESULTS)
    game.transition_to(GameState.LEADERBOARD)


class TestAdvanceQuestionService:
    def test_advance_activates_the_next_question(self) -> None:
        game = _started_game()
        first = game.current_question
        _to_leaderboard(game)

        question = AdvanceQuestionService().advance(game)

        assert game.state is GameState.QUESTION_ACTIVE
        assert question is game.questions[1]
        assert question is not first
        assert game.current_question is question

    def test_advance_after_final_question_finishes_the_game(self) -> None:
        game = _started_game()
        service = AdvanceQuestionService()
        for _ in range(len(game.questions) - 1):
            _to_leaderboard(game)
            service.advance(game)
        _to_leaderboard(game)

        question = service.advance(game)

        assert question is None
        assert game.state is GameState.FINISHED
        assert game.current_question is None
        assert service.is_finished(game) is True

    def test_questions_are_played_in_selection_order(self) -> None:
        game = _started_game()
        service = AdvanceQuestionService()
        played = [game.current_question]
        while game.state is not GameState.FINISHED:
            _to_leaderboard(game)
            nxt = service.advance(game)
            if nxt is not None:
                played.append(nxt)

        assert played == list(game.questions)
        assert [q.index for q in played] == list(range(len(game.questions)))

    def test_advance_rejected_outside_leaderboard(self) -> None:
        game = _started_game()

        with pytest.raises(GameNotAdvanceableError) as exc_info:
            AdvanceQuestionService().advance(game)

        assert exc_info.value.state is GameState.QUESTION_ACTIVE
        assert game.state is GameState.QUESTION_ACTIVE
        assert game.current_question is game.questions[0]

    def test_advance_rejected_before_the_game_starts(self) -> None:
        game = Game(game_id="g1")

        with pytest.raises(GameNotAdvanceableError):
            AdvanceQuestionService().advance(game)

        assert game.state is GameState.LOBBY

    def test_advance_rejected_after_finished(self) -> None:
        game = _started_game()
        service = AdvanceQuestionService()
        while game.state is not GameState.FINISHED:
            _to_leaderboard(game)
            service.advance(game)

        with pytest.raises(GameNotAdvanceableError):
            service.advance(game)

        assert game.state is GameState.FINISHED
