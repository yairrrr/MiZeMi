"""Wire schemas for the approved Player/Profile contracts (MASTER_SPEC.md §9.1, §9.2).

Read-only presentation mirrors of the domain: mappers never mutate domain
objects. The frontend counterparts live in frontend/src/types/contracts.ts —
changes here are shared-contract changes (§21).
"""

from pydantic import BaseModel, ConfigDict

from app.domain.game import Player, PlayerProfile


class PlayerSchema(BaseModel):
    """The §9.1 Player wire contract — exactly these seven fields."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    display_name: str
    is_host: bool
    connected: bool
    has_profile: bool
    is_ready: bool
    score: int

    @classmethod
    def from_domain(cls, player: Player, *, score: int) -> "PlayerSchema":
        """Map a domain Player to its wire shape.

        ``score`` is a required caller-supplied value: the domain holds no
        score state until the scoring workstream lands, and this mapper must
        not fabricate one. ``is_host`` is emitted as False because §9.1
        defines the host as not being a player in the MVP.
        """
        return cls(
            player_id=player.player_id,
            display_name=player.display_name,
            is_host=False,
            connected=player.connected,
            has_profile=player.has_profile,
            is_ready=player.is_ready,
            score=score,
        )


class ProfileFieldSchema(BaseModel):
    """One §9.2 profile field; ``str | int`` is the approved interim typing."""

    model_config = ConfigDict(extra="forbid")

    field_key: str
    value: str | int
    allow_question_usage: bool


class PlayerProfileSchema(BaseModel):
    """The §9.2 profile envelope: player_id plus ordered fields."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    fields: list[ProfileFieldSchema]

    @classmethod
    def from_domain(cls, profile: PlayerProfile) -> "PlayerProfileSchema":
        return cls(
            player_id=profile.player_id,
            fields=[
                ProfileFieldSchema(
                    field_key=field.field_key,
                    value=field.value,
                    allow_question_usage=field.allow_question_usage,
                )
                for field in profile.fields
            ],
        )
