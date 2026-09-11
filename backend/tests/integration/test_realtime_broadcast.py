"""Integration tests for live connection registration and broadcast delivery.

Covers the wiring between the WebSocket endpoints and the room connection
registry (MASTER_SPEC.md §14): accepted connections receive room events and
deregister on disconnect; rejected ones never register.
"""

import asyncio
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import create_app
from app.realtime.game_events import broadcast_question_started
from tests.fixtures.factories import make_question
from tests.fixtures.live import create_room, host_ws, join, player_ws, receive_until

STARTED_AT = datetime(2026, 9, 5, 10, 15, 30, tzinfo=UTC)


class TestConnectionRegistration:
    def test_accepted_connection_is_registered_and_deregistered(self) -> None:
        app = create_app()
        client = TestClient(app)
        room = create_room(client)
        dana = join(client, room.room_code, "Dana")
        connections = app.state.room_connections

        assert connections.connections_for(room.room_code) == ()
        with player_ws(client, room.room_code, dana) as ws:
            receive_until(ws, "room.updated")
            assert len(connections.connections_for(room.room_code)) == 1
        assert connections.connections_for(room.room_code) == ()

    def test_host_connection_is_registered_with_the_host_role(self) -> None:
        app = create_app()
        client = TestClient(app)
        room = create_room(client)

        with host_ws(client, room) as ws:
            receive_until(ws, "room.updated")
            handles = app.state.room_connections.handles_for(room.room_code)
            assert [h.role for h in handles] == ["host"]

    def test_rejected_connection_is_never_registered(self) -> None:
        app = create_app()
        client = TestClient(app)
        room = create_room(client)

        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                f"/ws/rooms/{room.room_code}?player_id=not-a-player",
                subprotocols=["mizemi.player", "token"],
            ):
                pytest.fail("session must not be established")  # pragma: no cover

        assert app.state.room_connections.connections_for(room.room_code) == ()

    def test_connected_player_receives_question_started_broadcast(self) -> None:
        app = create_app()
        client = TestClient(app)
        room = create_room(client)
        dana = join(client, room.room_code, "Dana")

        with player_ws(client, room.room_code, dana) as ws:
            receive_until(ws, "room.updated")
            asyncio.run(
                broadcast_question_started(
                    app.state.room_connections, room.room_code, make_question(), room.game_id, STARTED_AT
                )
            )
            message = receive_until(ws, "question.started")

        assert message["game_id"] == room.game_id
        assert message["payload"]["question_id"] == "q1"
        assert "correct_option_id" not in message["payload"]

    def test_two_players_both_receive_the_broadcast(self) -> None:
        app = create_app()
        client = TestClient(app)
        room = create_room(client)
        dana = join(client, room.room_code, "Dana")
        omer = join(client, room.room_code, "Omer")

        with player_ws(client, room.room_code, dana) as ws_one:
            with player_ws(client, room.room_code, omer) as ws_two:
                delivered = asyncio.run(
                    broadcast_question_started(
                        app.state.room_connections, room.room_code, make_question(), room.game_id, STARTED_AT
                    )
                )
                first = receive_until(ws_one, "question.started")
                second = receive_until(ws_two, "question.started")

        assert delivered == 2
        assert first["payload"]["question_id"] == second["payload"]["question_id"] == "q1"

    def test_broadcast_does_not_cross_rooms(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_a = create_room(client)
        room_b = create_room(client)
        dana = join(client, room_a.room_code, "Dana")
        omer = join(client, room_b.room_code, "Omer")

        with player_ws(client, room_a.room_code, dana) as ws_a:
            with player_ws(client, room_b.room_code, omer):
                delivered = asyncio.run(
                    broadcast_question_started(
                        app.state.room_connections, room_a.room_code, make_question(), room_a.game_id, STARTED_AT
                    )
                )
                assert delivered == 1
                assert receive_until(ws_a, "question.started")["event"] == "question.started"
        assert app.state.room_connections.connections_for(room_b.room_code) == ()
