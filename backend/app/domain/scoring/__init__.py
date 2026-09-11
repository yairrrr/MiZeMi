"""Scoring: the answer-points policy and leaderboard ranking (MASTER_SPEC.md §9.5, §9.7)."""

from app.domain.scoring.leaderboard import LeaderboardEntry, build_leaderboard, winners
from app.domain.scoring.policy import ScoringPolicy, SpeedBonusScoringPolicy

__all__ = [
    "LeaderboardEntry",
    "ScoringPolicy",
    "SpeedBonusScoringPolicy",
    "build_leaderboard",
    "winners",
]
