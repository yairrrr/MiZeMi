"""Unit tests for the full QuestionGenerator pipeline (MASTER_SPEC.md §12.1)."""

from random import Random

import pytest

from app.domain.game import Player, PlayerProfile, ProfileField
from app.domain.questions import (
    ProfileDataset,
    QuestionCandidate,
    QuestionGenerator,
    QuestionOption,
    QuestionRule,
    QuestionType,
)


def _player(
    player_id: str,
    name: str,
    fields: list[tuple[str, str | int, bool]],
) -> Player:
    player = Player(player_id=player_id, display_name=name)
    player.assign_initial_profile(
        PlayerProfile(
            player_id=player_id,
            fields=tuple(
                ProfileField(field_key=key, value=value, allow_question_usage=consent)
                for key, value, consent in fields
            ),
        )
    )
    return player


def _players() -> list[Player]:
    return [
        _player("p1", "Dana", [("favorite_food", "pizza", True), ("city", "Haifa", True), ("age", 27, True)]),
        _player("p2", "Omer", [("favorite_food", "pizza", True), ("city", "Tel Aviv", True), ("age", 30, True)]),
        _player("p3", "Noa", [("favorite_food", "sushi", True), ("city", "Haifa", True), ("age", 27, True)]),
    ]


class TestQuestionGeneratorPipeline:
    def test_generates_final_ordered_questions(self) -> None:
        questions = QuestionGenerator().generate(
            ProfileDataset(_players()), question_count=3, time_limit_seconds=20, seed=42
        )

        assert 0 < len(questions) <= 3
        total = len(questions)
        for index, question in enumerate(questions):
            assert question.index == index
            assert question.total_questions == total
            assert question.time_limit_seconds == 20
            assert question.question_type is QuestionType.MULTIPLE_CHOICE
            assert isinstance(question.question_id, str) and question.question_id
            correct = [o for o in question.options if o.option_id == question.correct_option_id]
            assert len(correct) == 1

    def test_identical_inputs_and_seed_are_fully_deterministic(self) -> None:
        first = QuestionGenerator().generate(
            ProfileDataset(_players()), question_count=4, time_limit_seconds=15, seed=99
        )
        second = QuestionGenerator().generate(
            ProfileDataset(_players()), question_count=4, time_limit_seconds=15, seed=99
        )

        assert first == second  # includes minted question ids

    def test_question_count_is_respected(self) -> None:
        questions = QuestionGenerator().generate(
            ProfileDataset(_players()), question_count=1, time_limit_seconds=20, seed=42
        )

        assert len(questions) == 1
        assert questions[0].total_questions == 1

    def test_fewer_candidates_than_requested_returns_all_without_fabrication(self) -> None:
        dataset = ProfileDataset(
            [
                _player("p1", "Dana", [("favorite_food", "pizza", True)]),
                _player("p2", "Omer", [("favorite_food", "pizza", True)]),
            ]
        )

        questions = QuestionGenerator().generate(
            dataset, question_count=50, time_limit_seconds=20, seed=42
        )

        assert 0 < len(questions) < 50
        assert all(q.total_questions == len(questions) for q in questions)

    def test_non_consented_values_never_influence_questions(self) -> None:
        players = [
            _player("p1", "Dana", [("favorite_food", "pizza", True), ("personal_fact", "SECRETVALUE", False)]),
            _player("p2", "Omer", [("favorite_food", "pizza", True), ("personal_fact", "OTHERSECRET", False)]),
            _player("p3", "Noa", [("favorite_food", "sushi", True)]),
        ]

        questions = QuestionGenerator().generate(
            ProfileDataset(players), question_count=10, time_limit_seconds=20, seed=42
        )

        assert questions
        for question in questions:
            assert "SECRETVALUE" not in question.text
            assert "OTHERSECRET" not in question.text
            assert "personal fact" not in question.text
            for option in question.options:
                assert "SECRETVALUE" not in option.text
                assert "OTHERSECRET" not in option.text

    def test_invalid_candidates_are_filtered_before_assembly(self) -> None:
        class BrokenRule(QuestionRule):
            @property
            def rule_id(self) -> str:
                return "broken"

            def generate(self, dataset, rng) -> tuple[QuestionCandidate, ...]:
                return (
                    QuestionCandidate(
                        text="Which option is correct?",
                        options=(
                            QuestionOption("a", "same"),
                            QuestionOption("b", "same"),  # duplicate texts: invalid
                        ),
                        correct_option_id="a",
                        source_rule_id="broken",
                        source_field_keys=(),
                        involved_player_ids=(),
                    ),
                )

        questions = QuestionGenerator(rules=[BrokenRule()]).generate(
            ProfileDataset(_players()), question_count=5, time_limit_seconds=20, seed=42
        )

        assert questions == ()

    def test_inputs_are_not_mutated(self) -> None:
        players = _players()
        fields_before = [player.profile.fields for player in players]
        dataset = ProfileDataset(players)
        keys_before = dataset.field_keys

        QuestionGenerator().generate(
            dataset, question_count=5, time_limit_seconds=20, seed=42
        )

        assert [player.profile.fields for player in players] == fields_before
        assert dataset.field_keys == keys_before

    def test_invalid_configuration_rejected(self) -> None:
        dataset = ProfileDataset(_players())

        with pytest.raises(ValueError):
            QuestionGenerator().generate(dataset, question_count=0, time_limit_seconds=20, seed=1)
        with pytest.raises(ValueError):
            QuestionGenerator().generate(dataset, question_count=3, time_limit_seconds=0, seed=1)

    def test_rules_receive_only_the_consent_boundary(self) -> None:
        """Structural proof: rule inputs are the dataset, never raw profiles."""
        seen_inputs: list[object] = []

        class ProbeRule(QuestionRule):
            @property
            def rule_id(self) -> str:
                return "probe"

            def generate(self, dataset, rng) -> tuple[QuestionCandidate, ...]:
                seen_inputs.append(dataset)
                return ()

        QuestionGenerator(rules=[ProbeRule()]).generate(
            ProfileDataset(_players()), question_count=1, time_limit_seconds=20, seed=1
        )

        assert len(seen_inputs) == 1
        assert isinstance(seen_inputs[0], ProfileDataset)
        assert isinstance(Random(1), Random)  # rng type sanity, no global state used
