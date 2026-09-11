"""Generate from consented profiles using the immutable room configuration."""

from dataclasses import dataclass
from datetime import datetime

from app.domain.game import Game, GameState
from app.domain.questions import ProfileDataset, Question, QuestionGenerator


@dataclass(frozen=True)
class QuestionGenerationConfig:
    """Validated generation inputs, including the shared question language."""

    question_count: int
    time_limit_seconds: int
    seed: int
    language: str = "en"


class GameNotStartableError(Exception):
    """The game is not in a state where starting is allowed."""

    def __init__(self, state: GameState) -> None:
        super().__init__(f"game cannot start from state {state.value}")
        self.state = state


class NoQuestionsGeneratedError(Exception):
    """The engine produced no questions for this group's consented data.

    The game stays in READY, unmutated. There is no approved §17 error code
    for this case; the transport that later triggers a start decides how to
    surface it once that contract exists.
    """


class StartGameService:
    """READY → generate questions → Game.start → QUESTION_ACTIVE."""

    def __init__(self, generator: QuestionGenerator | None = None) -> None:
        self._generator = generator if generator is not None else QuestionGenerator()

    def start(
        self,
        game: Game,
        config: QuestionGenerationConfig,
        *,
        opened_at: datetime | None = None,
    ) -> tuple[Question, ...]:
        """Start ``game`` and return its generated question sequence.

        Raises ``GameNotStartableError`` when the game is not in READY and
        ``NoQuestionsGeneratedError`` when the engine yields nothing; both
        leave the game untouched. ``opened_at`` is the server time the first
        question opens (enables the deadline and speed scoring).
        """
        if game.state is not GameState.READY:
            raise GameNotStartableError(game.state)

        dataset = ProfileDataset(game.players)
        questions = self._generator.generate(
            dataset,
            question_count=config.question_count,
            time_limit_seconds=config.time_limit_seconds,
            seed=config.seed,
            language=config.language,
        )
        if not questions:
            # Game.start would reject this anyway; failing here keeps the
            # reason explicit instead of surfacing a generic domain error.
            raise NoQuestionsGeneratedError(
                "the group's consented profile data supports no questions"
            )

        game.start(questions, opened_at=opened_at)
        return questions
