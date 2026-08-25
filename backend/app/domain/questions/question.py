"""Shared question domain types (MASTER_SPEC.md §9.3).

Pure domain layer: no FastAPI, SQLAlchemy, Pydantic, or IO imports allowed.
"""

from dataclasses import dataclass
from enum import Enum, unique


@unique
class QuestionType(Enum):
    """Question formats supported by the MVP."""

    MULTIPLE_CHOICE = "multiple_choice"


@dataclass(frozen=True)
class QuestionOption:
    """One selectable answer; ``option_id`` is an opaque string."""

    option_id: str
    text: str


@dataclass(frozen=True)
class Question:
    """A generated server-domain question.

    ``correct_option_id`` remains private to the server. ``started_at`` is
    deliberately absent: the application layer adds the authoritative server
    time when this question becomes active.
    """

    question_id: str
    index: int
    total_questions: int
    question_type: QuestionType
    text: str
    options: tuple[QuestionOption, ...]
    correct_option_id: str
    time_limit_seconds: int

    def __post_init__(self) -> None:
        option_ids = tuple(option.option_id for option in self.options)
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("question option_id values must be unique")
        if option_ids.count(self.correct_option_id) != 1:
            raise ValueError("correct_option_id must identify exactly one option")
