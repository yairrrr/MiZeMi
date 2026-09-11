"""Integration tests for the room REST endpoints (MASTER_SPEC.md §13, §17)."""

import pytest
from fastapi.testclient import TestClient

from app.domain.game import GameState
from app.infrastructure.settings import Settings
from app.main import create_app
from tests.fixtures.live import create_room, host_ws, receive_until


def _client_and_app(settings: Settings | None = None):
    app = create_app(settings)
    return TestClient(app), app


PLAYER_WIRE_KEYS = {
    "player_id",
    "display_name",
    "is_host",
    "connected",
    "has_profile",
    "is_ready",
    "score",
}


def _join(client: TestClient, room_code: str, display_name: str):
    return client.post(
        f"/api/v1/rooms/{room_code}/players", json={"display_name": display_name}
    )


class TestCreateRoomEndpoint:
    def test_create_room_returns_201_with_exact_contract_keys(self) -> None:
        client, _ = _client_and_app()

        response = client.post("/api/v1/rooms")

        assert response.status_code == 201
        body = response.json()
        assert set(body.keys()) == {"room_code", "game_id", "host_token", "config"}
        assert isinstance(body["room_code"], str) and body["room_code"]
        assert isinstance(body["game_id"], str) and body["game_id"]
        assert len(body["host_token"]) >= 40

    def test_host_token_is_verifiable_and_only_a_digest_is_stored(self) -> None:
        client, app = _client_and_app()

        body = client.post("/api/v1/rooms").json()

        credentials = app.state.credentials
        assert credentials.verify_host(body["room_code"], body["host_token"]) is True
        assert body["host_token"] not in repr(vars(credentials))

    def test_each_room_gets_a_different_host_token(self) -> None:
        client, _ = _client_and_app()

        first = client.post("/api/v1/rooms").json()
        second = client.post("/api/v1/rooms").json()

        assert first["host_token"] != second["host_token"]

    def test_created_room_is_registered_in_the_application_registry(self) -> None:
        client, app = _client_and_app()

        body = client.post("/api/v1/rooms").json()

        room = app.state.room_registry.get(body["room_code"])
        assert room.game.game_id == body["game_id"]

    def test_repeated_creates_register_independent_rooms(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client, app = _client_and_app()
        codes = iter(["ABC234", "DEF567"])
        monkeypatch.setattr(
            "app.application.create_room.generate_room_code", lambda: next(codes)
        )

        first = client.post("/api/v1/rooms").json()
        second = client.post("/api/v1/rooms").json()

        assert first["room_code"] == "ABC234"
        assert second["room_code"] == "DEF567"
        room_one = app.state.room_registry.get("ABC234")
        room_two = app.state.room_registry.get("DEF567")
        assert room_one is not room_two
        assert room_one.game.game_id == first["game_id"]
        assert room_two.game.game_id == second["game_id"]


class TestJoinRoomEndpoint:
    def _room(self, client: TestClient) -> str:
        return client.post("/api/v1/rooms").json()["room_code"]

    def test_join_returns_201_with_exact_response_and_player_keys(self) -> None:
        client, _ = _client_and_app()
        room_code = self._room(client)

        response = _join(client, room_code, "Dana")

        assert response.status_code == 201
        body = response.json()
        assert set(body.keys()) == {"game_id", "player", "player_token"}
        assert set(body["player"].keys()) == PLAYER_WIRE_KEYS
        assert body["player"]["display_name"] == "Dana"
        assert body["player"]["is_host"] is False
        assert body["player"]["score"] == 0
        assert len(body["player_token"]) >= 40

    def test_player_token_verifies_only_for_that_player(self) -> None:
        client, app = _client_and_app()
        room_code = self._room(client)

        dana = _join(client, room_code, "Dana").json()
        omer = _join(client, room_code, "Omer").json()

        credentials = app.state.credentials
        dana_id, omer_id = dana["player"]["player_id"], omer["player"]["player_id"]
        assert credentials.verify_player(room_code, dana_id, dana["player_token"])
        assert not credentials.verify_player(room_code, dana_id, omer["player_token"])
        assert not credentials.verify_player(room_code, omer_id, dana["player_token"])

    def test_join_returns_the_authoritative_room_game_id(self) -> None:
        client, app = _client_and_app()
        room_code = self._room(client)

        body = _join(client, room_code, "Dana").json()

        room = app.state.room_registry.get(room_code)
        assert body["game_id"] == room.game.game_id

    def test_returned_player_id_finds_the_player_in_the_game(self) -> None:
        client, app = _client_and_app()
        room_code = self._room(client)

        body = _join(client, room_code, "Dana").json()

        game = app.state.room_registry.get(room_code).game
        player = game.get_player(body["player"]["player_id"])
        assert player is not None
        assert player.display_name == "Dana"

    def test_display_name_is_returned_trimmed(self) -> None:
        client, _ = _client_and_app()
        room_code = self._room(client)

        body = _join(client, room_code, "  Dana  ").json()

        assert body["player"]["display_name"] == "Dana"

    def test_lowercase_room_code_joins(self) -> None:
        client, _ = _client_and_app()
        room_code = self._room(client)

        assert _join(client, room_code.lower(), "Dana").status_code == 201

    def test_unknown_room_maps_to_room_not_found(self) -> None:
        client, _ = _client_and_app()

        response = _join(client, "ZZZZZ2", "Dana")

        assert response.status_code == 404
        body = response.json()
        assert set(body.keys()) == {"error"}
        assert body["error"]["code"] == "ROOM_NOT_FOUND"
        assert isinstance(body["error"]["message"], str)

    def test_duplicate_name_maps_to_name_taken(self) -> None:
        client, _ = _client_and_app()
        room_code = self._room(client)
        _join(client, room_code, "Dana")

        response = _join(client, room_code, "Dana")

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "NAME_TAKEN"

    def test_case_insensitive_duplicate_maps_to_name_taken(self) -> None:
        client, _ = _client_and_app()
        room_code = self._room(client)
        _join(client, room_code, "Dana")

        response = _join(client, room_code, "dANA")

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "NAME_TAKEN"

    def test_invalid_display_name_maps_to_validation_error(self) -> None:
        client, _ = _client_and_app()
        room_code = self._room(client)

        for bad_name in ("   ", "A" * 21):
            response = _join(client, room_code, bad_name)

            assert response.status_code == 400
            assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_full_room_maps_to_room_full(self) -> None:
        client, app = _client_and_app(Settings(_env_file=None, max_players_per_room=2))
        room_code = self._room(client)
        _join(client, room_code, "Dana")
        _join(client, room_code, "Omer")

        response = _join(client, room_code, "Noa")

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "ROOM_FULL"
        assert len(app.state.room_registry.get(room_code).game.players) == 2

    def test_join_still_accepted_in_profile_collection(self) -> None:
        client, app = _client_and_app()
        room_code = self._room(client)
        _join(client, room_code, "Dana")
        game = app.state.room_registry.get(room_code).game
        game.transition_to(GameState.PROFILE_COLLECTION)

        response = _join(client, room_code, "Omer")

        assert response.status_code == 201

    def test_non_joinable_state_maps_to_room_not_joinable(self) -> None:
        client, app = _client_and_app()
        room_code = self._room(client)
        _join(client, room_code, "Dana")
        game = app.state.room_registry.get(room_code).game
        game.transition_to(GameState.PROFILE_COLLECTION)
        game.transition_to(GameState.READY)
        game.transition_to(GameState.QUESTION_ACTIVE)

        response = _join(client, room_code, "Omer")

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "ROOM_NOT_JOINABLE"
        assert len(game.players) == 1

    def test_failed_requests_do_not_add_players(self) -> None:
        client, app = _client_and_app()
        room_code = self._room(client)
        _join(client, room_code, "Dana")
        game = app.state.room_registry.get(room_code).game

        _join(client, room_code, "dana")       # NAME_TAKEN
        _join(client, room_code, "   ")        # VALIDATION_ERROR
        _join(client, "ZZZZZ2", "Omer")        # ROOM_NOT_FOUND

        assert len(game.players) == 1

    def test_join_is_broadcast_to_the_connected_host(self) -> None:
        client, _ = _client_and_app()
        room = create_room(client)

        with host_ws(client, room) as ws:
            receive_until(ws, "room.updated")  # snapshot on connect
            _join(client, room.room_code, "Dana")
            snapshot = receive_until(ws, "room.updated")

        assert [p["display_name"] for p in snapshot["payload"]["players"]] == ["Dana"]


class TestMalformedRequests:
    @pytest.mark.parametrize(
        "body",
        [
            {},
            {"display_name": "Dana", "extra": 1},
            {"display_name": 42},
            {"display_name": "x" * 101},
        ],
    )
    def test_invalid_join_body_uses_the_standard_error_shape(self, body: dict) -> None:
        client, _ = _client_and_app()
        room_code = client.post("/api/v1/rooms").json()["room_code"]

        response = client.post(f"/api/v1/rooms/{room_code}/players", json=body)

        assert response.status_code == 422
        assert response.json() == {
            "error": {"code": "VALIDATION_ERROR", "message": "The request is not valid."}
        }

    def test_non_json_body_uses_the_standard_error_shape(self) -> None:
        client, _ = _client_and_app()
        room_code = client.post("/api/v1/rooms").json()["room_code"]

        response = client.post(
            f"/api/v1/rooms/{room_code}/players",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"


class TestCors:
    def test_allowed_origin_receives_cors_headers(self) -> None:
        client, _ = _client_and_app(
            Settings(_env_file=None, cors_origins=["https://mizemi.example"])
        )

        response = client.options(
            "/api/v1/rooms",
            headers={
                "Origin": "https://mizemi.example",
                "Access-Control-Request-Method": "POST",
            },
        )

        assert response.headers["access-control-allow-origin"] == "https://mizemi.example"
        assert "access-control-allow-credentials" not in response.headers

    def test_other_origins_are_not_allowed(self) -> None:
        client, _ = _client_and_app(
            Settings(_env_file=None, cors_origins=["https://mizemi.example"])
        )

        response = client.options(
            "/api/v1/rooms",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
            },
        )

        assert "access-control-allow-origin" not in response.headers
