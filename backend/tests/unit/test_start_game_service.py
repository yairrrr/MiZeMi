"""Unit tests for StartGameService (MASTER_SPEC.md §11, §12)."""

import pytest

from app.application.start_game import (
    GameNotStartableError,
    NoQuestionsGeneratedError,
    QuestionGenerationConfig,
    StartGameService,
)
from app.domain.game import Game, GameState, Player, PlayerProfile, ProfileField
from app.domain.questions import Question, QuestionGenerator

CONFIG = QuestionGenerationConfig(question_count=5, time_limit_seconds=20, seed=42)


def _profile(player_id: str, fields: list[tuple[str, str | int]]) -> PlayerProfile:
    return PlayerProfile(
        player_id=player_id,
        fields=tuple(
            ProfileField(field_key=key, value=value, allow_question_usage=True)
            for key, value in fields
        ),
    )


def _ready_game(profiles: dict[str, list[tuple[str, str | int]]]) -> Game:
    """A game driven to READY through real domain behavior."""
    game = Game(game_id="g1")
    names = {"p1": "Dana", "p2": "Omer", "p3": "Noa"}
    for player_id in profiles:
        game.add_player(Player(player_id=player_id, display_name=names[player_id]))
    for player_id, fields in profiles.items():
        game.submit_initial_profile(player_id, _profile(player_id, fields))
    for player_id in profiles:
        game.mark_player_ready(player_id)
    assert game.state is GameState.READY
    return game


def _rich_game() -> Game:
    return _ready_game(
        {
            "p1": [("favorite_food", "pizza"), ("city", "Haifa"), ("hobby", "chess")],
            "p2": [("favorite_food", "pizza"), ("city", "Tel Aviv"), ("hobby", "running")],
            "p3": [("favorite_food", "sushi"), ("city", "Haifa"), ("hobby", "chess")],
        }
    )


class EmptyGenerator(QuestionGenerator):
    def generate(self, dataset, **kwargs) -> tuple[Question, ...]:  # type: ignore[override]
        return ()


class TestStartGameService:
    def test_start_generates_questions_and_activates_first(self) -> None:
        game = _rich_game()

        questions = StartGameService().start(game, CONFIG)

        assert questions
        assert game.state is GameState.QUESTION_ACTIVE
        assert game.questions == questions
        assert game.current_question is questions[0]

    def test_generated_questions_use_supplied_configuration(self) -> None:
        game = _rich_game()
        config = QuestionGenerationConfig(question_count=2, time_limit_seconds=45, seed=7)

        questions = StartGameService().start(game, config)

        assert len(questions) <= 2
        assert all(q.time_limit_seconds == 45 for q in questions)
        assert all(q.total_questions == len(questions) for q in questions)

    def test_start_is_deterministic_for_the_same_seed(self) -> None:
        first = StartGameService().start(_rich_game(), CONFIG)
        second = StartGameService().start(_rich_game(), CONFIG)

        assert first == second

    def test_non_consented_fields_never_reach_generated_questions(self) -> None:
        game = Game(game_id="g1")
        game.add_player(Player(player_id="p1", display_name="Dana"))
        game.add_player(Player(player_id="p2", display_name="Omer"))
        game.submit_initial_profile(
            "p1",
            PlayerProfile(
                player_id="p1",
                fields=(
                    ProfileField(field_key="favorite_food", value="pizza", allow_question_usage=True),
                    ProfileField(field_key="personal_fact", value="TOPSECRET", allow_question_usage=False),
                ),
            ),
        )
        game.submit_initial_profile("p2", _profile("p2", [("favorite_food", "sushi")]))
        game.mark_player_ready("p1")
        game.mark_player_ready("p2")

        questions = StartGameService().start(game, CONFIG)

        for question in questions:
            assert "TOPSECRET" not in question.text
            assert all("TOPSECRET" not in option.text for option in question.options)

    def test_start_rejected_when_not_ready(self) -> None:
        game = Game(game_id="g1")
        game.add_player(Player(player_id="p1", display_name="Dana"))

        with pytest.raises(GameNotStartableError) as exc_info:
            StartGameService().start(game, CONFIG)

        assert exc_info.value.state is GameState.LOBBY
        assert game.state is GameState.LOBBY
        assert game.questions == ()

    def test_start_rejected_when_already_started(self) -> None:
        game = _rich_game()
        StartGameService().start(game, CONFIG)
        original = game.questions

        with pytest.raises(GameNotStartableError):
            StartGameService().start(game, CONFIG)

        assert game.questions == original
        assert game.state is GameState.QUESTION_ACTIVE

    def test_zero_generated_questions_leaves_game_in_ready(self) -> None:
        game = _rich_game()

        with pytest.raises(NoQuestionsGeneratedError):
            StartGameService(generator=EmptyGenerator()).start(game, CONFIG)

        assert game.state is GameState.READY
        assert game.questions == ()
        assert game.current_question is None

    def test_service_never_fabricates_more_questions_than_available(self) -> None:
        game = _rich_game()
        config = QuestionGenerationConfig(question_count=99, time_limit_seconds=20, seed=1)

        questions = StartGameService().start(game, config)

        assert 0 < len(questions) < 99
