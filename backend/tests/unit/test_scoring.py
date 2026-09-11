"""Unit tests for the scoring policy and leaderboard (MASTER_SPEC.md §9.5, §9.7)."""

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.scoring import (
    LeaderboardEntry,
    SpeedBonusScoringPolicy,
    build_leaderboard,
    winners,
)

OPENED = datetime(2026, 9, 11, 10, 0, 0, tzinfo=UTC)


def _points(*, correct: bool = True, after_ms: int = 0, limit: int = 20) -> int:
    return SpeedBonusScoringPolicy().points_for(
        is_correct=correct,
        answered_at=OPENED + timedelta(milliseconds=after_ms),
        opened_at=OPENED,
        time_limit_seconds=limit,
    )


class TestSpeedBonusScoringPolicy:
    def test_wrong_answer_scores_zero(self) -> None:
        assert _points(correct=False, after_ms=0) == 0

    def test_instant_correct_answer_scores_maximum(self) -> None:
        assert _points(after_ms=0) == 1000

    def test_correct_answer_at_deadline_scores_base_points(self) -> None:
        assert _points(after_ms=20_000) == 500

    def test_halfway_answer_scores_midpoint(self) -> None:
        assert _points(after_ms=10_000) == 750

    def test_formula_uses_integer_millisecond_floor_division(self) -> None:
        # remaining 12_345ms of 20_000ms -> 500 * 12345 // 20000 = 308
        assert _points(after_ms=7_655) == 808

    def test_elapsed_time_is_clamped(self) -> None:
        assert _points(after_ms=-5_000) == 1000  # clock skew never exceeds max
        assert _points(after_ms=25_000) == 500   # late never goes below base

    def test_points_decrease_monotonically_with_time(self) -> None:
        samples = [_points(after_ms=ms) for ms in range(0, 20_001, 1_000)]
        assert samples == sorted(samples, reverse=True)

    def test_is_deterministic(self) -> None:
        assert _points(after_ms=4_321) == _points(after_ms=4_321)

    def test_invalid_time_limit_rejected(self) -> None:
        with pytest.raises(ValueError):
            _points(limit=0)


class TestLeaderboard:
    def test_orders_by_score_descending(self) -> None:
        entries = build_leaderboard(
            [("p1", "Dana"), ("p2", "Omer"), ("p3", "Noa")],
            {"p1": 500, "p2": 1500, "p3": 1000},
        )

        assert [e.player_id for e in entries] == ["p2", "p3", "p1"]
        assert [e.rank for e in entries] == [1, 2, 3]

    def test_equal_scores_share_rank_and_keep_join_order(self) -> None:
        entries = build_leaderboard(
            [("p1", "Dana"), ("p2", "Omer"), ("p3", "Noa"), ("p4", "Gil")],
            {"p1": 800, "p2": 1200, "p3": 1200, "p4": 800},
        )

        assert [(e.player_id, e.rank) for e in entries] == [
            ("p2", 1),
            ("p3", 1),
            ("p1", 3),
            ("p4", 3),
        ]

    def test_missing_scores_count_as_zero(self) -> None:
        entries = build_leaderboard([("p1", "Dana"), ("p2", "Omer")], {"p2": 10})

        assert entries[-1] == LeaderboardEntry(
            rank=2, player_id="p1", display_name="Dana", total_score=0
        )

    def test_all_zero_scores_are_all_rank_one(self) -> None:
        entries = build_leaderboard([("p1", "Dana"), ("p2", "Omer")], {})

        assert [e.rank for e in entries] == [1, 1]
        assert [e.player_id for e in entries] == ["p1", "p2"]

    def test_winners_are_every_rank_one_entry(self) -> None:
        entries = build_leaderboard(
            [("p1", "Dana"), ("p2", "Omer"), ("p3", "Noa")],
            {"p1": 900, "p2": 900, "p3": 100},
        )

        assert [w.player_id for w in winners(entries)] == ["p1", "p2"]

    def test_single_winner(self) -> None:
        entries = build_leaderboard([("p1", "Dana"), ("p2", "Omer")], {"p2": 5})

        assert [w.player_id for w in winners(entries)] == ["p2"]

    def test_empty_leaderboard_has_no_winners(self) -> None:
        assert build_leaderboard([], {}) == ()
        assert winners(()) == ()

    def test_ranking_is_deterministic(self) -> None:
        players = [(f"p{i}", f"Name{i}") for i in range(10)]
        scores = {f"p{i}": (i % 3) * 100 for i in range(10)}

        assert build_leaderboard(players, scores) == build_leaderboard(players, scores)
