"""Unit tests for QuestionSelector (MASTER_SPEC.md §12.5)."""

import pytest

from app.domain.questions import QuestionCandidate, QuestionOption, QuestionSelector


def _candidate(
    text: str,
    rule: str = "rule_a",
    fields: tuple[str, ...] = ("field_a",),
    players: tuple[str, ...] = ("p1",),
) -> QuestionCandidate:
    return QuestionCandidate(
        text=text,
        options=(QuestionOption("a", "one"), QuestionOption("b", "two")),
        correct_option_id="a",
        source_rule_id=rule,
        source_field_keys=fields,
        involved_player_ids=players,
    )


class TestQuestionSelector:
    def test_selection_is_deterministic(self) -> None:
        scored = [
            (_candidate("Q1", fields=("f1",)), 0.5),
            (_candidate("Q2", rule="rule_b", fields=("f2",)), 0.5),
            (_candidate("Q3", rule="rule_c", fields=("f3",)), 0.5),
        ]

        first = QuestionSelector().select(scored, question_count=2)
        second = QuestionSelector().select(scored, question_count=2)

        assert first == second

    def test_prefers_higher_scores(self) -> None:
        scored = [
            (_candidate("Low", fields=("f1",)), 0.1),
            (_candidate("High", fields=("f2",)), 0.9),
        ]

        selected = QuestionSelector().select(scored, question_count=1)

        assert [c.text for c in selected] == ["High"]

    def test_exact_duplicate_text_selected_once(self) -> None:
        scored = [
            (_candidate("Same question?", rule="rule_a", fields=("f1",)), 0.9),
            (_candidate("  same QUESTION?  ", rule="rule_b", fields=("f2",)), 0.8),
        ]

        selected = QuestionSelector().select(scored, question_count=2)

        assert len(selected) == 1

    def test_same_rule_and_field_signature_selected_once(self) -> None:
        scored = [
            (_candidate("Who is unique for pizza?", fields=("food",)), 0.9),
            (_candidate("Who is unique for sushi?", fields=("food",)), 0.8),
        ]

        selected = QuestionSelector().select(scored, question_count=2)

        assert [c.text for c in selected] == ["Who is unique for pizza?"]

    def test_rule_diversity_beats_raw_score(self) -> None:
        scored = [
            (_candidate("A1", rule="rule_a", fields=("f1",)), 0.9),
            (_candidate("A2", rule="rule_a", fields=("f2",)), 0.8),
            (_candidate("B1", rule="rule_b", fields=("f3",)), 0.5),
        ]

        selected = QuestionSelector().select(scored, question_count=2)

        assert {c.text for c in selected} == {"A1", "B1"}

    def test_fewer_selectable_than_requested_returns_all(self) -> None:
        scored = [
            (_candidate("Q1", fields=("f1",)), 0.5),
            (_candidate("Q2", rule="rule_b", fields=("f2",)), 0.4),
        ]

        selected = QuestionSelector().select(scored, question_count=10)

        assert len(selected) == 2

    def test_question_count_limits_selection(self) -> None:
        scored = [
            (_candidate(f"Q{i}", rule=f"rule_{i}", fields=(f"f{i}",)), 0.5)
            for i in range(5)
        ]

        selected = QuestionSelector().select(scored, question_count=3)

        assert len(selected) == 3

    def test_question_count_below_one_rejected(self) -> None:
        with pytest.raises(ValueError):
            QuestionSelector().select([], question_count=0)

    def test_lower_player_reuse_wins_when_rule_count_and_score_tie(self) -> None:
        first = _candidate("First pick", rule="rule_a", fields=("f1",), players=("p1",))
        reused = _candidate("Alpha text", rule="rule_b", fields=("f2",), players=("p1",))
        fresh = _candidate("Zulu text", rule="rule_c", fields=("f3",), players=("p9",))
        scored = [(first, 0.9), (reused, 0.5), (fresh, 0.5)]

        selected = QuestionSelector().select(scored, question_count=2)

        # rule counts tie (0) and scores tie (.5); "Alpha" would win the text
        # tiebreak, so only lower player reuse can explain "Zulu" winning.
        assert [c.text for c in selected] == ["First pick", "Zulu text"]

    def test_same_rule_and_field_with_different_subjects_both_selectable(self) -> None:
        scored = [
            (_candidate("Who is unique for pizza?", fields=("food",), players=("p1", "p2")), 0.9),
            (_candidate("Who is unique for sushi?", fields=("food",), players=("p2", "p1")), 0.8),
        ]

        selected = QuestionSelector().select(scored, question_count=2)

        assert len(selected) == 2

    def test_same_rule_field_and_subject_deduplicated(self) -> None:
        scored = [
            (_candidate("Who is unique for pizza?", fields=("food",), players=("p1", "p2")), 0.9),
            (_candidate("Who is unique for bamba?", fields=("food",), players=("p1", "p3")), 0.8),
        ]

        selected = QuestionSelector().select(scored, question_count=2)

        assert [c.text for c in selected] == ["Who is unique for pizza?"]
