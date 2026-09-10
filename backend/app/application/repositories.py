"""Repository interfaces the application layer depends on (MASTER_SPEC.md §15).

Application-side contract (owned by Backend/Platform, §7). Implementations
live in ``app/infrastructure/repositories/``; no SQLAlchemy type appears here.

``GameRepository`` covers the approved MVP persistence point (§15): the game
runs in memory during play and the whole aggregate is persisted on reaching
``FINISHED``. ``get`` returns a read-only ``FinishedGameRecord`` — a plain
snapshot for statistics / retention / audit — not a live ``Game`` (the domain
aggregate has no rehydration path and the MVP never resumes a stored game).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.game import Game


@dataclass(frozen=True)
class RecordedProfileField:
    """One persisted profile field. ``value`` keeps the §9.2 interim ``str | int``."""

    field_key: str
    value: str | int
    allow_question_usage: bool


@dataclass(frozen=True)
class RecordedPlayer:
    player_id: str
    display_name: str
    connected: bool
    is_ready: bool
    has_profile: bool
    profile_fields: tuple[RecordedProfileField, ...]


@dataclass(frozen=True)
class RecordedQuestionOption:
    option_id: str
    text: str


@dataclass(frozen=True)
class RecordedQuestion:
    question_id: str
    index: int
    total_questions: int
    question_type: str
    text: str
    options: tuple[RecordedQuestionOption, ...]
    correct_option_id: str
    time_limit_seconds: int


@dataclass(frozen=True)
class FinishedGameRecord:
    """A read-only snapshot of a persisted game (§15)."""

    game_id: str
    state: str
    current_question_index: int | None
    players: tuple[RecordedPlayer, ...]
    questions: tuple[RecordedQuestion, ...]


class GameRepository(ABC):
    """Persist and read back a whole ``Game`` aggregate, keyed by ``game_id``."""

    @abstractmethod
    def save(self, game: Game) -> None:
        """Upsert the game's current state, players, profiles, and questions.

        The MVP caller invokes this once, on the ``FINISHED`` transition (§15).
        The method itself does not require ``FINISHED`` — it stores whatever
        state the aggregate is in — so future milestone snapshots can reuse it.
        The caller owns the transaction (§15) and commits.
        """

    @abstractmethod
    def get(self, game_id: str) -> "FinishedGameRecord | None":
        """Return the stored snapshot for ``game_id``, or ``None`` if absent."""

    @abstractmethod
    def delete(self, game_id: str) -> None:
        """Remove the stored game. Idempotent — a missing game is not an error.

        Used by the retention cleanup routine; the retention window itself
        remains deferred (§10.5).
        """
