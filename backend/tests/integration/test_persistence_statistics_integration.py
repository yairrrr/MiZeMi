"""Cross-module integration for Developer D's pieces (MASTER_SPEC.md §15, §9.6, §19).

Proves that the persistence layer and the statistics calculator compose with
the *real* code of the other workstreams:

- Developer A: create/join REST, profile/ready over WebSocket, StartGameService,
  AdvanceQuestionService.
- Developer B: the real QuestionGenerator pipeline.
- Developer D: SqlAlchemyGameRepository, QuestionStatisticsCalculator.

No production code is exercised through a mock — only through its public API.
"""

import pytest
from fastapi.testclient import TestClient

from app.application.advance_question import AdvanceQuestionService
from app.application.repositories import FinishedGameRecord
from app.application.start_game import QuestionGenerationConfig, StartGameService
from app.domain.game import GameState
from app.domain.statistics import QuestionStatisticsCalculator
from app.infrastructure.repositories import SqlAlchemyGameRepository
from app.main import create_app
from tests.fixtures.factories import answers_from_counts, play_to_finished
from tests.fixtures.live import create_room, join, player_ws, submit_profile_and_ready

CONFIG = QuestionGenerationConfig(question_count=3, time_limit_seconds=20, seed=42)

# Valid §9.2 profiles: the four required fields plus an optional age.
PROFILES: dict[str, dict[str, str | int]] = {
    "Dana": {"favorite_food": "pizza", "city": "Haifa", "age": 27},
    "Omer": {"favorite_food": "pizza", "city": "Tel Aviv", "age": 31},
    "Noa": {"favorite_food": "sushi", "city": "Haifa", "age": 27},
    "Yael": {"favorite_food": "pizza", "city": "Haifa", "age": 41},
}


def _ready_room(client: TestClient) -> tuple[str, str]:
    room = create_room(client)
    players = {name: join(client, room.room_code, name) for name in PROFILES}
    for name, values in PROFILES.items():
        with player_ws(client, room.room_code, players[name]) as ws:
            submit_profile_and_ready(ws, room.game_id, players[name], **values)
    return room.room_code, room.game_id


class TestFullVerticalIsPersisted:
    def test_played_out_game_persists_and_reads_back(self, db_session) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, _ = _ready_room(client)
        game = app.state.room_registry.get(room_code).game

        questions = StartGameService().start(game, CONFIG)
        play_to_finished(game)
        assert game.state is GameState.FINISHED

        repo = SqlAlchemyGameRepository(db_session)
        repo.save(game)
        db_session.commit()
        record = repo.get(game.game_id)

        assert isinstance(record, FinishedGameRecord)
        assert record.state == "FINISHED"
        assert {p.display_name for p in record.players} == set(PROFILES)
        assert len(record.questions) == len(questions)

    def test_persisted_profiles_match_what_was_submitted_over_the_wire(
        self, db_session
    ) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, _ = _ready_room(client)
        game = app.state.room_registry.get(room_code).game

        repo = SqlAlchemyGameRepository(db_session)
        repo.save(game)
        db_session.commit()
        record = repo.get(game.game_id)

        dana = next(p for p in record.players if p.display_name == "Dana")
        stored = {f.field_key: f.value for f in dana.profile_fields}
        assert stored == {
            "city": "Haifa",
            "favorite_food": "pizza",
            "hobby": "chess",
            "favorite_music": "Rock",
            "age": 27,
        }
        assert [f.field_key for f in dana.profile_fields][:4] == [
            "city",
            "favorite_food",
            "hobby",
            "favorite_music",
        ]
        assert all(f.allow_question_usage for f in dana.profile_fields)


class TestGeneratedQuestionsSurvivePersistence:
    def test_generated_question_set_round_trips_intact(self, db_session) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, _ = _ready_room(client)
        game = app.state.room_registry.get(room_code).game
        questions = StartGameService().start(game, CONFIG)
        play_to_finished(game)

        repo = SqlAlchemyGameRepository(db_session)
        repo.save(game)
        db_session.commit()
        record = repo.get(game.game_id)

        for original, stored in zip(questions, record.questions, strict=True):
            assert stored.question_id == original.question_id
            assert stored.text == original.text
            assert stored.correct_option_id == original.correct_option_id
            assert [o.option_id for o in stored.options] == [
                o.option_id for o in original.options
            ]
            assert stored.question_type == "multiple_choice"


class TestStatisticsOnGeneratedQuestions:
    def test_calculator_produces_the_contract_shape_for_a_real_question(
        self, db_session
    ) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, _ = _ready_room(client)
        game = app.state.room_registry.get(room_code).game
        questions = StartGameService().start(game, CONFIG)

        question = questions[0]
        option_ids = [option.option_id for option in question.options]
        # everyone answers the first option
        answers = answers_from_counts({option_ids[0]: len(PROFILES)})

        stats = QuestionStatisticsCalculator().calculate(
            question, answers, player_count=len(PROFILES)
        )

        assert stats.question_id == question.question_id
        assert stats.correct_option_id == question.correct_option_id
        assert [entry.option_id for entry in stats.answer_distribution] == option_ids
        assert stats.answered_count == len(PROFILES)
        assert stats.player_count == len(PROFILES)
        assert sum(entry.count for entry in stats.answer_distribution) == len(PROFILES)

    def test_progression_service_and_persistence_agree_on_finished(
        self, db_session
    ) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, _ = _ready_room(client)
        game = app.state.room_registry.get(room_code).game
        StartGameService().start(game, CONFIG)

        advance = AdvanceQuestionService()
        while not advance.is_finished(game):
            if game.state is GameState.QUESTION_ACTIVE:
                game.transition_to(GameState.QUESTION_RESULTS)
            if game.state is GameState.QUESTION_RESULTS:
                game.transition_to(GameState.LEADERBOARD)
            advance.advance(game)

        repo = SqlAlchemyGameRepository(db_session)
        repo.save(game)
        db_session.commit()
        assert repo.get(game.game_id).state == "FINISHED"
