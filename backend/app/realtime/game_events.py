"""Server → client game events (MASTER_SPEC.md §14.2, §14.3).

Builds every approved server event inside the canonical four-key envelope.
Payload shapes are the Pydantic schemas in ``app.api.schemas`` (§13), so each
wire contract has exactly one definition. The correct option appears only in
``question.ended`` — never while a question is active (§9.3) — and no player
ever receives another player's individual answer (§10.6).
"""

from datetime import UTC, datetime
from typing import Any

from app.api.schemas import (
    AnswerAcceptedSchema,
    AnswerProgressSchema,
    GameFinishedSchema,
    GameStartedSchema,
    LeaderboardEntrySchema,
    LeaderboardSchema,
    PlayerQuestionResultSchema,
    PlayerSchema,
    PublicQuestionSchema,
    QuestionEndedSchema,
    QuestionStatisticsSchema,
    RoomSnapshotSchema,
)
from app.domain.game import Answer, Game, RoundResult
from app.domain.questions import Question
from app.domain.scoring import LeaderboardEntry, winners
from app.domain.statistics import QuestionStatistics
from app.realtime.connections import RoomConnectionRegistry
from app.realtime.envelope import RealtimeEnvelope
from app.realtime.errors import ErrorCode, ErrorDetail, ErrorPayload
from app.realtime.events import ServerToClientEvent


def build_envelope(
    event: ServerToClientEvent, payload: dict[str, Any], game_id: str
) -> dict[str, Any]:
    """Wrap a server payload in the §14.3 envelope with a server timestamp.

    The single construction path for every outbound realtime message. It
    delegates shape, timestamp normalization and serialization to the
    canonical ``RealtimeEnvelope`` model — this module never reimplements
    the envelope contract.
    """
    return RealtimeEnvelope(
        event=event.value,
        payload=payload,
        timestamp=datetime.now(UTC),
        game_id=game_id,
    ).model_dump(mode="json")


def build_error(game_id: str, code: ErrorCode, message: str) -> dict[str, Any]:
    """An §17 error payload inside the canonical envelope."""
    payload = ErrorPayload(error=ErrorDetail(code=code, message=message)).model_dump(
        mode="json"
    )
    return build_envelope(ServerToClientEvent.ERROR, payload, game_id)


def build_room_updated(room_code: str, game: Game) -> dict[str, Any]:
    """The authoritative room snapshot (§14.2 ``room.updated``)."""
    snapshot = RoomSnapshotSchema(
        room_code=room_code,
        state=game.state.value,
        players=[
            PlayerSchema.from_domain(player, score=game.score_of(player.player_id))
            for player in game.players
        ],
        current_question_index=game.current_question_index,
        total_questions=len(game.questions),
    )
    return build_envelope(
        ServerToClientEvent.ROOM_UPDATED, snapshot.model_dump(mode="json"), game.game_id
    )


def build_game_started(game: Game) -> dict[str, Any]:
    payload = GameStartedSchema(total_questions=len(game.questions))
    return build_envelope(
        ServerToClientEvent.GAME_STARTED, payload.model_dump(mode="json"), game.game_id
    )


def build_question_started(
    question: Question, game_id: str, started_at: datetime
) -> dict[str, Any]:
    """Build the ``question.started`` envelope for an active question.

    ``started_at`` is supplied by the caller (the server clock that opened
    the question). The payload is the §9.3 public question — the correct
    option is structurally unreachable through this schema.
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


def build_answer_accepted(game_id: str, answer: Answer) -> dict[str, Any]:
    payload = AnswerAcceptedSchema(question_id=answer.question_id, option_id=answer.option_id)
    return build_envelope(
        ServerToClientEvent.ANSWER_ACCEPTED, payload.model_dump(mode="json"), game_id
    )


def build_answer_progress(game: Game) -> dict[str, Any]:
    """``statistics.updated`` during an active question: counts only."""
    question = game.current_question
    question_id = question.question_id if question is not None else ""
    payload = AnswerProgressSchema(
        question_id=question_id,
        answered_count=len(game.answers_for(question_id)) if question is not None else 0,
        player_count=len(game.players),
    )
    return build_envelope(
        ServerToClientEvent.STATISTICS_UPDATED, payload.model_dump(mode="json"), game.game_id
    )


def build_question_ended(
    game: Game,
    result: RoundResult,
    statistics: QuestionStatistics,
    *,
    player_id: str | None,
) -> dict[str, Any]:
    """``question.ended`` for one recipient — the host passes ``player_id=None``."""
    player_result = None
    if player_id is not None:
        own = result.result_for(player_id)
        if own is not None:
            player_result = PlayerQuestionResultSchema(
                option_id=own.option_id,
                is_correct=own.is_correct,
                points_awarded=own.points_awarded,
                total_score=game.score_of(player_id),
            )
    payload = QuestionEndedSchema(
        question_id=result.question.question_id,
        correct_option_id=result.question.correct_option_id,
        statistics=QuestionStatisticsSchema.from_domain(statistics),
        player_result=player_result,
    )
    return build_envelope(
        ServerToClientEvent.QUESTION_ENDED, payload.model_dump(mode="json"), game.game_id
    )


def _leaderboard(entries: tuple[LeaderboardEntry, ...]) -> LeaderboardSchema:
    return LeaderboardSchema(entries=[LeaderboardEntrySchema.from_domain(e) for e in entries])


def build_leaderboard_updated(
    game_id: str, entries: tuple[LeaderboardEntry, ...]
) -> dict[str, Any]:
    return build_envelope(
        ServerToClientEvent.LEADERBOARD_UPDATED,
        _leaderboard(entries).model_dump(mode="json"),
        game_id,
    )


def build_game_finished(
    game_id: str, entries: tuple[LeaderboardEntry, ...]
) -> dict[str, Any]:
    payload = GameFinishedSchema(
        leaderboard=_leaderboard(entries),
        winners=[LeaderboardEntrySchema.from_domain(e) for e in winners(entries)],
    )
    return build_envelope(
        ServerToClientEvent.GAME_FINISHED, payload.model_dump(mode="json"), game_id
    )
