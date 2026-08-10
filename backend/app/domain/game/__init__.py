"""Game domain package: shared Player/Profile contracts (MASTER_SPEC.md §9)."""

from app.domain.game.player import Player
from app.domain.game.profile import PlayerProfile, ProfileField

__all__ = ["Player", "PlayerProfile", "ProfileField"]
