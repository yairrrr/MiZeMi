"""Game domain package: shared Player/Profile/state/Game contracts (MASTER_SPEC.md §8, §9, §11)."""

from app.domain.game.game import Game, InvalidStateTransitionError
from app.domain.game.player import Player
from app.domain.game.profile import PlayerProfile, ProfileField
from app.domain.game.state import GameState, GameStateMachine

__all__ = [
    "Game",
    "GameState",
    "GameStateMachine",
    "InvalidStateTransitionError",
    "Player",
    "PlayerProfile",
    "ProfileField",
]
