"""Integration tests for live connection registration and broadcast delivery.

Covers the wiring between the WebSocket endpoint and the room connection
registry (MASTER_SPEC.md §14): accepted connections receive room events and
deregister on disconnect.
"""

import asyncio
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.domain.questions import Question, QuestionOption, QuestionType
from app.main import create_app
from app.realtime.game_events import broadcast_question_started

STARTED_AT = datetime(2026, 9, 5, 10, 15, 30, tzinfo=UTC)


def _question() -> Question:
    return Question(
        question_id="q1",
        index=0,
        total_questions=2,
        question_type=QuestionType.MULTIPLE_CHOICE,
        text="Who is the only player from Haifa?",
        options=(
            QuestionOption(option_id="a", text="Dana"),
            QuestionOption(option_id="b", text="Omer"),
        ),
        correct_option_id="b",
        time_limit_seconds=20,
    )


def _room_with_player(client: TestClient, name: str = "Dana") -> tuple[str, str]:
    room_code = client.post("/api/v1/rooms").json()["room_code"]
    player_id = client.post(
        f"/api/v1/rooms/{room_code}/players", json={"display_name": name}
    ).json()["player"]["player_id"]
    return room_code, player_id


def _ws(room_code: str, player_id: str) -> str:
    return f"/ws/rooms/{room_code}?player_id={player_id}"


class TestConnectionRegistration:
    def test_accepted_connection_is_registered_and_deregistered(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, player_id = _room_with_player(client)
        connections = app.state.room_connections

        assert connections.connections_for(room_code) == ()
        with client.websocket_connect(_ws(room_code, player_id)):
            assert len(connections.connections_for(room_code)) == 1
        assert connections.connections_for(room_code) == ()

    def test_rejected_connection_is_never_registered(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, _ = _room_with_player(client)

        try:
            with client.websocket_connect(_ws(room_code, "not-a-player")):
                pass
        except Exception:
            pass

        assert app.state.room_connections.connections_for(room_code) == ()

    def test_connected_player_receives_question_started_broadcast(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, player_id = _room_with_player(client)
        game = app.state.room_registry.get(room_code).game

        with client.websocket_connect(_ws(room_code, player_id)) as ws:
            asyncio.run(
                broadcast_question_started(
                    app.state.room_connections,
                    room_code,
                    _question(),
                    game.game_id,
                    STARTED_AT,
                )
            )
            message = ws.receive_json()

        assert message["event"] == "question.started"
        assert message["game_id"] == game.game_id
        assert message["payload"]["question_id"] == "q1"
        assert "correct_option_id" not in message["payload"]

    def test_two_players_both_receive_the_broadcast(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, dana = _room_with_player(client, "Dana")
        omer = client.post(
            f"/api/v1/rooms/{room_code}/players", json={"display_name": "Omer"}
        ).json()["player"]["player_id"]
        game = app.state.room_registry.get(room_code).game

        with client.websocket_connect(_ws(room_code, dana)) as ws_one:
            with client.websocket_connect(_ws(room_code, omer)) as ws_two:
                delivered = asyncio.run(
                    broadcast_question_started(
                        app.state.room_connections,
                        room_code,
                        _question(),
                        game.game_id,
                        STARTED_AT,
                    )
                )
                first = ws_one.receive_json()
                second = ws_two.receive_json()

        assert delivered == 2
        assert first["payload"]["question_id"] == "q1"
        assert second["payload"]["question_id"] == "q1"

    def test_broadcast_does_not_cross_rooms(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_a, player_a = _room_with_player(client, "Dana")
        room_b, player_b = _room_with_player(client, "Omer")
        game_a = app.state.room_registry.get(room_a).game

        with client.websocket_connect(_ws(room_a, player_a)) as ws_a:
            with client.websocket_connect(_ws(room_b, player_b)):
                delivered = asyncio.run(
                    broadcast_question_started(
                        app.state.room_connections,
                        room_a,
                        _question(),
                        game_a.game_id,
                        STARTED_AT,
                    )
                )
                assert delivered == 1
                assert ws_a.receive_json()["event"] == "question.started"
        assert app.state.room_connections.connections_for(room_b) == ()
