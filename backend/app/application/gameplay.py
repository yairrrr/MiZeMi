"""Gameplay orchestration (MASTER_SPEC.md §9.4–§9.7, §11).

Application layer: turns host and player commands into domain calls and
returns plain outcome objects; the transport layer decides what to send and
to whom. No FastAPI, Pydantic, or asyncio here — concurrency (one command at
a time per room) and the question timer are the realtime layer's concern.

The clock is injected, so every timestamp the domain sees (question opening
time, answer receive time) is server-owned and tests stay deterministic.
"""

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum, unique

from app.application.advance_question import AdvanceQuestionService
from app.application.start_game import QuestionGenerationConfig, StartGameService
from app.domain.game import (
    Answer,
    Game,
    GameState,
    InvalidStateTransitionError,
    RoundResult,
)
from app.domain.questions import Question, QuestionGenerator
from app.domain.scoring import (
    LeaderboardEntry,
    ScoringPolicy,
    SpeedBonusScoringPolicy,
    build_leaderboard,
)
from app.domain.statistics import QuestionStatistics, QuestionStatisticsCalculator

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


def seed_for_game(game_id: str) -> int:
    """A stable per-game seed, so a game's question set is reproducible (§12)."""
    return int.from_bytes(hashlib.sha256(game_id.encode("utf-8")).digest()[:8], "big")


@dataclass(frozen=True)
class GameplayConfig:
    """Per-game settings supplied by configuration (§16) — never hard-coded."""

    questions_per_game: int
    time_limit_seconds: int


@unique
class NextStep(Enum):
    LEADERBOARD = "leaderboard"
    QUESTION = "question"
    FINISHED = "finished"


@dataclass(frozen=True)
class NextOutcome:
    step: NextStep
    question: Question | None = None


@dataclass(frozen=True)
class AnswerOutcome:
    answer: Answer
    all_answered: bool


class GameplayService:
    """READY → questions → results → leaderboard → … → FINISHED."""

    def __init__(
        self,
        config: GameplayConfig,
        *,
        clock: Clock | None = None,
        generator: QuestionGenerator | None = None,
        scoring: ScoringPolicy | None = None,
    ) -> None:
        self._config = config
        self._clock = clock if clock is not None else utc_now
        self._start = StartGameService(generator)
        self._advance = AdvanceQuestionService()
        self._scoring = scoring if scoring is not None else SpeedBonusScoringPolicy()
        self._statistics = QuestionStatisticsCalculator()

    @property
    def config(self) -> GameplayConfig:
        return self._config

    def now(self) -> datetime:
        return self._clock()

    def start_game(self, game: Game) -> tuple[Question, ...]:
        """Generate the question set and open the first question.

        Raises ``GameNotStartableError`` (not READY) or
        ``NoQuestionsGeneratedError`` (no valid questions); both leave the
        game in its previous state.
        """
        generation = QuestionGenerationConfig(
            question_count=game.config.question_count,
            language=game.config.language,
            time_limit_seconds=self._config.time_limit_seconds,
            seed=seed_for_game(game.game_id),
        )
        return self._start.start(game, generation, opened_at=self._clock())

    def submit_answer(
        self, game: Game, player_id: str, question_id: str, option_id: str
    ) -> AnswerOutcome:
        """Record an answer stamped with the server clock (§9.4)."""
        answer = game.submit_answer(player_id, question_id, option_id, self._clock())
        return AnswerOutcome(answer=answer, all_answered=game.all_players_answered())

    def close_question(self, game: Game) -> RoundResult:
        """QUESTION_ACTIVE → QUESTION_RESULTS, applying the scoring policy."""
        return game.close_question(self._scoring)

    def next(self, game: Game) -> NextOutcome:
        """The host's ``game.next``: results → leaderboard → next / finished."""
        if game.state is GameState.QUESTION_RESULTS:
            game.show_leaderboard()
            return NextOutcome(NextStep.LEADERBOARD)
        if game.state is GameState.LEADERBOARD:
            question = self._advance.advance(game, opened_at=self._clock())
            if question is None:
                return NextOutcome(NextStep.FINISHED)
            return NextOutcome(NextStep.QUESTION, question)
        raise InvalidStateTransitionError(game.state, GameState.LEADERBOARD)

    def leaderboard(self, game: Game) -> tuple[LeaderboardEntry, ...]:
        return build_leaderboard(
            [(player.player_id, player.display_name) for player in game.players],
            game.scores,
        )

    def question_statistics(self, game: Game, result: RoundResult) -> QuestionStatistics:
        return self._statistics.calculate(
            result.question,
            [answer.option_id for answer in result.answers],
            player_count=len(game.players),
        )
