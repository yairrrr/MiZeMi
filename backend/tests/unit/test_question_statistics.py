"""Unit tests for aggregate question statistics (MASTER_SPEC.md §9.6)."""

import pytest

from app.domain.questions import Question, QuestionOption, QuestionType
from app.domain.statistics import (
    OptionCount,
    QuestionStatistics,
    QuestionStatisticsCalculator,
)


def _question(
    *,
    option_ids: tuple[str, ...] = ("a", "b", "c", "d"),
    correct: str | None = None,
    question_id: str = "q1",
) -> Question:
    correct = correct if correct is not None else option_ids[0]
    return Question(
        question_id=question_id,
        index=0,
        total_questions=1,
        question_type=QuestionType.MULTIPLE_CHOICE,
        text="How many players picked pizza?",
        options=tuple(QuestionOption(option_id=oid, text=oid.upper()) for oid in option_ids),
        correct_option_id=correct,
        time_limit_seconds=20,
    )


@pytest.fixture
def calculator() -> QuestionStatisticsCalculator:
    return QuestionStatisticsCalculator()


class TestDistribution:
    def test_counts_answers_per_option(self, calculator) -> None:
        stats = calculator.calculate(
            _question(),
            ["a", "a", "b", "b", "b", "b", "b", "b", "c"],
            player_count=11,
        )

        assert stats.answer_distribution == (
            OptionCount("a", 2),
            OptionCount("b", 6),
            OptionCount("c", 1),
            OptionCount("d", 0),
        )

    def test_every_option_appears_in_question_order_including_zeros(
        self, calculator
    ) -> None:
        stats = calculator.calculate(
            _question(option_ids=("x", "y", "z")), ["y"], player_count=3
        )

        assert [entry.option_id for entry in stats.answer_distribution] == ["x", "y", "z"]
        assert [entry.count for entry in stats.answer_distribution] == [0, 1, 0]

    def test_no_answers_yields_all_zeros(self, calculator) -> None:
        stats = calculator.calculate(_question(), [], player_count=5)

        assert all(entry.count == 0 for entry in stats.answer_distribution)
        assert stats.answered_count == 0


class TestCounts:
    def test_answered_count_is_the_number_of_counted_answers(self, calculator) -> None:
        stats = calculator.calculate(_question(), ["a", "b", "c"], player_count=10)
        assert stats.answered_count == 3

    def test_player_count_is_carried_through_as_the_denominator(
        self, calculator
    ) -> None:
        stats = calculator.calculate(_question(), ["a"], player_count=9)
        assert stats.player_count == 9

    def test_answered_count_may_be_below_player_count(self, calculator) -> None:
        stats = calculator.calculate(_question(), ["a", "b"], player_count=8)
        assert stats.answered_count == 2
        assert stats.player_count == 8

    def test_correct_option_id_comes_from_the_question(self, calculator) -> None:
        stats = calculator.calculate(
            _question(correct="c"), ["a"], player_count=4
        )
        assert stats.correct_option_id == "c"

    def test_question_id_comes_from_the_question(self, calculator) -> None:
        stats = calculator.calculate(
            _question(question_id="q-42"), ["a"], player_count=4
        )
        assert stats.question_id == "q-42"


class TestRejections:
    def test_unknown_option_id_is_rejected(self, calculator) -> None:
        with pytest.raises(ValueError, match="unknown option_id"):
            calculator.calculate(_question(), ["a", "zzz"], player_count=5)

    def test_more_answers_than_players_is_rejected(self, calculator) -> None:
        with pytest.raises(ValueError, match="exceeds"):
            calculator.calculate(_question(), ["a", "b", "c"], player_count=2)

    def test_negative_player_count_is_rejected(self, calculator) -> None:
        with pytest.raises(ValueError, match="negative"):
            calculator.calculate(_question(), [], player_count=-1)


class TestAggregateOnlyAndImmutability:
    def test_result_exposes_no_per_player_data(self, calculator) -> None:
        stats = calculator.calculate(_question(), ["a"], player_count=3)
        field_names = set(QuestionStatistics.__dataclass_fields__)
        assert field_names == {
            "question_id",
            "correct_option_id",
            "answer_distribution",
            "answered_count",
            "player_count",
        }
        assert "player_id" not in repr(stats)

    def test_result_is_frozen(self, calculator) -> None:
        stats = calculator.calculate(_question(), ["a"], player_count=3)
        with pytest.raises(AttributeError):
            stats.answered_count = 99  # type: ignore[misc]

    def test_accepts_a_single_use_iterator(self, calculator) -> None:
        stats = calculator.calculate(_question(), iter(["a", "b", "b"]), player_count=5)
        assert stats.answered_count == 3
        assert stats.answer_distribution[1] == OptionCount("b", 2)
