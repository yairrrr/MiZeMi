"""Wire schemas for the approved Player/Profile contracts (MASTER_SPEC.md §9.1, §9.2).

Read-only presentation mirrors of the domain: mappers never mutate domain
objects. The frontend counterparts live in frontend/src/types/contracts.ts —
changes here are shared-contract changes (§21).
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.domain.game import Player, PlayerProfile
from app.domain.questions.question import Question
from app.domain.scoring import LeaderboardEntry
from app.domain.statistics import QuestionStatistics


class PlayerSchema(BaseModel):
    """The §9.1 Player wire contract — exactly these seven fields."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    display_name: str
    is_host: bool
    connected: bool
    has_profile: bool
    is_ready: bool
    score: int

    @classmethod
    def from_domain(cls, player: Player, *, score: int) -> "PlayerSchema":
        """Map a domain Player to its wire shape.

        ``score`` is a required caller-supplied value: the domain holds no
        score state until the scoring workstream lands, and this mapper must
        not fabricate one. ``is_host`` is emitted as False because §9.1
        defines the host as not being a player in the MVP.
        """
        return cls(
            player_id=player.player_id,
            display_name=player.display_name,
            is_host=False,
            connected=player.connected,
            has_profile=player.has_profile,
            is_ready=player.is_ready,
            score=score,
        )


class ProfileFieldSchema(BaseModel):
    """One §9.2 profile field; ``str | int`` is the approved interim typing."""

    model_config = ConfigDict(extra="forbid")

    field_key: str
    value: str | int
    allow_question_usage: bool


class PlayerProfileSchema(BaseModel):
    """The §9.2 profile envelope: player_id plus ordered fields."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    fields: list[ProfileFieldSchema]

    @classmethod
    def from_domain(cls, profile: PlayerProfile) -> "PlayerProfileSchema":
        return cls(
            player_id=profile.player_id,
            fields=[
                ProfileFieldSchema(
                    field_key=field.field_key,
                    value=field.value,
                    allow_question_usage=field.allow_question_usage,
                )
                for field in profile.fields
            ],
        )


class CreateRoomResponse(BaseModel):
    """The §13 create-room response.

    ``host_token`` is returned only to the creating client; it authorizes the
    host WebSocket (§14.1) and is never broadcast or persisted in plaintext.
    """

    model_config = ConfigDict(extra="forbid")

    room_code: str
    game_id: str
    host_token: str


class JoinRoomRequest(BaseModel):
    """The §13 join request — exactly display_name; rules enforced in application.

    The generous schema cap only rejects abusive payloads early; the approved
    1–20 character rule is applied after trimming by the application layer.
    """

    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(max_length=100)


class JoinRoomResponse(BaseModel):
    """The §13 join response: authoritative game id plus joined Player."""

    model_config = ConfigDict(extra="forbid")

    game_id: str
    player: PlayerSchema
    # The player's WebSocket credential (§14.1); returned only to this client.
    player_token: str


class PlayerReadyPayloadSchema(BaseModel):
    """The player.ready payload — exactly {} (MASTER_SPEC.md §14.2, v1.7).

    The connected player is authoritative; any key in the payload is a
    validation failure.
    """

    model_config = ConfigDict(extra="forbid")


class AnswerSubmissionSchema(BaseModel):
    """The answer.submit payload — exactly question_id + option_id (§9.4).

    Wire shape only. Recording an answer additionally requires the answer
    domain/scoring components and the deferred resubmission and deadline
    policies, so no handler consumes this schema yet.
    """

    model_config = ConfigDict(extra="forbid")

    question_id: str
    option_id: str


class QuestionOptionSchema(BaseModel):
    """One selectable answer on the wire (MASTER_SPEC.md §9.3)."""

    model_config = ConfigDict(extra="forbid")

    option_id: str
    text: str


class PublicQuestionSchema(BaseModel):
    """The §9.3 active-question wire shape.

    Deliberately has no ``correct_option_id`` field: the correct answer is
    never sent to clients while a question is active, and ``extra="forbid"``
    keeps it structurally unserializable through this schema.
    """

    model_config = ConfigDict(extra="forbid")

    question_id: str
    index: int
    total_questions: int
    question_type: Literal["multiple_choice"]
    text: str
    options: list[QuestionOptionSchema]
    time_limit_seconds: int
    started_at: datetime

    @field_validator("started_at")
    @classmethod
    def _require_timezone_aware(cls, value: datetime) -> datetime:
        # A naive datetime cannot be labeled Z without guessing its zone.
        if value.tzinfo is None:
            raise ValueError("started_at must be timezone-aware")
        return value

    @field_serializer("started_at")
    def _serialize_started_at(self, value: datetime) -> str:
        normalized = value.astimezone(UTC).replace(tzinfo=None)
        return normalized.isoformat(timespec="milliseconds") + "Z"

    @classmethod
    def from_domain(
        cls, question: Question, *, started_at: datetime
    ) -> "PublicQuestionSchema":
        """Map a domain Question to its public wire shape.

        ``started_at`` is a required caller-supplied value: the application
        layer stamps the authoritative server time when the question opens;
        this mapper never reads a clock. ``correct_option_id`` is never
        mapped.
        """
        return cls(
            question_id=question.question_id,
            index=question.index,
            total_questions=question.total_questions,
            question_type=question.question_type.value,
            text=question.text,
            options=[
                QuestionOptionSchema(option_id=option.option_id, text=option.text)
                for option in question.options
            ],
            time_limit_seconds=question.time_limit_seconds,
            started_at=started_at,
        )


class EmptyPayloadSchema(BaseModel):
    """A payload that must be exactly {} (``game.start``, ``game.next``)."""

    model_config = ConfigDict(extra="forbid")


class RemovePlayerPayloadSchema(BaseModel):
    """The host's ``player.remove`` payload (§14.2)."""

    model_config = ConfigDict(extra="forbid")

    player_id: str = Field(min_length=1, max_length=64)


class RoomSnapshotSchema(BaseModel):
    """The ``room.updated`` payload: the authoritative room snapshot (§14.2)."""

    model_config = ConfigDict(extra="forbid")

    room_code: str
    state: str
    players: list[PlayerSchema]
    current_question_index: int | None
    total_questions: int


class GameStartedSchema(BaseModel):
    """The ``game.started`` payload."""

    model_config = ConfigDict(extra="forbid")

    total_questions: int


class AnswerAcceptedSchema(BaseModel):
    """The ``answer.accepted`` payload, sent only to the answering player."""

    model_config = ConfigDict(extra="forbid")

    question_id: str
    option_id: str


class AnswerProgressSchema(BaseModel):
    """The ``statistics.updated`` payload during an active question.

    Counts only — no distribution and no correct option — so the live
    progress bar cannot leak the answer or the crowd's choice.
    """

    model_config = ConfigDict(extra="forbid")

    question_id: str
    answered_count: int
    player_count: int


class OptionStatisticsSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    option_id: str
    count: int
    percentage: float


class QuestionStatisticsSchema(BaseModel):
    """The §9.6 statistics shape plus a per-option ``percentage`` (0–100)."""

    model_config = ConfigDict(extra="forbid")

    question_id: str
    correct_option_id: str
    answer_distribution: list[OptionStatisticsSchema]
    answered_count: int
    player_count: int

    @classmethod
    def from_domain(cls, statistics: QuestionStatistics) -> "QuestionStatisticsSchema":
        answered = statistics.answered_count
        return cls(
            question_id=statistics.question_id,
            correct_option_id=statistics.correct_option_id,
            answer_distribution=[
                OptionStatisticsSchema(
                    option_id=entry.option_id,
                    count=entry.count,
                    percentage=round(entry.count * 100 / answered, 1) if answered else 0.0,
                )
                for entry in statistics.answer_distribution
            ],
            answered_count=answered,
            player_count=statistics.player_count,
        )


class PlayerQuestionResultSchema(BaseModel):
    """One player's own outcome, sent only to that player."""

    model_config = ConfigDict(extra="forbid")

    option_id: str | None
    is_correct: bool
    points_awarded: int
    total_score: int


class QuestionEndedSchema(BaseModel):
    """The ``question.ended`` payload (§14.2).

    ``player_result`` is the recipient's own result on player connections
    and ``null`` on the host connection — no player ever receives another
    player's individual answer.
    """

    model_config = ConfigDict(extra="forbid")

    question_id: str
    correct_option_id: str
    statistics: QuestionStatisticsSchema
    player_result: PlayerQuestionResultSchema | None


class LeaderboardEntrySchema(BaseModel):
    """One §9.7 leaderboard entry."""

    model_config = ConfigDict(extra="forbid")

    rank: int
    player_id: str
    display_name: str
    total_score: int

    @classmethod
    def from_domain(cls, entry: LeaderboardEntry) -> "LeaderboardEntrySchema":
        return cls(
            rank=entry.rank,
            player_id=entry.player_id,
            display_name=entry.display_name,
            total_score=entry.total_score,
        )


class LeaderboardSchema(BaseModel):
    """The §9.7 ``leaderboard.updated`` payload."""

    model_config = ConfigDict(extra="forbid")

    entries: list[LeaderboardEntrySchema]


class GameFinishedSchema(BaseModel):
    """The ``game.finished`` payload: final leaderboard plus every rank-1 winner."""

    model_config = ConfigDict(extra="forbid")

    leaderboard: LeaderboardSchema
    winners: list[LeaderboardEntrySchema]
