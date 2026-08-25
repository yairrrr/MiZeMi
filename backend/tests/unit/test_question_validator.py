"""Unit tests for structural candidate validation."""

import pytest

from app.domain.game import Player, PlayerProfile, ProfileField
from app.domain.questions import (
    ProfileDataset,
    QuestionCandidate,
    QuestionOption,
    QuestionValidator,
)


def _dataset(*, allow_city: bool = True) -> ProfileDataset:
    player = Player(
        player_id="p1",
        display_name="Dana",
        profile=PlayerProfile(
            player_id="p1",
            fields=(ProfileField("city", "Haifa", allow_city),),
        ),
    )
    return ProfileDataset((player,))


def _candidate(**overrides: object) -> QuestionCandidate:
    values: dict[str, object] = {
        "text": "Which city appears in the group?",
        "options": (
            QuestionOption(option_id="haifa", text="Haifa"),
            QuestionOption(option_id="eilat", text="Eilat"),
        ),
        "correct_option_id": "haifa",
        "source_rule_id": "example_rule",
        "source_field_keys": ("city",),
        "involved_player_ids": ("p1",),
    }
    values.update(overrides)
    return QuestionCandidate(**values)  # type: ignore[arg-type]


class TestQuestionValidatorCorrectness:
    def test_accepts_structurally_valid_candidate(self) -> None:
        assert QuestionValidator().is_valid(_candidate(), _dataset()) is True

    def test_rejects_missing_correct_option(self) -> None:
        candidate = _candidate(correct_option_id="missing")

        assert QuestionValidator().is_valid(candidate, _dataset()) is False

    def test_rejects_duplicate_option_ids(self) -> None:
        candidate = _candidate(
            options=(
                QuestionOption(option_id="same", text="Haifa"),
                QuestionOption(option_id="same", text="Eilat"),
            ),
            correct_option_id="same",
        )

        assert QuestionValidator().is_valid(candidate, _dataset()) is False

    @pytest.mark.parametrize(
        "first_text, second_text",
        (("Haifa", " haifa "), ("PIZZA", "pizza")),
    )
    def test_rejects_option_texts_equal_after_normalization(
        self,
        first_text: str,
        second_text: str,
    ) -> None:
        candidate = _candidate(
            options=(
                QuestionOption(option_id="first", text=first_text),
                QuestionOption(option_id="second", text=second_text),
            ),
            correct_option_id="first",
        )

        assert QuestionValidator().is_valid(candidate, _dataset()) is False


class TestQuestionValidatorContent:
    @pytest.mark.parametrize("text", ("", "   "))
    def test_rejects_empty_question_text(self, text: str) -> None:
        assert QuestionValidator().is_valid(_candidate(text=text), _dataset()) is False

    def test_rejects_empty_option_text(self) -> None:
        candidate = _candidate(
            options=(
                QuestionOption(option_id="haifa", text=" "),
                QuestionOption(option_id="eilat", text="Eilat"),
            )
        )

        assert QuestionValidator().is_valid(candidate, _dataset()) is False

    def test_rejects_empty_option_id(self) -> None:
        candidate = _candidate(
            options=(
                QuestionOption(option_id=" ", text="Haifa"),
                QuestionOption(option_id="eilat", text="Eilat"),
            ),
            correct_option_id=" ",
        )

        assert QuestionValidator().is_valid(candidate, _dataset()) is False


class TestQuestionValidatorDatasetSafety:
    def test_rejects_player_absent_from_current_dataset(self) -> None:
        candidate = _candidate(involved_player_ids=("player-who-left",))

        assert QuestionValidator().is_valid(candidate, _dataset()) is False

    def test_rejects_field_absent_from_consented_dataset(self) -> None:
        candidate = _candidate(source_field_keys=("personal_fact",))

        assert QuestionValidator().is_valid(candidate, _dataset()) is False

    def test_rejects_non_consented_source_field(self) -> None:
        candidate = _candidate(source_field_keys=("city",))

        assert QuestionValidator().is_valid(candidate, _dataset(allow_city=False)) is False


class TestQuestionValidatorDeferredBounds:
    def test_does_not_invent_deferred_option_count_bounds(self) -> None:
        candidate = _candidate(
            options=(QuestionOption(option_id="haifa", text="Haifa"),),
            correct_option_id="haifa",
        )

        assert QuestionValidator().is_valid(candidate, _dataset()) is True
