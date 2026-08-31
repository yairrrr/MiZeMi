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
    # "Realtime connection status" (§9.1): set true only by an accepted
    # WebSocket connection (§14.1) — a newly joined player is not connected.
    connected: bool = False
    is_ready: bool = False
    profile: PlayerProfile | None = None

    @property
    def has_profile(self) -> bool:
        return self.profile is not None

    def assign_initial_profile(self, profile: PlayerProfile) -> None:
        """Assign this player's first profile.

        Scoped to initial assignment only: rejecting a second assignment here
        does not decide the deferred resubmission/finality product policy —
        editing/replacing, if ever approved, gets its own method.
        """
        if profile.player_id != self.player_id:
            raise ValueError(
                f"profile belongs to {profile.player_id!r}, not {self.player_id!r}"
            )
        if self.profile is not None:
            raise ValueError(f"player {self.player_id!r} already has a profile")
        self.profile = profile
