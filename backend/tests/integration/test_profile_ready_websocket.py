"""Integration tests for player.profile_submit / player.ready over WebSocket.

Success has no acknowledgement beyond the room snapshot, so success tests
assert the authoritative in-memory domain state after the socket closes —
the endpoint processes frames in order, so post-context assertions are
deterministic. Error tests read until the ``error`` envelope arrives.
"""

from fastapi.testclient import TestClient

from app.application.profile_rules import PRIVACY_MESSAGE
from app.domain.game import Game, GameState
from app.main import create_app
from tests.fixtures.live import (
    JoinedPlayer,
    collect_until,
    create_room,
    envelope,
    join,
    player_ws,
    profile_fields,
    profile_payload,
    receive_until,
)

ENVELOPE_KEYS = {"event", "payload", "timestamp", "game_id"}


def _setup(client: TestClient, names: list[str]) -> tuple[str, str, dict[str, JoinedPlayer]]:
    room = create_room(client)
    players = {name: join(client, room.room_code, name) for name in names}
    return room.room_code, room.game_id, players


def _submit(ws, game_id: str, player: JoinedPlayer, **values) -> None:
    ws.send_json(envelope("player.profile_submit", profile_payload(player.player_id, **values), game_id))


def _error(ws) -> dict:
    return receive_until(ws, "error")


class TestProfileSubmitOverWebSocket:
    def test_profile_submit_assigns_profile_and_transitions_to_profile_collection(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, players = _setup(client, ["Dana"])
        game: Game = app.state.room_registry.get(room_code).game
        assert game.state is GameState.LOBBY

        with player_ws(client, room_code, players["Dana"]) as ws:
            _submit(ws, game_id, players["Dana"])
            snapshot = receive_until(ws, "room.updated")
            while snapshot["payload"]["state"] != "PROFILE_COLLECTION":
                snapshot = receive_until(ws, "room.updated")

        assert game.get_player(players["Dana"].player_id).has_profile is True
        assert game.state is GameState.PROFILE_COLLECTION
        assert snapshot["payload"]["players"][0]["has_profile"] is True

    def test_fields_are_stored_in_canonical_order_with_consent(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, players = _setup(client, ["Dana"])
        game = app.state.room_registry.get(room_code).game
        fields = list(reversed(profile_fields(age=27)))
        fields.append({"field_key": "personal_fact", "value": "I juggle", "allow_question_usage": False})

        with player_ws(client, room_code, players["Dana"]) as ws:
            ws.send_json(
                envelope(
                    "player.profile_submit",
                    {"player_id": players["Dana"].player_id, "fields": fields},
                    game_id,
                )
            )

        stored = game.get_player(players["Dana"].player_id).profile.fields
        assert [f.field_key for f in stored] == [
            "city",
            "favorite_food",
            "hobby",
            "favorite_music",
            "age",
            "personal_fact",
        ]
        assert stored[4].value == 27 and isinstance(stored[4].value, int)
        assert [f.allow_question_usage for f in stored] == [True, True, True, True, True, False]

    def test_profile_lands_on_connected_player_only(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, players = _setup(client, ["Dana", "Omer"])
        game = app.state.room_registry.get(room_code).game

        with player_ws(client, room_code, players["Dana"]) as ws:
            _submit(ws, game_id, players["Dana"])

        assert game.get_player(players["Dana"].player_id).has_profile is True
        assert game.get_player(players["Omer"].player_id).has_profile is False

    def test_payload_for_another_player_is_rejected(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, players = _setup(client, ["Dana", "Omer"])
        game = app.state.room_registry.get(room_code).game

        with player_ws(client, room_code, players["Dana"]) as ws:
            _submit(ws, game_id, players["Omer"])  # names Omer, sent on Dana's socket
            reply = _error(ws)

        assert reply["payload"]["error"]["code"] == "VALIDATION_ERROR"
        assert game.get_player(players["Dana"].player_id).has_profile is False
        assert game.get_player(players["Omer"].player_id).has_profile is False
        assert game.state is GameState.LOBBY

    def test_invalid_profile_shape_rejected_without_mutation(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, players = _setup(client, ["Dana"])
        game = app.state.room_registry.get(room_code).game
        bad = {"player_id": players["Dana"].player_id, "fields": [{"field_key": "city", "value": "Haifa"}]}

        with player_ws(client, room_code, players["Dana"]) as ws:
            ws.send_json(envelope("player.profile_submit", bad, game_id))
            reply = _error(ws)

        assert set(reply.keys()) == ENVELOPE_KEYS
        assert reply["game_id"] == game_id
        assert reply["payload"]["error"]["code"] == "VALIDATION_ERROR"
        assert game.get_player(players["Dana"].player_id).has_profile is False
        assert game.state is GameState.LOBBY

    def test_missing_required_field_is_rejected_with_a_clear_message(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, players = _setup(client, ["Dana"])
        game = app.state.room_registry.get(room_code).game
        fields = [f for f in profile_fields() if f["field_key"] != "city"]

        with player_ws(client, room_code, players["Dana"]) as ws:
            ws.send_json(
                envelope("player.profile_submit", {"player_id": players["Dana"].player_id, "fields": fields}, game_id)
            )
            reply = _error(ws)

        assert reply["payload"]["error"]["message"] == "City is required."
        assert game.get_player(players["Dana"].player_id).has_profile is False

    def test_sensitive_looking_text_is_rejected(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, players = _setup(client, ["Dana"])
        game = app.state.room_registry.get(room_code).game

        with player_ws(client, room_code, players["Dana"]) as ws:
            _submit(ws, game_id, players["Dana"], personal_fact="write me at dana@example.com")
            reply = _error(ws)

        assert reply["payload"]["error"]["message"] == PRIVACY_MESSAGE
        assert "dana@example.com" not in str(reply)
        assert game.get_player(players["Dana"].player_id).has_profile is False

    def test_second_initial_submission_follows_existing_domain_rejection(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, players = _setup(client, ["Dana"])
        game = app.state.room_registry.get(room_code).game

        with player_ws(client, room_code, players["Dana"]) as ws:
            _submit(ws, game_id, players["Dana"])
            _submit(ws, game_id, players["Dana"], city="Eilat")
            reply = _error(ws)

        assert reply["payload"]["error"]["message"] == "The profile submission was rejected."
        assert "already has a profile" not in reply["payload"]["error"]["message"]
        city = game.get_player(players["Dana"].player_id).profile.fields[0]
        assert city.value == "Haifa"
        assert game.state is GameState.PROFILE_COLLECTION


class TestPlayerReadyOverWebSocket:
    def test_profile_then_ready_marks_player_ready(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, players = _setup(client, ["Dana", "Omer"])
        game = app.state.room_registry.get(room_code).game

        with player_ws(client, room_code, players["Dana"]) as ws:
            _submit(ws, game_id, players["Dana"])
            ws.send_json(envelope("player.ready", {}, game_id))

        assert game.get_player(players["Dana"].player_id).is_ready is True
        assert game.state is GameState.PROFILE_COLLECTION  # Omer not ready

    def test_ready_without_profile_rejected_without_mutation(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, players = _setup(client, ["Dana", "Omer"])
        game = app.state.room_registry.get(room_code).game

        with player_ws(client, room_code, players["Dana"]) as ws:
            _submit(ws, game_id, players["Dana"])
        with player_ws(client, room_code, players["Omer"]) as ws:
            ws.send_json(envelope("player.ready", {}, game_id))
            reply = _error(ws)

        assert reply["payload"]["error"]["code"] == "VALIDATION_ERROR"
        assert reply["payload"]["error"]["message"] == "The ready request was rejected."
        assert game.get_player(players["Omer"].player_id).is_ready is False

    def test_ready_in_lobby_rejected_by_domain_state_rule(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, players = _setup(client, ["Dana"])
        game = app.state.room_registry.get(room_code).game

        with player_ws(client, room_code, players["Dana"]) as ws:
            ws.send_json(envelope("player.ready", {}, game_id))
            reply = _error(ws)

        assert reply["payload"]["error"]["code"] == "VALIDATION_ERROR"
        assert game.get_player(players["Dana"].player_id).is_ready is False
        assert game.state is GameState.LOBBY

    def test_ready_with_non_empty_payload_rejected_without_mutation(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, players = _setup(client, ["Dana"])
        game = app.state.room_registry.get(room_code).game

        with player_ws(client, room_code, players["Dana"]) as ws:
            _submit(ws, game_id, players["Dana"])
            ws.send_json(envelope("player.ready", {"player_id": players["Dana"].player_id}, game_id))
            reply = _error(ws)

        assert reply["payload"]["error"]["message"] == "The player.ready payload must be exactly empty."
        assert game.get_player(players["Dana"].player_id).is_ready is False

    def test_ready_is_idempotent(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, players = _setup(client, ["Dana", "Omer"])
        game = app.state.room_registry.get(room_code).game

        with player_ws(client, room_code, players["Dana"]) as ws:
            _submit(ws, game_id, players["Dana"])
            ws.send_json(envelope("player.ready", {}, game_id))
            ws.send_json(envelope("player.ready", {}, game_id))
            ws.send_json({"nope": True})
            messages = collect_until(ws, "error")

        # The first error is the malformed frame — neither ready produced one.
        assert messages[-1]["payload"]["error"]["message"] == "The message is not a valid realtime envelope."
        assert game.get_player(players["Dana"].player_id).is_ready is True
        assert game.state is GameState.PROFILE_COLLECTION

    def test_all_players_ready_transitions_to_ready_even_disconnected(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, players = _setup(client, ["Dana", "Omer"])
        game = app.state.room_registry.get(room_code).game

        with player_ws(client, room_code, players["Dana"]) as ws:
            _submit(ws, game_id, players["Dana"])
            ws.send_json(envelope("player.ready", {}, game_id))
        assert game.get_player(players["Dana"].player_id).connected is False
        assert game.state is GameState.PROFILE_COLLECTION

        with player_ws(client, room_code, players["Omer"]) as ws:
            _submit(ws, game_id, players["Omer"])
            ws.send_json(envelope("player.ready", {}, game_id))

        assert game.state is GameState.READY

    def test_disconnected_unready_player_blocks_ready_transition(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, players = _setup(client, ["Dana", "Omer"])
        game = app.state.room_registry.get(room_code).game

        with player_ws(client, room_code, players["Dana"]) as ws:
            _submit(ws, game_id, players["Dana"])
        with player_ws(client, room_code, players["Omer"]) as ws:
            _submit(ws, game_id, players["Omer"])
            ws.send_json(envelope("player.ready", {}, game_id))

        assert game.state is GameState.PROFILE_COLLECTION


class TestRealtimeContractOverWebSocket:
    def test_malformed_envelope_gets_validation_error_envelope(self) -> None:
        client = TestClient(create_app())
        room_code, game_id, players = _setup(client, ["Dana"])

        with player_ws(client, room_code, players["Dana"]) as ws:
            ws.send_json({"event": "player.ready", "payload": {}})
            reply = _error(ws)

        assert set(reply.keys()) == ENVELOPE_KEYS
        assert reply["game_id"] == game_id
        assert reply["payload"]["error"]["code"] == "VALIDATION_ERROR"

    def test_non_json_text_gets_validation_error_envelope(self) -> None:
        client = TestClient(create_app())
        room_code, _, players = _setup(client, ["Dana"])

        with player_ws(client, room_code, players["Dana"]) as ws:
            ws.send_text("this is not json")
            assert _error(ws)["payload"]["error"]["code"] == "VALIDATION_ERROR"

    def test_binary_frame_gets_validation_error_envelope(self) -> None:
        client = TestClient(create_app())
        room_code, _, players = _setup(client, ["Dana"])

        with player_ws(client, room_code, players["Dana"]) as ws:
            ws.send_bytes(b"\x00\x01binary")
            assert _error(ws)["payload"]["error"]["code"] == "VALIDATION_ERROR"

    def test_oversized_frame_is_rejected(self) -> None:
        client = TestClient(create_app())
        room_code, _, players = _setup(client, ["Dana"])

        with player_ws(client, room_code, players["Dana"]) as ws:
            ws.send_text("x" * 20_000)
            reply = _error(ws)

        assert reply["payload"]["error"]["message"] == "The message is too large."

    def test_unknown_event_gets_unknown_event_envelope(self) -> None:
        client = TestClient(create_app())
        room_code, game_id, players = _setup(client, ["Dana"])

        with player_ws(client, room_code, players["Dana"]) as ws:
            ws.send_json(envelope("player.dance", {}, game_id))
            assert _error(ws)["payload"]["error"]["code"] == "UNKNOWN_EVENT"

    def test_mismatched_game_id_is_rejected_and_socket_stays_usable(self) -> None:
        app = create_app()
        client = TestClient(app)
        room_code, game_id, players = _setup(client, ["Dana"])
        game = app.state.room_registry.get(room_code).game

        with player_ws(client, room_code, players["Dana"]) as ws:
            ws.send_json(envelope("player.profile_submit", profile_payload(players["Dana"].player_id), "another-game"))
            reply = _error(ws)
            assert reply["payload"]["error"]["code"] == "VALIDATION_ERROR"
            assert reply["game_id"] == game_id
            assert game.get_player(players["Dana"].player_id).has_profile is False
            _submit(ws, game_id, players["Dana"])

        assert game.get_player(players["Dana"].player_id).has_profile is True
        assert game.state is GameState.PROFILE_COLLECTION

    def test_player_join_resyncs_the_current_state(self) -> None:
        client = TestClient(create_app())
        room_code, game_id, players = _setup(client, ["Dana"])

        with player_ws(client, room_code, players["Dana"]) as ws:
            receive_until(ws, "room.updated")
            ws.send_json(envelope("player.join", {}, game_id))
            snapshot = receive_until(ws, "room.updated")

        assert snapshot["payload"]["room_code"] == room_code
