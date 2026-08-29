"""Contract-pinning tests for the realtime wire contracts (MASTER_SPEC.md §14, §17).

The literal value lists below mirror MASTER_SPEC.md and the frontend's
contractValues.test.ts: if either side drifts, one of these suites fails.
"""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.realtime import (
    ClientToServerEvent,
    ErrorCode,
    ErrorPayload,
    MalformedEnvelopeError,
    RealtimeEnvelope,
    ServerToClientEvent,
    UnknownEventError,
    parse_client_envelope,
)

APPROVED_CLIENT_EVENTS = [
    "player.join",
    "player.profile_submit",
    "player.ready",
    "game.start",
    "answer.submit",
    "game.next",
]

APPROVED_SERVER_EVENTS = [
    "room.updated",
    "player.joined",
    "player.updated",
    "game.started",
    "question.started",
    "answer.accepted",
    "question.ended",
    "statistics.updated",
    "leaderboard.updated",
    "game.finished",
    "error",
]

APPROVED_ERROR_CODES = [
    "ROOM_NOT_FOUND",
    "ROOM_FULL",
    "NAME_TAKEN",
    "INVALID_STATE_TRANSITION",
    "QUESTION_CLOSED",
    "ALREADY_ANSWERED",
    "NOT_HOST",
    "VALIDATION_ERROR",
    "UNKNOWN_EVENT",
    "INTERNAL_ERROR",
]


def _valid_raw_envelope() -> dict:
    return {
        "event": "player.ready",
        "payload": {},
        "timestamp": "2026-08-29T10:15:30.000Z",
        "game_id": "g1",
    }


class TestEventRegistries:
    def test_client_events_match_approved_contract_exactly(self) -> None:
        assert [event.value for event in ClientToServerEvent] == APPROVED_CLIENT_EVENTS
        assert len(ClientToServerEvent) == 6

    def test_server_events_match_approved_contract_exactly(self) -> None:
        assert [event.value for event in ServerToClientEvent] == APPROVED_SERVER_EVENTS
        assert len(ServerToClientEvent) == 11


class TestEnvelopeShape:
    def test_envelope_serializes_with_exactly_four_keys(self) -> None:
        envelope = RealtimeEnvelope.model_validate(_valid_raw_envelope())

        dumped = envelope.model_dump(mode="json")

        assert set(dumped.keys()) == {"event", "payload", "timestamp", "game_id"}

    def test_envelope_rejects_extra_top_level_fields(self) -> None:
        raw = _valid_raw_envelope()
        raw["room_code"] = "ABC123"

        with pytest.raises(ValidationError):
            RealtimeEnvelope.model_validate(raw)

    def test_timestamp_serializes_as_utc_iso8601_with_trailing_z(self) -> None:
        envelope = RealtimeEnvelope(
            event="room.updated",
            payload={},
            timestamp=datetime(2026, 8, 29, 10, 15, 30, tzinfo=UTC),
            game_id="g1",
        )

        assert envelope.model_dump(mode="json")["timestamp"] == "2026-08-29T10:15:30.000Z"

    def test_timestamp_round_trips_through_parse_and_serialize(self) -> None:
        raw = _valid_raw_envelope()

        envelope = RealtimeEnvelope.model_validate(raw)

        assert envelope.timestamp == datetime(2026, 8, 29, 10, 15, 30, tzinfo=UTC)
        assert envelope.model_dump(mode="json")["timestamp"] == raw["timestamp"]

    def test_naive_datetime_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RealtimeEnvelope(
                event="room.updated",
                payload={},
                timestamp=datetime(2026, 8, 29, 10, 15, 30),  # naive
                game_id="g1",
            )

    def test_wire_timestamp_without_timezone_is_malformed(self) -> None:
        raw = _valid_raw_envelope()
        raw["timestamp"] = "2026-08-29T10:15:30"  # no Z, no offset

        with pytest.raises(MalformedEnvelopeError):
            parse_client_envelope(raw)

    def test_non_utc_aware_timestamp_normalizes_to_utc_z(self) -> None:
        israel = timezone(timedelta(hours=3))
        envelope = RealtimeEnvelope(
            event="room.updated",
            payload={},
            timestamp=datetime(2026, 8, 29, 13, 15, 30, tzinfo=israel),
            game_id="g1",
        )

        assert envelope.model_dump(mode="json")["timestamp"] == "2026-08-29T10:15:30.000Z"


class TestParseClientEnvelope:
    def test_valid_known_client_event_parses(self) -> None:
        event, envelope = parse_client_envelope(_valid_raw_envelope())

        assert event is ClientToServerEvent.PLAYER_READY
        assert envelope.game_id == "g1"

    def test_unknown_event_is_distinguishable_from_malformed(self) -> None:
        raw = _valid_raw_envelope()
        raw["event"] = "player.dance"

        with pytest.raises(UnknownEventError) as exc_info:
            parse_client_envelope(raw)

        assert exc_info.value.event == "player.dance"
        assert not isinstance(exc_info.value, MalformedEnvelopeError)

    def test_server_event_from_client_is_unknown_not_malformed(self) -> None:
        raw = _valid_raw_envelope()
        raw["event"] = "room.updated"  # valid name, but not a client intent

        with pytest.raises(UnknownEventError):
            parse_client_envelope(raw)

    def test_missing_field_is_malformed_not_unknown(self) -> None:
        raw = _valid_raw_envelope()
        del raw["timestamp"]

        with pytest.raises(MalformedEnvelopeError) as exc_info:
            parse_client_envelope(raw)

        assert not isinstance(exc_info.value, UnknownEventError)

    def test_invalid_field_type_is_malformed(self) -> None:
        raw = _valid_raw_envelope()
        raw["payload"] = "not-an-object"

        with pytest.raises(MalformedEnvelopeError):
            parse_client_envelope(raw)


class TestErrorPayload:
    def test_all_approved_error_codes_validate(self) -> None:
        assert [code.value for code in ErrorCode] == APPROVED_ERROR_CODES
        for code in APPROVED_ERROR_CODES:
            payload = ErrorPayload.model_validate(
                {"error": {"code": code, "message": "something happened"}}
            )
            assert payload.error.code.value == code

    def test_unknown_error_code_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ErrorPayload.model_validate(
                {"error": {"code": "TOTALLY_MADE_UP", "message": "nope"}}
            )

    def test_message_is_required(self) -> None:
        with pytest.raises(ValidationError):
            ErrorPayload.model_validate({"error": {"code": "ROOM_NOT_FOUND"}})

    def test_details_is_optional_and_accepted(self) -> None:
        without = ErrorPayload.model_validate(
            {"error": {"code": "ROOM_NOT_FOUND", "message": "no such room"}}
        )
        with_details = ErrorPayload.model_validate(
            {
                "error": {
                    "code": "ROOM_NOT_FOUND",
                    "message": "no such room",
                    "details": {"room_code": "K7PW3N"},
                }
            }
        )

        assert without.error.details is None
        assert with_details.error.details == {"room_code": "K7PW3N"}

    def test_absent_details_key_is_omitted_from_output(self) -> None:
        payload = ErrorPayload.model_validate(
            {"error": {"code": "ROOM_NOT_FOUND", "message": "no such room"}}
        )

        dumped = payload.model_dump(mode="json")

        assert payload.error.details is None
        assert "details" not in dumped["error"]
        assert dumped == {"error": {"code": "ROOM_NOT_FOUND", "message": "no such room"}}

    def test_output_matches_nested_error_contract(self) -> None:
        payload = ErrorPayload.model_validate(
            {"error": {"code": "NOT_HOST", "message": "host only", "details": {"x": 1}}}
        )

        dumped = payload.model_dump(mode="json")

        assert dumped == {
            "error": {"code": "NOT_HOST", "message": "host only", "details": {"x": 1}}
        }
