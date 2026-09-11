"""Leaderboard ranking (MASTER_SPEC.md §9.7).

Pure domain layer: no FastAPI, SQLAlchemy, Pydantic, or IO imports allowed.

Approved deterministic tie-breaking (§9.7):

1. Higher ``total_score`` first.
2. Equal scores share the same ``rank`` (standard competition ranking —
   1, 1, 3), so ties are never decided arbitrarily.
3. Within equal scores, entries are listed in player join order.

``winners`` are every entry holding rank 1, so a tie for first place produces
co-winners rather than a random single winner.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class LeaderboardEntry:
    rank: int
    player_id: str
    display_name: str
    total_score: int


def build_leaderboard(
    players_in_join_order: Sequence[tuple[str, str]],
    scores: Mapping[str, int],
) -> tuple[LeaderboardEntry, ...]:
    """Rank ``(player_id, display_name)`` pairs by their ``scores``.

    Players missing from ``scores`` count as 0. The input order is the join
    order used as the display tie-breaker.
    """
    indexed = [
        (position, player_id, display_name, scores.get(player_id, 0))
        for position, (player_id, display_name) in enumerate(players_in_join_order)
    ]
    ordered = sorted(indexed, key=lambda item: (-item[3], item[0]))

    entries: list[LeaderboardEntry] = []
    previous_score: int | None = None
    rank = 0
    for position, (_, player_id, display_name, total) in enumerate(ordered, start=1):
        if total != previous_score:
            rank = position
            previous_score = total
        entries.append(
            LeaderboardEntry(
                rank=rank,
                player_id=player_id,
                display_name=display_name,
                total_score=total,
            )
        )
    return tuple(entries)


def winners(entries: Sequence[LeaderboardEntry]) -> tuple[LeaderboardEntry, ...]:
    """Every entry at rank 1 — co-winners on a tie; empty for no players."""
    return tuple(entry for entry in entries if entry.rank == 1)
