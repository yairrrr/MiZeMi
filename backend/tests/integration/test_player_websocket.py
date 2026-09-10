"""Integration tests for the player WebSocket connection (MASTER_SPEC.md §14.1).

Connect/disconnect lifecycle only: event handling, broadcasts, host
connections, and reconnect/simultaneous-connection policy are deferred and
deliberately untested here.
"""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.domain.game import Game, Player
from app.main import create_app


def _room_with_player(client: TestClient, display_name: str = "Dana") -> tuple[str, str]:
    room_code = client.post("/api/v1/rooms").json()["room_code"]
    player_id = client.post(
        f"/api/v1/rooms/{room_code}/players", json={"display_name": display_name}
    ).json()["player"]["player_id"]
    return room_code, player_id


def _ws_url(room_code: str, player_id: str) -> str:
    return f"/ws/rooms/{room_code}?player_id={player_id}"


class TestPlayerWebSocketLifecycle:
    def test_connected_flag_follows_the_websocket_lifecycle(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, player_id = _room_with_player(client)
        game: Game = app.state.room_registry.get(room_code).game
        player: Player = game.get_player(player_id)

        assert player.connected is False  # joined over REST, not yet connected

        with client.websocket_connect(_ws_url(room_code, player_id)):
            assert player.connected is True

        assert player.connected is False

    def test_lowercase_room_code_resolves_through_registry_normalization(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, player_id = _room_with_player(client)
        player = app.state.room_registry.get(room_code).game.get_player(player_id)

        with client.websocket_connect(_ws_url(room_code.lower(), player_id)):
            assert player.connected is True

        assert player.connected is False

    def test_unknown_room_is_rejected_without_envelope(self) -> None:
        client = TestClient(create_app())

        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(_ws_url("ZZZZZ2", "whoever")):
                pytest.fail("session must not be established")  # pragma: no cover

    def test_unknown_player_is_rejected_without_envelope_or_mutation(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, player_id = _room_with_player(client)
        game = app.state.room_registry.get(room_code).game

        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(_ws_url(room_code, "not-a-player")):
                pytest.fail("session must not be established")  # pragma: no cover

        assert len(game.players) == 1
        assert game.get_player(player_id).connected is False

    def test_connecting_one_player_does_not_affect_another(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, dana_id = _room_with_player(client, "Dana")
        omer_id = client.post(
            f"/api/v1/rooms/{room_code}/players", json={"display_name": "Omer"}
        ).json()["player"]["player_id"]
        game = app.state.room_registry.get(room_code).game

        with client.websocket_connect(_ws_url(room_code, dana_id)):
            assert game.get_player(dana_id).connected is True
            assert game.get_player(omer_id).connected is False

        assert game.get_player(dana_id).connected is False
        assert game.get_player(omer_id).connected is False

    def test_lifecycle_does_not_alter_other_player_fields(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, player_id = _room_with_player(client)
        player = app.state.room_registry.get(room_code).game.get_player(player_id)

        def snapshot() -> tuple:
            return (player.player_id, player.display_name, player.has_profile, player.is_ready)

        before = snapshot()
        with client.websocket_connect(_ws_url(room_code, player_id)):
            assert snapshot() == before
        assert snapshot() == before == (player_id, "Dana", False, False)
