"""Immutable, transport-independent room configuration."""

from dataclasses import dataclass
from typing import Literal

QuestionSource = Literal["algorithmic", "ai"]


@dataclass(frozen=True)
class GameConfig:
    question_count: int = 5
    language: str = "en"
    # Per-game question generator (§9.0, §12.7). ``algorithmic`` is the pure
    # offline engine; ``ai`` opts the game into Anthropic-generated questions
    # that use consented profile data and still pass the shared validator.
    question_source: QuestionSource = "algorithmic"

    def __post_init__(self) -> None:
        if type(self.question_count) is not int or not 1 <= self.question_count <= 50:
            raise ValueError("question_count must be an integer between 1 and 50")
        if self.language not in ("en", "he"):
            raise ValueError("language must be en or he")
        if self.question_source not in ("algorithmic", "ai"):
            raise ValueError("question_source must be 'algorithmic' or 'ai'")
