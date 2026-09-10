"""Integration tests for player.profile_submit / player.ready over WebSocket.

Success has no acknowledgement (room.updated is deferred), so success tests
assert the authoritative in-memory domain state after the socket closes —
the endpoint processes frames sequentially, so post-context assertions are
deterministic. Error tests block on receive_json for the error envelope.
"""

from fastapi.testclient import TestClient

from app.domain.game import Game, GameState
from app.main import create_app

TIMESTAMP = "2026-08-31T10:00:00.000Z"

ENVELOPE_KEYS = {"event", "payload", "timestamp", "game_id"}


def _setup(client: TestClient, names: list[str]) -> tuple[str, str, dict[str, str]]:
    """Create a room and join the given players. Returns (room_code, game_id, ids)."""
    created = client.post("/api/v1/rooms").json()
    ids = {
        name: client.post(
            f"/api/v1/rooms/{created['room_code']}/players", json={"display_name": name}
        ).json()["player"]["player_id"]
        for name in names
    }
    return created["room_code"], created["game_id"], ids


def _envelope(event: str, payload: dict, game_id: str) -> dict:
    return {"event": event, "payload": payload, "timestamp": TIMESTAMP, "game_id": game_id}


def _profile_payload(player_id: str) -> dict:
    return {
        "player_id": player_id,
        "fields": [
            {"field_key": "favorite_food", "value": "pizza", "allow_question_usage": True},
            {"field_key": "age", "value": 27, "allow_question_usage": True},
            {"field_key": "personal_fact", "value": "afraid of pigeons", "allow_question_usage": False},
        ],
    }


def _ws(room_code: str, player_id: str) -> str:
    return f"/ws/rooms/{room_code}?player_id={player_id}"


class TestProfileSubmitOverWebSocket:
    def test_profile_submit_assigns_profile_and_transitions_to_profile_collection(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _setup(client, ["Dana"])
        game: Game = app.state.room_registry.get(room_code).game
        assert game.state is GameState.LOBBY

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json(
                _envelope("player.profile_submit", _profile_payload(ids["Dana"]), game_id)
            )

        player = game.get_player(ids["Dana"])
        assert player.has_profile is True
        assert game.state is GameState.PROFILE_COLLECTION

    def test_profile_fields_preserve_key_value_consent_and_order(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _setup(client, ["Dana"])
        game = app.state.room_registry.get(room_code).game

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json(
                _envelope("player.profile_submit", _profile_payload(ids["Dana"]), game_id)
            )

        fields = game.get_player(ids["Dana"]).profile.fields
        assert [f.field_key for f in fields] == ["favorite_food", "age", "personal_fact"]
        assert fields[0].value == "pizza" and isinstance(fields[0].value, str)
        assert fields[1].value == 27 and isinstance(fields[1].value, int)
        assert [f.allow_question_usage for f in fields] == [True, True, False]

    def test_profile_lands_on_connected_player_only(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _setup(client, ["Dana", "Omer"])
        game = app.state.room_registry.get(room_code).game

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json(
                _envelope("player.profile_submit", _profile_payload(ids["Dana"]), game_id)
            )

        assert game.get_player(ids["Dana"]).has_profile is True
        assert game.get_player(ids["Omer"]).has_profile is False

    def test_payload_for_another_player_is_rejected(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _setup(client, ["Dana", "Omer"])
        game = app.state.room_registry.get(room_code).game

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json(
                _envelope("player.profile_submit", _profile_payload(ids["Omer"]), game_id)
            )
            reply = ws.receive_json()

        assert reply["event"] == "error"
        assert reply["payload"]["error"]["code"] == "VALIDATION_ERROR"
        assert game.get_player(ids["Dana"]).has_profile is False
        assert game.get_player(ids["Omer"]).has_profile is False
        assert game.state is GameState.LOBBY

    def test_invalid_profile_payload_rejected_without_mutation(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _setup(client, ["Dana"])
        game = app.state.room_registry.get(room_code).game
        bad_payload = {
            "player_id": ids["Dana"],
            "fields": [{"field_key": "age", "value": 27}],  # missing consent flag
        }

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json(_envelope("player.profile_submit", bad_payload, game_id))
            reply = ws.receive_json()

        assert set(reply.keys()) == ENVELOPE_KEYS
        assert reply["event"] == "error"
        assert reply["game_id"] == game_id
        assert reply["payload"]["error"]["code"] == "VALIDATION_ERROR"
        assert game.get_player(ids["Dana"]).has_profile is False
        assert game.state is GameState.LOBBY

    def test_second_initial_submission_follows_existing_domain_rejection(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _setup(client, ["Dana"])
        game = app.state.room_registry.get(room_code).game

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json(
                _envelope("player.profile_submit", _profile_payload(ids["Dana"]), game_id)
            )
            ws.send_json(
                _envelope("player.profile_submit", _profile_payload(ids["Dana"]), game_id)
            )
            reply = ws.receive_json()

        assert reply["payload"]["error"]["code"] == "VALIDATION_ERROR"
        # Stable public message only — the internal ValueError text never leaks.
        assert reply["payload"]["error"]["message"] == "The profile submission was rejected."
        assert "already has a profile" not in reply["payload"]["error"]["message"]
        fields = game.get_player(ids["Dana"]).profile.fields
        assert [f.field_key for f in fields] == ["favorite_food", "age", "personal_fact"]
        assert game.state is GameState.PROFILE_COLLECTION


class TestPlayerReadyOverWebSocket:
    def test_profile_then_ready_marks_player_ready(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _setup(client, ["Dana", "Omer"])
        game = app.state.room_registry.get(room_code).game

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json(
                _envelope("player.profile_submit", _profile_payload(ids["Dana"]), game_id)
            )
            ws.send_json(_envelope("player.ready", {}, game_id))

        assert game.get_player(ids["Dana"]).is_ready is True
        assert game.state is GameState.PROFILE_COLLECTION  # Omer not ready

    def test_ready_without_profile_rejected_without_mutation(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _setup(client, ["Dana", "Omer"])
        game = app.state.room_registry.get(room_code).game

        # Dana's profile moves the game to PROFILE_COLLECTION first.
        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json(
                _envelope("player.profile_submit", _profile_payload(ids["Dana"]), game_id)
            )
        with client.websocket_connect(_ws(room_code, ids["Omer"])) as ws:
            ws.send_json(_envelope("player.ready", {}, game_id))
            reply = ws.receive_json()

        assert reply["payload"]["error"]["code"] == "VALIDATION_ERROR"
        # Stable public message only — the internal ValueError text never leaks.
        assert reply["payload"]["error"]["message"] == "The ready request was rejected."
        assert "has no profile" not in reply["payload"]["error"]["message"]
        assert game.get_player(ids["Omer"]).is_ready is False

    def test_ready_in_lobby_rejected_by_domain_state_rule(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _setup(client, ["Dana"])
        game = app.state.room_registry.get(room_code).game

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json(_envelope("player.ready", {}, game_id))
            reply = ws.receive_json()

        assert reply["payload"]["error"]["code"] == "VALIDATION_ERROR"
        assert game.get_player(ids["Dana"]).is_ready is False
        assert game.state is GameState.LOBBY

    def test_ready_with_non_empty_payload_rejected_without_mutation(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _setup(client, ["Dana"])
        game = app.state.room_registry.get(room_code).game

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json(
                _envelope("player.profile_submit", _profile_payload(ids["Dana"]), game_id)
            )
            ws.send_json(
                _envelope("player.ready", {"player_id": ids["Dana"]}, game_id)
            )
            reply = ws.receive_json()

        assert reply["payload"]["error"]["code"] == "VALIDATION_ERROR"
        assert game.get_player(ids["Dana"]).is_ready is False
        assert game.state is GameState.PROFILE_COLLECTION

    def test_ready_is_idempotent(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _setup(client, ["Dana", "Omer"])
        game = app.state.room_registry.get(room_code).game

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json(
                _envelope("player.profile_submit", _profile_payload(ids["Dana"]), game_id)
            )
            ws.send_json(_envelope("player.ready", {}, game_id))
            ws.send_json(_envelope("player.ready", {}, game_id))
            # Sync trick: a malformed frame forces exactly one reply; if either
            # ready had errored, the first received reply would differ.
            ws.send_json({"nope": True})
            reply = ws.receive_json()

        assert reply["payload"]["error"]["message"] == "The message is not a valid realtime envelope."
        assert game.get_player(ids["Dana"]).is_ready is True
        assert game.state is GameState.PROFILE_COLLECTION

    def test_all_players_ready_transitions_to_ready_even_disconnected(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _setup(client, ["Dana", "Omer"])
        game = app.state.room_registry.get(room_code).game

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json(
                _envelope("player.profile_submit", _profile_payload(ids["Dana"]), game_id)
            )
            ws.send_json(_envelope("player.ready", {}, game_id))
        # Dana is now disconnected but ready — still counts toward all-ready.
        assert game.get_player(ids["Dana"]).connected is False
        assert game.state is GameState.PROFILE_COLLECTION

        with client.websocket_connect(_ws(room_code, ids["Omer"])) as ws:
            ws.send_json(
                _envelope("player.profile_submit", _profile_payload(ids["Omer"]), game_id)
            )
            ws.send_json(_envelope("player.ready", {}, game_id))

        assert game.state is GameState.READY

    def test_disconnected_unready_player_blocks_ready_transition(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _setup(client, ["Dana", "Omer"])
        game = app.state.room_registry.get(room_code).game

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json(
                _envelope("player.profile_submit", _profile_payload(ids["Dana"]), game_id)
            )
        with client.websocket_connect(_ws(room_code, ids["Omer"])) as ws:
            ws.send_json(
                _envelope("player.profile_submit", _profile_payload(ids["Omer"]), game_id)
            )
            ws.send_json(_envelope("player.ready", {}, game_id))

        # Dana is disconnected and not ready: still in the denominator.
        assert game.state is GameState.PROFILE_COLLECTION


class TestRealtimeContractOverWebSocket:
    def _connected(self, app, client, room_code: str, player_id: str):
        return client.websocket_connect(_ws(room_code, player_id))

    def test_malformed_envelope_gets_validation_error_envelope(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _setup(client, ["Dana"])

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json({"event": "player.ready", "payload": {}})  # missing keys
            reply = ws.receive_json()

        assert set(reply.keys()) == ENVELOPE_KEYS
        assert reply["event"] == "error"
        assert reply["game_id"] == game_id
        assert reply["payload"]["error"]["code"] == "VALIDATION_ERROR"

    def test_non_json_text_gets_validation_error_envelope(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _setup(client, ["Dana"])

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_text("this is not json")
            reply = ws.receive_json()

        assert reply["payload"]["error"]["code"] == "VALIDATION_ERROR"

    def test_unknown_event_gets_unknown_event_envelope(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _setup(client, ["Dana"])

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json(_envelope("player.dance", {}, game_id))
            reply = ws.receive_json()

        assert reply["event"] == "error"
        assert reply["payload"]["error"]["code"] == "UNKNOWN_EVENT"

    def test_mismatched_game_id_is_rejected_without_mutation(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, ids = _setup(client, ["Dana"])
        game = app.state.room_registry.get(room_code).game

        with client.websocket_connect(_ws(room_code, ids["Dana"])) as ws:
            ws.send_json(
                _envelope(
                    "player.profile_submit", _profile_payload(ids["Dana"]), "another-game"
                )
            )
            reply = ws.receive_json()
            assert reply["payload"]["error"]["code"] == "VALIDATION_ERROR"
            assert reply["game_id"] == game_id  # the error names the real game
            assert game.get_player(ids["Dana"]).has_profile is False
            assert game.state is GameState.LOBBY
            # The socket stays open and usable after the rejection:
            ws.send_json(
                _envelope("player.profile_submit", _profile_payload(ids["Dana"]), game_id)
            )

        assert game.get_player(ids["Dana"]).has_profile is True
        assert game.state is GameState.PROFILE_COLLECTION
