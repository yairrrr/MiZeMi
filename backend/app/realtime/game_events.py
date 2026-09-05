"""Server → client game event delivery (MASTER_SPEC.md §14.2, §14.3).

Builds approved server events inside the standard four-key envelope and
delivers them to a room's connected players. Only events whose payload
MASTER_SPEC already pins are implemented here: ``question.started`` carries
the §9.3 public question (§14.2), which structurally excludes
``correct_option_id``.

Deliberately absent: ``room.updated`` (payload not pinned beyond "state +
players"), ``game.started`` (payload undefined), ``question.ended``,
``statistics.updated``, ``leaderboard.updated`` and ``game.finished`` (their
payloads depend on scoring/statistics contracts that do not exist yet).
"""

from datetime import UTC, datetime
from typing import Any

from app.api.schemas import PublicQuestionSchema
from app.domain.questions import Question
from app.realtime.connections import RoomConnectionRegistry
from app.realtime.envelope import RealtimeEnvelope
from app.realtime.events import ServerToClientEvent


def build_envelope(
    event: ServerToClientEvent, payload: dict[str, Any], game_id: str
) -> dict[str, Any]:
    """Wrap a server payload in the §14.3 envelope with a server timestamp."""
    return RealtimeEnvelope(
        event=event.value,
        payload=payload,
        timestamp=datetime.now(UTC),
        game_id=game_id,
    ).model_dump(mode="json")


def build_question_started(
    question: Question, game_id: str, started_at: datetime
) -> dict[str, Any]:
    """Build the ``question.started`` envelope for an active question.

    ``started_at`` is supplied by the caller (the application/realtime layer
    owns the authoritative server clock; the domain Question has no such
    field). The payload is the §9.3 public question — the correct option is
    structurally unreachable through this schema.
    """
    payload = PublicQuestionSchema.from_domain(question, started_at=started_at).model_dump(
        mode="json"
    )
    return build_envelope(ServerToClientEvent.QUESTION_STARTED, payload, game_id)


async def broadcast_question_started(
    connections: RoomConnectionRegistry,
    room_code: str,
    question: Question,
    game_id: str,
    started_at: datetime | None = None,
) -> int:
    """Stamp the server time, then broadcast ``question.started`` to the room."""
    stamped = started_at if started_at is not None else datetime.now(UTC)
    message = build_question_started(question, game_id, stamped)
    return await connections.broadcast(room_code, message)
