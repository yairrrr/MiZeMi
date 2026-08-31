"""Wire schemas for the approved Player/Profile contracts (MASTER_SPEC.md §9.1, §9.2).

Read-only presentation mirrors of the domain: mappers never mutate domain
objects. The frontend counterparts live in frontend/src/types/contracts.ts —
changes here are shared-contract changes (§21).
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator

from app.domain.game import Player, PlayerProfile
from app.domain.questions.question import Question


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
    """The §13 create-room response — exactly room_code and game_id."""

    model_config = ConfigDict(extra="forbid")

    room_code: str
    game_id: str


class JoinRoomRequest(BaseModel):
    """The §13 join request — exactly display_name; rules enforced in application."""

    model_config = ConfigDict(extra="forbid")

    display_name: str


class PlayerReadyPayloadSchema(BaseModel):
    """The player.ready payload — exactly {} (MASTER_SPEC.md §14.2, v1.7).

    The connected player is authoritative; any key in the payload is a
    validation failure.
    """

    model_config = ConfigDict(extra="forbid")


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
