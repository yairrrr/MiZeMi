"""Player domain entity (MASTER_SPEC.md §9.1).

Pure domain layer: no FastAPI, SQLAlchemy, Pydantic, or IO imports allowed.
"""

from dataclasses import dataclass

from app.domain.game.profile import PlayerProfile


@dataclass
class Player:
    """A participant in a room, ephemeral and scoped to one game.

    The ``is_host`` and ``score`` wire fields (MASTER_SPEC.md §9.1) are
    deliberately absent here: ``is_host`` stays a wire/DTO concern while the
    internal host representation is deferred, and score state belongs to the
    Game/scoring side, so it is mapped in at serialization time. Display-name
    validation is deferred and not enforced here.
    """

    player_id: str
    display_name: str
    connected: bool = True
    is_ready: bool = False
    profile: PlayerProfile | None = None

    @property
    def has_profile(self) -> bool:
        return self.profile is not None
