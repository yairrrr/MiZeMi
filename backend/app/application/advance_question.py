"""Question progression orchestration (MASTER_SPEC.md §11).

Application layer around the domain's ``Game.advance_to_next_question``:
the domain still owns the LEADERBOARD → QUESTION_ACTIVE | FINISHED
transition; this service only guards the application boundary and reports
which question (if any) became active.

Transport-independent: the host trigger for ``game.next`` is not wired here
because the host authorization mechanism remains deferred (§0).
"""

from datetime import datetime

from app.domain.game import Game, GameState
from app.domain.questions import Question


class GameNotAdvanceableError(Exception):
    """Advancing is only allowed from LEADERBOARD."""

    def __init__(self, state: GameState) -> None:
        super().__init__(f"cannot advance from state {state.value}")
        self.state = state


class AdvanceQuestionService:
    """LEADERBOARD → next question, or the end of the game."""

    def advance(self, game: Game, *, opened_at: datetime | None = None) -> Question | None:
        """Advance ``game`` and return the newly active question.

        Returns ``None`` when the final question was already played and the
        game therefore finished. Raises ``GameNotAdvanceableError`` when the
        game is not at the leaderboard, leaving it untouched.
        """
        if game.state is not GameState.LEADERBOARD:
            raise GameNotAdvanceableError(game.state)
        game.advance_to_next_question(opened_at=opened_at)
        return game.current_question

    @staticmethod
    def is_finished(game: Game) -> bool:
        return game.state is GameState.FINISHED
