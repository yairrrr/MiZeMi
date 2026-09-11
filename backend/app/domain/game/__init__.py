"""Game domain package: shared Player/Profile/state/Game contracts (MASTER_SPEC.md §8, §9, §11)."""

# Import order matters here: player/profile/state must bind into this package's
# namespace before game.py runs, because game.py (via the questions package
# __init__) re-enters this package mid-initialization — dataset.py imports
# Player and ProfileField from app.domain.game.
from app.domain.game.player import Player
from app.domain.game.profile import PlayerProfile, ProfileField
from app.domain.game.state import GameState, GameStateMachine
from app.domain.game.answer import (
    Answer,
    AnswerRejectedError,
    AnswerRejection,
    PlayerRoundResult,
    RoundResult,
)
from app.domain.game.game import Game, InvalidStateTransitionError
from app.domain.game.room import Room

__all__ = [
    "Answer",
    "AnswerRejectedError",
    "AnswerRejection",
    "Game",
    "GameState",
    "GameStateMachine",
    "InvalidStateTransitionError",
    "Player",
    "PlayerProfile",
    "PlayerRoundResult",
    "ProfileField",
    "Room",
    "RoundResult",
]
