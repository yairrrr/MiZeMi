"""Unit tests for deterministic candidate quality scoring."""

from app.domain.game import Player
from app.domain.questions import (
    ProfileDataset,
    QuestionCandidate,
    QuestionOption,
    QuestionQualityScorer,
)


def _dataset(player_count: int) -> ProfileDataset:
    return ProfileDataset(
        Player(player_id=f"p{index}", display_name=f"Player {index}")
        for index in range(player_count)
    )


def _candidate(*player_ids: str) -> QuestionCandidate:
    return QuestionCandidate(
        text="Example question",
        options=(QuestionOption(option_id="correct", text="Correct"),),
        correct_option_id="correct",
        source_rule_id="example_rule",
        source_field_keys=(),
        involved_player_ids=player_ids,
    )


class TestQuestionQualityScorerCoverage:
    def test_full_group_coverage_scores_one(self) -> None:
        score = QuestionQualityScorer().score(
            _candidate("p0", "p1", "p2"),
            _dataset(3),
        )

        assert score == 1.0

    def test_partial_group_coverage_is_normalized(self) -> None:
        score = QuestionQualityScorer().score(_candidate("p0"), _dataset(4))

        assert score == 0.25

    def test_no_involved_players_scores_zero(self) -> None:
        assert QuestionQualityScorer().score(_candidate(), _dataset(2)) == 0.0

    def test_empty_dataset_scores_zero(self) -> None:
        assert QuestionQualityScorer().score(_candidate("p0"), _dataset(0)) == 0.0

    def test_duplicate_player_ids_count_once(self) -> None:
        score = QuestionQualityScorer().score(
            _candidate("p0", "p0", "p1"),
            _dataset(4),
        )

        assert score == 0.5

    def test_players_outside_current_dataset_do_not_inflate_score(self) -> None:
        score = QuestionQualityScorer().score(
            _candidate("p0", "player-who-left"),
            _dataset(2),
        )

        assert score == 0.5

    def test_same_input_produces_same_score(self) -> None:
        candidate = _candidate("p0", "p2")
        dataset = _dataset(3)
        scorer = QuestionQualityScorer()

        assert scorer.score(candidate, dataset) == scorer.score(candidate, dataset)
