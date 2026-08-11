"""Game domain package: shared Player/Profile/state contracts (MASTER_SPEC.md §9, §11)."""

from app.domain.game.player import Player
from app.domain.game.profile import PlayerProfile, ProfileField
from app.domain.game.state import GameState, GameStateMachine

__all__ = ["GameState", "GameStateMachine", "Player", "PlayerProfile", "ProfileField"]
