"""Immutable, transport-independent room configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GameConfig:
    question_count: int = 20
    language: str = "en"

    def __post_init__(self) -> None:
        if type(self.question_count) is not int or not 1 <= self.question_count <= 50:
            raise ValueError("question_count must be an integer between 1 and 50")
        if self.language not in ("en", "he"):
            raise ValueError("language must be en or he")
