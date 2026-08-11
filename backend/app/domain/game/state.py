"""Game-state domain model and structural transition rules (MASTER_SPEC.md §11).

Pure domain layer: no FastAPI, SQLAlchemy, Pydantic, or IO imports allowed.
"""

from enum import Enum, unique


@unique
class GameState(Enum):
    """The seven approved game states; names appear verbatim in payloads."""

    LOBBY = "LOBBY"
    PROFILE_COLLECTION = "PROFILE_COLLECTION"
    READY = "READY"
    QUESTION_ACTIVE = "QUESTION_ACTIVE"
    QUESTION_RESULTS = "QUESTION_RESULTS"
    LEADERBOARD = "LEADERBOARD"
    FINISHED = "FINISHED"


class GameStateMachine:
    """Answers whether a state-to-state transition is structurally legal.

    Structural legality only: the conditions that trigger a transition
    (all players ready, first profile accepted, answers received or timer
    expired, whether another question exists, host authorization) are
    orchestration concerns decided elsewhere. ``FINISHED`` is terminal,
    and a state-to-self move is not a game transition.
    """

    _ALLOWED: dict[GameState, frozenset[GameState]] = {
        GameState.LOBBY: frozenset({GameState.PROFILE_COLLECTION}),
        GameState.PROFILE_COLLECTION: frozenset({GameState.READY}),
        GameState.READY: frozenset({GameState.QUESTION_ACTIVE}),
        GameState.QUESTION_ACTIVE: frozenset({GameState.QUESTION_RESULTS}),
        GameState.QUESTION_RESULTS: frozenset({GameState.LEADERBOARD}),
        GameState.LEADERBOARD: frozenset({GameState.QUESTION_ACTIVE, GameState.FINISHED}),
        GameState.FINISHED: frozenset(),
    }

    def is_transition_allowed(self, current: GameState, target: GameState) -> bool:
        return target in self._ALLOWED[current]
