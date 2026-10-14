"""Gameplay orchestration (MASTER_SPEC.md §9.4–§9.7, §11).

Application layer: turns host and player commands into domain calls and
returns plain outcome objects; the transport layer decides what to send and
to whom. No FastAPI, Pydantic, or asyncio here — concurrency (one command at
a time per room) and the question timer are the realtime layer's concern.

The clock is injected, so every timestamp the domain sees (question opening
time, answer receive time) is server-owned and tests stay deterministic.
"""

import hashlib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum, unique

from app.application.advance_question import AdvanceQuestionService
from app.application.start_game import (
    GameNotStartableError,
    NoQuestionsGeneratedError,
    QuestionGenerationConfig,
    StartGameService,
)
from app.domain.game import (
    Answer,
    Game,
    GameState,
    InvalidStateTransitionError,
    RoundResult,
)
from app.domain.questions import ProfileDataset, Question, QuestionGenerator
from app.domain.questions.ai_generator import AIQuestionGenerator
from app.domain.scoring import (
    LeaderboardEntry,
    ScoringPolicy,
    SpeedBonusScoringPolicy,
    build_leaderboard,
)
from app.domain.statistics import QuestionStatistics, QuestionStatisticsCalculator
from app.infrastructure.ai_client import (
    AIClientUnavailable,
    AIGenerationError,
    AIRateLimitError,
)

logger = logging.getLogger("mizemi.gameplay")

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


class RoomChangedDuringGenerationError(Exception):
    """The roster changed while AI questions were being written for the old one."""


@dataclass(frozen=True)
class AiStartTicket:
    """Immutable snapshot of a room taken when the host pressed start."""

    dataset: ProfileDataset
    generation: QuestionGenerationConfig


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
        ai_generator: AIQuestionGenerator | None = None,
    ) -> None:
        self._config = config
        self._clock = clock if clock is not None else utc_now
        self._start = StartGameService(generator)
        self._advance = AdvanceQuestionService()
        self._scoring = scoring if scoring is not None else SpeedBonusScoringPolicy()
        self._statistics = QuestionStatisticsCalculator()
        # None → AI mode is disabled for this deployment; a request for
        # question_source="ai" is answered with the standard algorithmic path.
        self._ai_generator = ai_generator

    @property
    def config(self) -> GameplayConfig:
        return self._config

    @property
    def ai_available(self) -> bool:
        return self._ai_generator is not None

    def now(self) -> datetime:
        return self._clock()

    def _generation_config(self, game: Game) -> QuestionGenerationConfig:
        return QuestionGenerationConfig(
            question_count=game.config.question_count,
            language=game.config.language,
            time_limit_seconds=self._config.time_limit_seconds,
            seed=seed_for_game(game.game_id),
        )

    def start_game(self, game: Game) -> tuple[Question, ...]:
        """Generate the question set and open the first question (blocking).

        Algorithmic games are instant. A room that opted into
        ``question_source="ai"`` goes through the three AI phases below, which
        can take a long time because they call a network service: the realtime
        layer therefore drives those phases itself (generation in a worker
        thread). This method is the plain sequential composition, for callers
        that are not on an event loop.

        Raises ``GameNotStartableError`` or ``NoQuestionsGeneratedError``
        exactly as before; both leave the game in its previous state.
        """
        if not self.wants_ai_start(game):
            return self._start.start(game, self._generation_config(game), opened_at=self._clock())
        ticket = self.begin_ai_start(game)
        return self.finish_ai_start(game, ticket, self.generate_ai_questions(ticket))

    # --- AI start, in three phases ---------------------------------------------------

    def wants_ai_start(self, game: Game) -> bool:
        """True when this game asked for AI questions and the server can make them."""
        return game.config.question_source == "ai" and self._ai_generator is not None

    def begin_ai_start(self, game: Game) -> AiStartTicket:
        """Phase 1 — snapshot the room. Cheap; call it on the event loop.

        The snapshot is immutable, so phase 2 can read it from a worker thread
        while the live ``Game`` keeps changing. Raises ``GameNotStartableError``
        when the game is not READY.
        """
        if game.state is not GameState.READY:
            raise GameNotStartableError(game.state)
        return AiStartTicket(
            dataset=ProfileDataset(game.players, language=game.config.language),
            generation=self._generation_config(game),
        )

    def generate_ai_questions(self, ticket: AiStartTicket) -> tuple[Question, ...] | None:
        """Phase 2 — ask the AI. BLOCKING: never call this on the event loop.

        Touches only the immutable ticket. Returns ``None`` — the signal to fall
        back to the algorithmic engine — on any failure. Only the exception
        *type* is logged, so neither the API key nor profile data can leak.
        """
        assert self._ai_generator is not None
        generation = ticket.generation
        try:
            questions = self._ai_generator.generate(
                ticket.dataset,
                question_count=generation.question_count,
                time_limit_seconds=generation.time_limit_seconds,
                seed=generation.seed,
                language=generation.language,
            )
        except (AIGenerationError, AIRateLimitError, AIClientUnavailable) as exc:
            # The exception's own message is designed to be safe (no key, no
            # profile data), so we can log it here to help diagnose quality
            # regressions. Nothing from the API response is included.
            logger.warning(
                "AI start failed, falling back to algorithmic: %s: %s",
                type(exc).__name__, exc,
            )
            return None
        except Exception as exc:  # noqa: BLE001 — never leak details.
            logger.error("Unexpected AI failure, falling back: %s", type(exc).__name__)
            return None
        return questions or None

    def finish_ai_start(
        self,
        game: Game,
        ticket: AiStartTicket,
        questions: tuple[Question, ...] | None,
    ) -> tuple[Question, ...]:
        """Phase 3 — open the game. Call it on the event loop, under the room lock.

        Re-checks the room, because it may have changed while the AI worked:
        ``GameNotStartableError`` if it is no longer READY,
        ``RoomChangedDuringGenerationError`` if the roster is different (the
        AI questions were written for other players). With ``questions=None``
        the algorithmic engine starts the game from the *current* roster.
        """
        if game.state is not GameState.READY:
            raise GameNotStartableError(game.state)
        if questions:
            if tuple(p.player_id for p in game.players) != ticket.dataset.player_ids:
                raise RoomChangedDuringGenerationError()
            game.start(questions, opened_at=self._clock())
            return questions
        return self._start.start(game, ticket.generation, opened_at=self._clock())

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
