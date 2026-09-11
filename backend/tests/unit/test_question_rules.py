"""Unit tests for the production question rules (MASTER_SPEC.md §12.2)."""

from random import Random

from app.domain.game import Player, PlayerProfile, ProfileField
from app.domain.questions import (
    MostCommonValueRule,
    ProfileDataset,
    QuestionValidator,
    UniqueValueRule,
    ValueCountRule,
    default_rules,
)


def _player(player_id: str, name: str, fields: list[tuple[str, str | int]]) -> Player:
    player = Player(player_id=player_id, display_name=name)
    player.assign_initial_profile(
        PlayerProfile(
            player_id=player_id,
            fields=tuple(
                ProfileField(field_key=key, value=value, allow_question_usage=True)
                for key, value in fields
            ),
        )
    )
    return player


def _group_dataset() -> ProfileDataset:
    """Dana+Omer share pizza; Noa is unique (sushi). Haifa 2 vs Tel Aviv 1."""
    return ProfileDataset(
        [
            _player("p1", "Dana", [("favorite_food", "pizza"), ("city", "Haifa")]),
            _player("p2", "Omer", [("favorite_food", "pizza"), ("city", "Tel Aviv")]),
            _player("p3", "Noa", [("favorite_food", "sushi"), ("city", "Haifa")]),
        ]
    )


class TestUniqueValueRule:
    def test_generates_unique_value_candidate_with_correct_subject(self) -> None:
        candidates = UniqueValueRule().generate(_group_dataset(), Random(7))

        sushi = [c for c in candidates if '"sushi"' in c.text]
        assert len(sushi) == 1
        candidate = sushi[0]
        assert candidate.text == 'Who is the only player whose favorite food is "sushi"?'
        correct = next(o for o in candidate.options if o.option_id == candidate.correct_option_id)
        assert correct.text == "Noa"
        assert candidate.involved_player_ids[0] == "p3"
        assert candidate.source_field_keys == ("favorite_food",)

    def test_no_candidates_when_no_value_is_unique(self) -> None:
        dataset = ProfileDataset(
            [
                _player("p1", "Dana", [("favorite_food", "pizza")]),
                _player("p2", "Omer", [("favorite_food", "pizza")]),
            ]
        )

        assert UniqueValueRule().generate(dataset, Random(7)) == ()

    def test_no_candidates_with_fewer_than_two_players(self) -> None:
        dataset = ProfileDataset([_player("p1", "Dana", [("city", "Haifa")])])

        assert UniqueValueRule().generate(dataset, Random(7)) == ()


class TestMostCommonValueRule:
    def test_generates_strict_majority_candidate(self) -> None:
        candidates = MostCommonValueRule().generate(_group_dataset(), Random(7))

        food = [c for c in candidates if "favorite food" in c.text]
        assert len(food) == 1
        candidate = food[0]
        assert candidate.text == "What is the most common favorite food in this group?"
        correct = next(o for o in candidate.options if o.option_id == candidate.correct_option_id)
        assert correct.text == "pizza"
        assert set(candidate.involved_player_ids) == {"p1", "p2"}

    def test_tie_produces_no_candidate(self) -> None:
        dataset = ProfileDataset(
            [
                _player("p1", "Dana", [("favorite_food", "pizza")]),
                _player("p2", "Omer", [("favorite_food", "sushi")]),
            ]
        )

        assert MostCommonValueRule().generate(dataset, Random(7)) == ()


class TestValueCountRule:
    def test_generates_count_candidate_with_correct_number(self) -> None:
        candidates = ValueCountRule().generate(_group_dataset(), Random(7))

        pizza = [c for c in candidates if '"pizza"' in c.text]
        assert len(pizza) == 1
        candidate = pizza[0]
        assert candidate.text == 'How many players have "pizza" as their favorite food?'
        correct = next(o for o in candidate.options if o.option_id == candidate.correct_option_id)
        assert correct.text == "2"
        assert set(candidate.involved_player_ids) == {"p1", "p2"}

    def test_empty_dataset_produces_no_candidates(self) -> None:
        assert ValueCountRule().generate(ProfileDataset([]), Random(7)) == ()


class TestAllProductionRules:
    def test_every_rule_produces_validator_approved_candidates(self) -> None:
        dataset = _group_dataset()
        validator = QuestionValidator()

        for rule in default_rules():
            candidates = rule.generate(dataset, Random(7))
            assert candidates, f"rule {rule.rule_id} produced nothing on supporting data"
            for candidate in candidates:
                assert validator.is_valid(candidate, dataset)
                correct_matches = [
                    o for o in candidate.options if o.option_id == candidate.correct_option_id
                ]
                assert len(correct_matches) == 1

    def test_rules_are_deterministic_for_identical_rng(self) -> None:
        dataset = _group_dataset()

        for rule in default_rules():
            assert rule.generate(dataset, Random(42)) == rule.generate(dataset, Random(42))

    def test_registry_exposes_stable_rule_ids(self) -> None:
        assert [rule.rule_id for rule in default_rules()] == [
            "unique_value",
            "most_common_value",
            "value_count",
        ]


class TestRuleEdgeCases:
    def test_most_common_three_one_one_has_strict_winner_and_valid_distractors(self) -> None:
        dataset = ProfileDataset(
            [
                _player("p1", "Dana", [("favorite_food", "pizza")]),
                _player("p2", "Omer", [("favorite_food", "pizza")]),
                _player("p3", "Noa", [("favorite_food", "pizza")]),
                _player("p4", "Gil", [("favorite_food", "sushi")]),
                _player("p5", "Adi", [("favorite_food", "falafel")]),
            ]
        )

        candidates = MostCommonValueRule().generate(dataset, Random(7))

        assert len(candidates) == 1
        candidate = candidates[0]
        correct = next(o for o in candidate.options if o.option_id == candidate.correct_option_id)
        assert correct.text == "pizza"
        assert {o.text for o in candidate.options} == {"pizza", "sushi", "falafel"}
        assert set(candidate.involved_player_ids) == {"p1", "p2", "p3"}
        assert QuestionValidator().is_valid(candidate, dataset)

    def test_value_count_single_player_produces_valid_two_option_question(self) -> None:
        dataset = ProfileDataset([_player("p1", "Dana", [("city", "Haifa")])])

        candidates = ValueCountRule().generate(dataset, Random(7))

        assert len(candidates) == 1
        candidate = candidates[0]
        assert {o.text for o in candidate.options} == {"1", "0"}
        correct = next(o for o in candidate.options if o.option_id == candidate.correct_option_id)
        assert correct.text == "1"
        assert QuestionValidator().is_valid(candidate, dataset)

    def test_unique_value_on_partial_field_is_truthful_for_consented_data(self) -> None:
        dataset = ProfileDataset(
            [
                _player("p1", "Dana", [("favorite_food", "pizza")]),
                _player("p2", "Omer", [("favorite_food", "pizza")]),
                _player("p3", "Noa", [("favorite_food", "pizza"), ("hobby", "chess")]),
            ]
        )

        candidates = UniqueValueRule().generate(dataset, Random(7))

        hobby = [c for c in candidates if "hobby" in c.text]
        assert len(hobby) == 1
        candidate = hobby[0]
        assert candidate.text == 'Who is the only player whose hobby is "chess"?'
        correct = next(o for o in candidate.options if o.option_id == candidate.correct_option_id)
        assert correct.text == "Noa"
        # Truthful relative to the consent-safe dataset: chess appears once.
        assert [pid for pid, value in dataset.values_for("hobby") if value == "chess"] == ["p3"]

    def test_duplicate_display_names_rejected_by_validator(self) -> None:
        dataset = ProfileDataset(
            [
                _player("p1", "Dana", [("favorite_food", "pizza")]),
                _player("p2", "Dana", [("favorite_food", "sushi")]),
            ]
        )

        candidates = UniqueValueRule().generate(dataset, Random(7))

        assert candidates  # the rule emits; the validator is the safety net
        validator = QuestionValidator()
        assert all(not validator.is_valid(c, dataset) for c in candidates)


class TestValueNormalization:
    def test_equivalent_spellings_are_grouped_together(self) -> None:
        dataset = ProfileDataset(
            [
                _player("p1", "Dana", [("favorite_food", "Pizza")]),
                _player("p2", "Omer", [("favorite_food", "  pizza ")]),
                _player("p3", "Noa", [("favorite_food", "sushi")]),
            ]
        )

        candidates = MostCommonValueRule().generate(dataset, Random(7))

        assert len(candidates) == 1
        correct = next(
            o for o in candidates[0].options if o.option_id == candidates[0].correct_option_id
        )
        assert correct.text == "Pizza"  # first-seen spelling is displayed
        assert set(candidates[0].involved_player_ids) == {"p1", "p2"}

    def test_numbers_are_rendered_without_quotes(self) -> None:
        dataset = ProfileDataset(
            [
                _player("p1", "Dana", [("age", 27)]),
                _player("p2", "Omer", [("age", 31)]),
            ]
        )

        texts = [c.text for c in UniqueValueRule().generate(dataset, Random(7))]

        assert "Who is the only player whose age is 27?" in texts
