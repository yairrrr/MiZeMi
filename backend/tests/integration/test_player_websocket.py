"""Integration tests for the player WebSocket connection (MASTER_SPEC.md §14.1).

Connection lifecycle and authentication: room/player/token resolution before
accept, the ``connected`` flag, Origin checks, and the approved
multi-connection policy (connected while at least one socket remains).
"""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.domain.game import Game, Player
from app.infrastructure.settings import Settings
from app.main import create_app
from tests.fixtures.live import (
    PLAYER_PROTOCOL,
    JoinedPlayer,
    create_room,
    join,
    player_ws,
    receive_until,
)


def _setup(client: TestClient, name: str = "Dana") -> tuple[str, JoinedPlayer]:
    room = create_room(client)
    return room.room_code, join(client, room.room_code, name)


def _raw_connect(client: TestClient, room_code: str, player_id: str, protocols=None, **kw):
    return client.websocket_connect(
        f"/ws/rooms/{room_code}?player_id={player_id}", subprotocols=protocols or [], **kw
    )


class TestPlayerWebSocketLifecycle:
    def test_connected_flag_follows_the_websocket_lifecycle(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, dana = _setup(client)
        game: Game = app.state.room_registry.get(room_code).game
        player: Player = game.get_player(dana.player_id)

        assert player.connected is False  # joined over REST, not yet connected

        with player_ws(client, room_code, dana) as ws:
            assert ws.accepted_subprotocol == PLAYER_PROTOCOL
            receive_until(ws, "room.updated")
            assert player.connected is True

        assert player.connected is False

    def test_connection_starts_with_a_room_snapshot(self) -> None:
        client = TestClient(create_app())
        room_code, dana = _setup(client)

        with player_ws(client, room_code, dana) as ws:
            first = ws.receive_json()

        assert first["event"] == "room.updated"
        assert first["payload"]["room_code"] == room_code
        assert first["payload"]["state"] == "LOBBY"
        assert [p["player_id"] for p in first["payload"]["players"]] == [dana.player_id]

    def test_lowercase_room_code_resolves_through_registry_normalization(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, dana = _setup(client)
        player = app.state.room_registry.get(room_code).game.get_player(dana.player_id)

        with player_ws(client, room_code.lower(), dana) as ws:
            receive_until(ws, "room.updated")
            assert player.connected is True

        assert player.connected is False

    def test_connecting_one_player_does_not_affect_another(self) -> None:
        app = create_app()
        client = TestClient(app)
        room = create_room(client)
        dana = join(client, room.room_code, "Dana")
        omer = join(client, room.room_code, "Omer")
        game = app.state.room_registry.get(room.room_code).game

        with player_ws(client, room.room_code, dana) as ws:
            receive_until(ws, "room.updated")
            assert game.get_player(dana.player_id).connected is True
            assert game.get_player(omer.player_id).connected is False

        assert game.get_player(dana.player_id).connected is False

    def test_lifecycle_does_not_alter_other_player_fields(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, dana = _setup(client)
        player = app.state.room_registry.get(room_code).game.get_player(dana.player_id)

        def snapshot() -> tuple:
            return (player.player_id, player.display_name, player.has_profile, player.is_ready)

        before = snapshot()
        with player_ws(client, room_code, dana) as ws:
            receive_until(ws, "room.updated")
            assert snapshot() == before
        assert snapshot() == before == (dana.player_id, "Dana", False, False)


class TestMultipleConnections:
    def test_player_stays_connected_until_the_last_socket_closes(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, dana = _setup(client)
        player = app.state.room_registry.get(room_code).game.get_player(dana.player_id)

        with player_ws(client, room_code, dana) as first:
            receive_until(first, "room.updated")
            with player_ws(client, room_code, dana) as second:
                receive_until(second, "room.updated")
                assert app.state.room_connections.player_connection_count(
                    room_code, dana.player_id
                ) == 2
            # One of two sockets closed: still connected (§14.1 policy).
            assert player.connected is True
            assert app.state.room_connections.player_connection_count(
                room_code, dana.player_id
            ) == 1

        assert player.connected is False
        assert app.state.room_connections.connections_for(room_code) == ()


class TestConnectionRejection:
    def test_unknown_room_is_rejected_without_envelope(self) -> None:
        client = TestClient(create_app())

        with pytest.raises(WebSocketDisconnect):
            with _raw_connect(client, "ZZZZZ2", "whoever", [PLAYER_PROTOCOL, "x"]):
                pytest.fail("session must not be established")  # pragma: no cover

    def test_unknown_player_is_rejected_without_envelope_or_mutation(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, dana = _setup(client)
        game = app.state.room_registry.get(room_code).game

        with pytest.raises(WebSocketDisconnect):
            with _raw_connect(client, room_code, "not-a-player", [PLAYER_PROTOCOL, dana.player_token]):
                pytest.fail("session must not be established")  # pragma: no cover

        assert len(game.players) == 1
        assert game.get_player(dana.player_id).connected is False

    @pytest.mark.parametrize(
        "protocols",
        [
            [],                              # no credential at all
            [PLAYER_PROTOCOL],               # role without token
            [PLAYER_PROTOCOL, "wrong-token"],
            ["mizemi.host", "wrong-token"],  # wrong role
        ],
    )
    def test_missing_or_wrong_token_is_rejected(self, protocols: list[str]) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, dana = _setup(client)

        with pytest.raises(WebSocketDisconnect):
            with _raw_connect(client, room_code, dana.player_id, protocols):
                pytest.fail("session must not be established")  # pragma: no cover

        assert app.state.room_registry.get(room_code).game.get_player(dana.player_id).connected is False

    def test_another_players_token_cannot_impersonate(self) -> None:
        client = TestClient(create_app())
        room = create_room(client)
        dana = join(client, room.room_code, "Dana")
        omer = join(client, room.room_code, "Omer")

        with pytest.raises(WebSocketDisconnect):
            with _raw_connect(client, room.room_code, dana.player_id, [PLAYER_PROTOCOL, omer.player_token]):
                pytest.fail("session must not be established")  # pragma: no cover

    def test_disallowed_origin_is_rejected(self) -> None:
        app = create_app(Settings(_env_file=None, cors_origins=["https://mizemi.example"]))
        client = TestClient(app)
        room_code, dana = _setup(client)

        with pytest.raises(WebSocketDisconnect):
            with player_ws(client, room_code, dana, headers={"origin": "https://evil.example"}):
                pytest.fail("session must not be established")  # pragma: no cover

    def test_allowed_origin_is_accepted(self) -> None:
        app = create_app(Settings(_env_file=None, cors_origins=["https://mizemi.example"]))
        client = TestClient(app)
        room_code, dana = _setup(client)

        with player_ws(client, room_code, dana, headers={"origin": "https://mizemi.example"}) as ws:
            assert ws.receive_json()["event"] == "room.updated"
