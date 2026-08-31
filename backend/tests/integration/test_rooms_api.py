"""Integration tests for POST /api/v1/rooms (MASTER_SPEC.md §13)."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def _client_and_app():
    app = create_app()
    return TestClient(app), app


class TestCreateRoomEndpoint:
    def test_create_room_returns_201_with_exact_contract_keys(self) -> None:
        client, _ = _client_and_app()

        response = client.post("/api/v1/rooms")

        assert response.status_code == 201
        body = response.json()
        assert set(body.keys()) == {"room_code", "game_id"}
        assert isinstance(body["room_code"], str) and body["room_code"]
        assert isinstance(body["game_id"], str) and body["game_id"]

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
