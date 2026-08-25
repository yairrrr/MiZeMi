"""Unit tests for QuestionCandidate and the QuestionRule contract."""

from abc import ABC
from dataclasses import FrozenInstanceError
from random import Random

import pytest

from app.domain.game import Player, PlayerProfile, ProfileField
from app.domain.questions import (
    ProfileDataset,
    QuestionCandidate,
    QuestionOption,
    QuestionRule,
)


def _candidate() -> QuestionCandidate:
    return QuestionCandidate(
        text="What is the most common city?",
        options=(
            QuestionOption(option_id="haifa", text="Haifa"),
            QuestionOption(option_id="eilat", text="Eilat"),
        ),
        correct_option_id="haifa",
        source_rule_id="example_rule",
        source_field_keys=("city",),
        involved_player_ids=("p1", "p2"),
        metadata=(("coverage", 2),),
    )


class SupportingRule(QuestionRule):
    @property
    def rule_id(self) -> str:
        return "supporting_rule"

    def generate(
        self,
        dataset: ProfileDataset,
        rng: Random,
    ) -> tuple[QuestionCandidate, ...]:
        del rng
        return (_candidate(),) if dataset.values_for("city") else ()


class IncompleteRule(QuestionRule):
    pass


class TestQuestionCandidate:
    def test_stores_rule_metadata_for_later_pipeline_stages(self) -> None:
        candidate = _candidate()

        assert candidate.source_rule_id == "example_rule"
        assert candidate.source_field_keys == ("city",)
        assert candidate.involved_player_ids == ("p1", "p2")
        assert candidate.metadata == (("coverage", 2),)

    def test_candidate_is_immutable(self) -> None:
        candidate = _candidate()

        with pytest.raises(FrozenInstanceError):
            candidate.text = "Changed"  # type: ignore[misc]

    def test_candidate_allows_invalid_output_for_validator_to_reject(self) -> None:
        candidate = QuestionCandidate(
            text="Invalid candidate",
            options=(
                QuestionOption(option_id="duplicate", text="Same"),
                QuestionOption(option_id="duplicate", text="Same"),
            ),
            correct_option_id="missing",
            source_rule_id="buggy_rule",
            source_field_keys=(),
            involved_player_ids=(),
        )

        assert candidate.correct_option_id == "missing"


class TestQuestionRule:
    def test_is_an_abstract_polymorphic_contract(self) -> None:
        assert issubclass(QuestionRule, ABC)
        with pytest.raises(TypeError):
            IncompleteRule()

    def test_rule_produces_candidates_for_supporting_dataset(self) -> None:
        player = Player(
            player_id="p1",
            display_name="Dana",
            profile=PlayerProfile(
                player_id="p1",
                fields=(ProfileField("city", "Haifa", True),),
            ),
        )

        candidates = SupportingRule().generate(ProfileDataset((player,)), Random(7))

        assert candidates == (_candidate(),)

    def test_rule_returns_zero_candidates_for_non_supporting_dataset(self) -> None:
        candidates = SupportingRule().generate(ProfileDataset(()), Random(7))

        assert candidates == ()

    def test_rule_cannot_see_non_consented_fields(self) -> None:
        player = Player(
            player_id="p1",
            display_name="Dana",
            profile=PlayerProfile(
                player_id="p1",
                fields=(ProfileField("city", "Haifa", False),),
            ),
        )

        candidates = SupportingRule().generate(ProfileDataset((player,)), Random(7))

        assert candidates == ()
