"""Integration between GameplayService and the optional AI generator."""

from __future__ import annotations

import pytest
from unittest.mock import Mock

from app.application.gameplay import GameplayConfig, GameplayService
from app.domain.game import Game, GameState, Player, PlayerProfile, ProfileField
from app.domain.game.config import GameConfig
from app.domain.questions.question import Difficulty, Question, QuestionOption, QuestionType
from app.infrastructure.ai_client import AIGenerationError


def _bare_player(pid: str, name: str) -> Player:
    return Player(pid, name)


def _profile(pid: str, *fields: tuple[str, str, bool]) -> PlayerProfile:
    return PlayerProfile(
        pid, tuple(ProfileField(k, v, consent) for k, v, consent in fields),
    )


def _ready_game(source: str = "algorithmic") -> Game:
    """Drive a game through the real state machine to READY."""
    game = Game(game_id=f"g_{source}", config=GameConfig(5, "he", source))
    players = [("p1", "אליק"), ("p2", "יאיר"), ("p3", "נועה")]
    for pid, name in players:
        game.add_player(_bare_player(pid, name))
    for i, (pid, _) in enumerate(players):
        game.submit_initial_profile(pid, _profile(
            pid,
            ("city", ["תל אביב", "חיפה", "חיפה"][i], True),
            ("favorite_food", ["פיצה", "סושי", "פיצה"][i], True),
            ("hobby", ["כדורגל", "ריצה", "קריאה"][i], True),
            ("favorite_music", ["Pop", "Rock", "Pop"][i], True),
        ))
    for pid, _ in players:
        game.mark_player_ready(pid)
    assert game.state is GameState.READY
    return game


class TestAIAvailabilityFlag:
    def test_defaults_to_false_without_ai_generator(self):
        service = GameplayService(GameplayConfig(5, 20))
        assert service.ai_available is False

    def test_true_when_ai_generator_passed(self):
        service = GameplayService(GameplayConfig(5, 20), ai_generator=Mock())
        assert service.ai_available is True


class TestStartSelection:
    def test_algorithmic_game_never_calls_ai(self):
        ai = Mock()
        ai.generate = Mock(return_value=())
        service = GameplayService(GameplayConfig(5, 20), ai_generator=ai)
        service.start_game(_ready_game(source="algorithmic"))
        ai.generate.assert_not_called()

    def test_ai_game_calls_ai_generator(self):
        fake_q = Question(
            question_id="q1", index=0, total_questions=1,
            question_type=QuestionType.MULTIPLE_CHOICE,
            text="x", options=(QuestionOption("a", "a"), QuestionOption("b", "b")),
            correct_option_id="a", time_limit_seconds=20,
            difficulty=Difficulty.EASY, language="he",
            source_rule_id="ai_group_insight", explanation="y", knowledge_version="ai",
        )
        ai = Mock()
        ai.generate = Mock(return_value=(fake_q,))
        service = GameplayService(GameplayConfig(5, 20), ai_generator=ai)
        questions = service.start_game(_ready_game(source="ai"))
        assert ai.generate.called
        assert questions[0].source_rule_id == "ai_group_insight"

    def test_ai_failure_falls_back_to_algorithmic(self):
        ai = Mock()
        ai.generate = Mock(side_effect=AIGenerationError("boom"))
        service = GameplayService(GameplayConfig(5, 20), ai_generator=ai)
        questions = service.start_game(_ready_game(source="ai"))
        # The game started via the real algorithmic engine; questions exist
        # and are not AI-flagged.
        assert len(questions) >= 1
        assert questions[0].source_rule_id != "ai_group_insight"

    def test_ai_game_without_generator_uses_algorithmic(self):
        service = GameplayService(GameplayConfig(5, 20), ai_generator=None)
        questions = service.start_game(_ready_game(source="ai"))
        assert all(q.source_rule_id != "ai_group_insight" for q in questions)
