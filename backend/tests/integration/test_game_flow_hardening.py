"""End-to-end hardening tests for the Developer A game flow.

Drives the real REST + WebSocket vertical (create → join → connect →
profile → ready), then exercises the application-layer start and
progression services against the same live app state, checking the
error/boundary behavior Developer A owns.
"""

import asyncio
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.application.advance_question import (
    AdvanceQuestionService,
    GameNotAdvanceableError,
)
from app.application.start_game import (
    GameNotStartableError,
    NoQuestionsGeneratedError,
    QuestionGenerationConfig,
    StartGameService,
)
from app.domain.game import GameState
from app.domain.questions import Question, QuestionGenerator
from app.main import create_app
from app.realtime.game_events import broadcast_question_started

CONFIG = QuestionGenerationConfig(question_count=3, time_limit_seconds=20, seed=42)
TIMESTAMP = "2026-09-05T10:00:00.000Z"

PROFILES = {
    "Dana": [("favorite_food", "pizza"), ("city", "Haifa"), ("hobby", "chess")],
    "Omer": [("favorite_food", "pizza"), ("city", "Tel Aviv"), ("hobby", "running")],
    "Noa": [("favorite_food", "sushi"), ("city", "Haifa"), ("hobby", "chess")],
}


class EmptyGenerator(QuestionGenerator):
    def generate(self, dataset, **kwargs) -> tuple[Question, ...]:  # type: ignore[override]
        return ()


def _ws(room_code: str, player_id: str) -> str:
    return f"/ws/rooms/{room_code}?player_id={player_id}"


def _envelope(event: str, payload: dict, game_id: str) -> dict:
    return {"event": event, "payload": payload, "timestamp": TIMESTAMP, "game_id": game_id}


def _ready_room(client: TestClient) -> tuple[str, str, dict[str, str]]:
    """Create a room, join every player, submit profiles, mark all ready."""
    created = client.post("/api/v1/rooms").json()
    room_code, game_id = created["room_code"], created["game_id"]
    ids: dict[str, str] = {}
    for name in PROFILES:
        ids[name] = client.post(
            f"/api/v1/rooms/{room_code}/players", json={"display_name": name}
        ).json()["player"]["player_id"]
    for name, fields in PROFILES.items():
        payload = {
            "player_id": ids[name],
            "fields": [
                {"field_key": k, "value": v, "allow_question_usage": True} for k, v in fields
            ],
        }
        with client.websocket_connect(_ws(room_code, ids[name])) as ws:
            ws.send_json(_envelope("player.profile_submit", payload, game_id))
            ws.send_json(_envelope("player.ready", {}, game_id))
    return room_code, game_id, ids


class TestFullVerticalToStart:
    def test_rest_and_realtime_vertical_reaches_ready_then_starts(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, _ = _ready_room(client)
        game = app.state.room_registry.get(room_code).game
        assert game.state is GameState.READY

        questions = StartGameService().start(game, CONFIG)

        assert questions
        assert game.state is GameState.QUESTION_ACTIVE
        assert game.current_question is questions[0]

    def test_started_question_broadcasts_to_connected_players(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _ready_room(client)
        game = app.state.room_registry.get(room_code).game
        questions = StartGameService().start(game, CONFIG)

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            asyncio.run(
                broadcast_question_started(
                    app.state.room_connections, room_code, questions[0], game.game_id
                )
            )
            message = ws.receive_json()

        assert message["event"] == "question.started"
        assert message["payload"]["question_id"] == questions[0].question_id
        assert message["payload"]["time_limit_seconds"] == 20
        assert message["payload"]["total_questions"] == len(questions)

    def test_broadcast_never_leaks_the_correct_option(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _ready_room(client)
        game = app.state.room_registry.get(room_code).game
        questions = StartGameService().start(game, CONFIG)

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            asyncio.run(
                broadcast_question_started(
                    app.state.room_connections, room_code, questions[0], game.game_id
                )
            )
            message = ws.receive_json()

        # Structural check: the correct answer has no key to travel in.
        # (Its *value* is one of the option ids, which are legitimately sent.)
        assert "correct_option_id" not in str(message)
        assert set(message["payload"].keys()) == {
            "question_id",
            "index",
            "total_questions",
            "question_type",
            "text",
            "options",
            "time_limit_seconds",
            "started_at",
        }
        assert all(set(o.keys()) == {"option_id", "text"} for o in message["payload"]["options"])

    def test_started_at_is_server_generated_not_client_supplied(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, _, ids = _ready_room(client)
        game = app.state.room_registry.get(room_code).game
        questions = StartGameService().start(game, CONFIG)
        before = datetime.now(UTC)

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            asyncio.run(
                broadcast_question_started(
                    app.state.room_connections, room_code, questions[0], game.game_id
                )
            )
            started_at = ws.receive_json()["payload"]["started_at"]

        stamped = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        assert stamped >= before.replace(microsecond=0)
        assert started_at != TIMESTAMP  # never the client's clock


class TestStartBoundaries:
    def test_start_rejected_before_all_players_are_ready(self) -> None:
        app = create_app()
        client = TestClient(app)
        created = client.post("/api/v1/rooms").json()
        room_code, game_id = created["room_code"], created["game_id"]
        player_id = client.post(
            f"/api/v1/rooms/{room_code}/players", json={"display_name": "Dana"}
        ).json()["player"]["player_id"]
        game = app.state.room_registry.get(room_code).game

        with pytest.raises(GameNotStartableError):
            StartGameService().start(game, CONFIG)

        assert game.state is GameState.LOBBY
        assert game.questions == ()

    def test_zero_generated_questions_keeps_the_room_in_ready(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, _, _ = _ready_room(client)
        game = app.state.room_registry.get(room_code).game

        with pytest.raises(NoQuestionsGeneratedError):
            StartGameService(generator=EmptyGenerator()).start(game, CONFIG)

        assert game.state is GameState.READY
        assert game.current_question is None

    def test_double_start_is_rejected_and_keeps_the_first_question_set(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, _, _ = _ready_room(client)
        game = app.state.room_registry.get(room_code).game
        questions = StartGameService().start(game, CONFIG)

        with pytest.raises(GameNotStartableError):
            StartGameService().start(game, CONFIG)

        assert game.questions == questions
        assert game.current_question is questions[0]


class TestProgressionBoundaries:
    def test_full_progression_plays_every_question_then_finishes(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, _, _ = _ready_room(client)
        game = app.state.room_registry.get(room_code).game
        questions = StartGameService().start(game, CONFIG)
        service = AdvanceQuestionService()

        played = [game.current_question]
        while game.state is not GameState.FINISHED:
            game.transition_to(GameState.QUESTION_RESULTS)
            game.transition_to(GameState.LEADERBOARD)
            nxt = service.advance(game)
            if nxt is not None:
                played.append(nxt)

        assert played == list(questions)
        assert game.state is GameState.FINISHED
        assert game.current_question is None

    def test_advance_rejected_during_an_active_question(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, _, _ = _ready_room(client)
        game = app.state.room_registry.get(room_code).game
        StartGameService().start(game, CONFIG)

        with pytest.raises(GameNotAdvanceableError):
            AdvanceQuestionService().advance(game)

        assert game.state is GameState.QUESTION_ACTIVE

    def test_each_question_gets_a_fresh_started_at_on_broadcast(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, _, ids = _ready_room(client)
        game = app.state.room_registry.get(room_code).game
        StartGameService().start(game, CONFIG)

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            asyncio.run(
                broadcast_question_started(
                    app.state.room_connections, room_code, game.current_question, game.game_id
                )
            )
            first = ws.receive_json()["payload"]

            game.transition_to(GameState.QUESTION_RESULTS)
            game.transition_to(GameState.LEADERBOARD)
            second_question = AdvanceQuestionService().advance(game)
            asyncio.run(
                broadcast_question_started(
                    app.state.room_connections, room_code, second_question, game.game_id
                )
            )
            second = ws.receive_json()["payload"]

        assert first["question_id"] != second["question_id"]
        assert second["index"] == first["index"] + 1
        assert second["started_at"] >= first["started_at"]


class TestConnectionHardening:
    def test_disconnect_cleans_up_registration_and_connected_flag(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, _, ids = _ready_room(client)
        game = app.state.room_registry.get(room_code).game

        with client.websocket_connect(_ws(room_code, ids["Dana"])):
            assert game.get_player(ids["Dana"]).connected is True
            assert len(app.state.room_connections.connections_for(room_code)) == 1

        assert game.get_player(ids["Dana"]).connected is False
        assert app.state.room_connections.connections_for(room_code) == ()

    def test_unknown_room_and_player_are_closed_without_registration(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, _, _ = _ready_room(client)

        for url in (_ws("ZZZZZ2", "whoever"), _ws(room_code, "not-a-player")):
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect(url):
                    pytest.fail("session must not be established")  # pragma: no cover

        assert app.state.room_connections.connections_for(room_code) == ()

    def test_socket_stays_usable_after_recoverable_validation_errors(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _ready_room(client)
        game = app.state.room_registry.get(room_code).game
        questions = StartGameService().start(game, CONFIG)

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json({"event": "player.ready", "payload": {}})  # malformed
            assert ws.receive_json()["payload"]["error"]["code"] == "VALIDATION_ERROR"
            ws.send_json(_envelope("player.dance", {}, game_id))  # unknown event
            assert ws.receive_json()["payload"]["error"]["code"] == "UNKNOWN_EVENT"
            ws.send_json(_envelope("player.ready", {}, "another-game"))  # game_id mismatch
            assert ws.receive_json()["payload"]["error"]["code"] == "VALIDATION_ERROR"

            # Still delivering broadcasts on the same socket.
            asyncio.run(
                broadcast_question_started(
                    app.state.room_connections, room_code, questions[0], game.game_id
                )
            )
            assert ws.receive_json()["event"] == "question.started"

        assert game.state is GameState.QUESTION_ACTIVE

    def test_rejected_commands_do_not_mutate_game_state(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _ready_room(client)
        game = app.state.room_registry.get(room_code).game
        StartGameService().start(game, CONFIG)
        state_before = game.state
        questions_before = game.questions

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            # ready is invalid in QUESTION_ACTIVE
            ws.send_json(_envelope("player.ready", {}, game_id))
            assert ws.receive_json()["payload"]["error"]["code"] == "VALIDATION_ERROR"

        assert game.state is state_before
        assert game.questions == questions_before
        assert game.get_player(ids["Dana"]).is_ready is True  # unchanged from pre-game


class TestHostOnlyActionsDoNotMutateState:
    """Host authorization is deferred, so no player action may start or advance.

    These tests assert only that game state is unchanged. They deliberately
    do NOT assert what the server replies to a registry-known but
    unimplemented event: that response is a temporary implementation gap for
    each event's own task to define, not a protocol guarantee to freeze.
    """

    def test_player_sending_game_start_does_not_start_the_game(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _ready_room(client)
        game = app.state.room_registry.get(room_code).game
        assert game.state is GameState.READY

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json(_envelope("game.start", {}, game_id))

        assert game.state is GameState.READY
        assert game.questions == ()
        assert game.current_question is None

    def test_player_sending_game_next_does_not_advance_the_game(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _ready_room(client)
        game = app.state.room_registry.get(room_code).game
        StartGameService().start(game, CONFIG)
        game.transition_to(GameState.QUESTION_RESULTS)
        game.transition_to(GameState.LEADERBOARD)
        question_before = game.current_question

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json(_envelope("game.next", {}, game_id))

        assert game.state is GameState.LEADERBOARD
        assert game.current_question is question_before

    def test_player_sending_answer_submit_records_nothing(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _ready_room(client)
        game = app.state.room_registry.get(room_code).game
        questions = StartGameService().start(game, CONFIG)

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json(
                _envelope(
                    "answer.submit",
                    {"question_id": questions[0].question_id, "option_id": "a"},
                    game_id,
                )
            )

        assert game.state is GameState.QUESTION_ACTIVE
        assert game.current_question is questions[0]
