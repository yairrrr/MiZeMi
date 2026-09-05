"""Unit tests for server game-event delivery (MASTER_SPEC.md §14.2, §14.3)."""

import asyncio
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest

from app.domain.questions import Question, QuestionOption, QuestionType
from app.realtime.connections import RoomConnectionRegistry
from app.realtime.game_events import (
    broadcast_question_started,
    build_question_started,
)

ENVELOPE_KEYS = {"event", "payload", "timestamp", "game_id"}
STARTED_AT = datetime(2026, 9, 5, 10, 15, 30, tzinfo=UTC)


class RecordingSink:
    def __init__(self) -> None:
        self.received: list[dict[str, Any]] = []

    async def send_json(self, data: Any) -> None:
        self.received.append(data)


def _question() -> Question:
    return Question(
        question_id="q1",
        index=0,
        total_questions=3,
        question_type=QuestionType.MULTIPLE_CHOICE,
        text="Who is the only player from Haifa?",
        options=(
            QuestionOption(option_id="a", text="Dana"),
            QuestionOption(option_id="b", text="Omer"),
        ),
        correct_option_id="b",
        time_limit_seconds=20,
    )


class TestBuildQuestionStarted:
    def test_envelope_has_approved_shape(self) -> None:
        envelope = build_question_started(_question(), "game-1", STARTED_AT)

        assert set(envelope.keys()) == ENVELOPE_KEYS
        assert envelope["event"] == "question.started"
        assert envelope["game_id"] == "game-1"
        # §14.3 timestamp is the *sender* time, distinct from the payload's
        # started_at (the question's activation time).
        assert envelope["timestamp"].endswith("Z")
        assert envelope["payload"]["started_at"] == "2026-09-05T10:15:30.000Z"

    def test_payload_is_the_public_question_contract(self) -> None:
        payload = build_question_started(_question(), "game-1", STARTED_AT)["payload"]

        assert set(payload.keys()) == {
            "question_id",
            "index",
            "total_questions",
            "question_type",
            "text",
            "options",
            "time_limit_seconds",
            "started_at",
        }
        assert payload["question_type"] == "multiple_choice"
        assert payload["started_at"] == "2026-09-05T10:15:30.000Z"
        assert [o["option_id"] for o in payload["options"]] == ["a", "b"]

    def test_correct_option_id_never_appears_anywhere(self) -> None:
        envelope = build_question_started(_question(), "game-1", STARTED_AT)

        assert "correct_option_id" not in envelope["payload"]
        assert "correct_option_id" not in str(envelope)
        assert all("correct" not in key for key in envelope["payload"])

    def test_naive_started_at_is_rejected(self) -> None:
        with pytest.raises(Exception):
            build_question_started(_question(), "game-1", datetime(2026, 9, 5, 10, 15, 30))

    def test_non_utc_started_at_normalizes_to_utc(self) -> None:
        israel = timezone(timedelta(hours=3))

        envelope = build_question_started(
            _question(), "game-1", datetime(2026, 9, 5, 13, 15, 30, tzinfo=israel)
        )

        assert envelope["payload"]["started_at"] == "2026-09-05T10:15:30.000Z"


class TestBroadcastQuestionStarted:
    def test_broadcast_reaches_room_players_only(self) -> None:
        connections = RoomConnectionRegistry()
        player_one, player_two, other_room = RecordingSink(), RecordingSink(), RecordingSink()
        connections.add("ABC234", player_one)
        connections.add("ABC234", player_two)
        connections.add("DEF567", other_room)

        delivered = asyncio.run(
            broadcast_question_started(
                connections, "ABC234", _question(), "game-1", STARTED_AT
            )
        )

        assert delivered == 2
        assert player_one.received[0]["event"] == "question.started"
        assert player_two.received[0]["payload"]["question_id"] == "q1"
        assert other_room.received == []

    def test_broadcast_stamps_server_time_when_not_supplied(self) -> None:
        connections = RoomConnectionRegistry()
        sink = RecordingSink()
        connections.add("ABC234", sink)
        before = datetime.now(UTC)

        asyncio.run(broadcast_question_started(connections, "ABC234", _question(), "g1"))

        stamped = sink.received[0]["payload"]["started_at"]
        assert stamped.endswith("Z")
        assert datetime.fromisoformat(stamped.replace("Z", "+00:00")) >= before.replace(
            microsecond=(before.microsecond // 1000) * 1000
        )

    def test_broadcast_to_room_without_connections_is_safe(self) -> None:
        delivered = asyncio.run(
            broadcast_question_started(
                RoomConnectionRegistry(), "ABC234", _question(), "g1", STARTED_AT
            )
        )

        assert delivered == 0
