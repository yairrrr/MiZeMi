"""Answers and round results (MASTER_SPEC.md §9.4, §9.5).

Pure domain layer: no FastAPI, SQLAlchemy, Pydantic, or IO imports allowed.

An ``Answer`` is recorded with a server-supplied ``answered_at`` — client
timestamps never reach the domain (§9.4). A ``RoundResult`` is the immutable
outcome of closing one question: every player's result, in join order.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique

from app.domain.questions.question import Question


@unique
class AnswerRejection(Enum):
    """Why the server refused an answer (mapped to §17 codes at the boundary)."""

    QUESTION_NOT_ACTIVE = "question_not_active"
    WRONG_QUESTION = "wrong_question"
    UNKNOWN_PLAYER = "unknown_player"
    INVALID_OPTION = "invalid_option"
    ALREADY_ANSWERED = "already_answered"
    DEADLINE_PASSED = "deadline_passed"


class AnswerRejectedError(Exception):
    """A submitted answer was rejected; the game is left unchanged."""

    def __init__(self, reason: AnswerRejection) -> None:
        super().__init__(f"answer rejected: {reason.value}")
        self.reason = reason


@dataclass(frozen=True)
class Answer:
    """One accepted answer — at most one per player per question (§9.4)."""

    player_id: str
    question_id: str
    option_id: str
    answered_at: datetime


@dataclass(frozen=True)
class PlayerRoundResult:
    """A single player's outcome for one closed question.

    ``option_id`` is ``None`` when the player did not answer in time; such a
    player is not correct and earns no points.
    """

    player_id: str
    option_id: str | None
    is_correct: bool
    points_awarded: int


@dataclass(frozen=True)
class RoundResult:
    """The immutable outcome of closing one question."""

    question: Question
    answers: tuple[Answer, ...]
    player_results: tuple[PlayerRoundResult, ...]

    def result_for(self, player_id: str) -> PlayerRoundResult | None:
        for result in self.player_results:
            if result.player_id == player_id:
                return result
        return None
