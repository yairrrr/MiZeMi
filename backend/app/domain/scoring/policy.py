"""Scoring policy (MASTER_SPEC.md §9.5).

Pure domain layer: no FastAPI, SQLAlchemy, Pydantic, or IO imports allowed.

Deliberately takes primitive arguments rather than domain entities, so the
scoring module never imports the game package (no import cycle) and a policy
can be tested in complete isolation.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta

_ONE_MILLISECOND = timedelta(milliseconds=1)


class ScoringPolicy(ABC):
    """Turns one answer's correctness and timing into non-negative points."""

    @abstractmethod
    def points_for(
        self,
        *,
        is_correct: bool,
        answered_at: datetime,
        opened_at: datetime,
        time_limit_seconds: int,
    ) -> int:
        """Return the points earned by one answer. Must be deterministic."""


class SpeedBonusScoringPolicy(ScoringPolicy):
    """The approved MVP formula (§9.5).

    * wrong answer (or no answer): 0 points
    * correct answer: ``BASE_POINTS + MAX_SPEED_BONUS * remaining / limit``

    ``remaining`` is the time left before the deadline when the server
    received the answer, clamped to ``[0, limit]``; the division is integer
    floor division on whole milliseconds, so the result is exact and
    platform-independent. A correct answer therefore earns between 500
    (answered at the deadline) and 1000 points (answered instantly).
    """

    BASE_POINTS = 500
    MAX_SPEED_BONUS = 500

    def points_for(
        self,
        *,
        is_correct: bool,
        answered_at: datetime,
        opened_at: datetime,
        time_limit_seconds: int,
    ) -> int:
        if not is_correct:
            return 0
        if time_limit_seconds < 1:
            raise ValueError("time_limit_seconds must be at least 1")
        limit_ms = time_limit_seconds * 1000
        elapsed_ms = (answered_at - opened_at) // _ONE_MILLISECOND
        remaining_ms = min(limit_ms, max(0, limit_ms - elapsed_ms))
        return self.BASE_POINTS + (self.MAX_SPEED_BONUS * remaining_ms) // limit_ms
