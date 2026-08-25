"""Unit tests for the shared Question domain types (MASTER_SPEC.md §9.3)."""

from dataclasses import FrozenInstanceError

import pytest

from app.domain.questions import Question, QuestionOption, QuestionType


def _options() -> tuple[QuestionOption, ...]:
    return (
        QuestionOption(option_id="option-pizza", text="Pizza"),
        QuestionOption(option_id="option-pasta", text="Pasta"),
    )


def _question(**overrides: object) -> Question:
    values: dict[str, object] = {
        "question_id": "question-1",
        "index": 0,
        "total_questions": 5,
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "text": "What is the most common favorite food?",
        "options": _options(),
        "correct_option_id": "option-pizza",
        "time_limit_seconds": 20,
    }
    values.update(overrides)
    return Question(**values)  # type: ignore[arg-type]


class TestQuestionType:
    def test_multiple_choice_is_the_only_mvp_question_type(self) -> None:
        assert list(QuestionType) == [QuestionType.MULTIPLE_CHOICE]
        assert QuestionType.MULTIPLE_CHOICE.value == "multiple_choice"


class TestQuestionOption:
    def test_option_id_is_an_opaque_string(self) -> None:
        option = QuestionOption(option_id="server-generated-id", text="Pizza")

        assert option.option_id == "server-generated-id"
        assert option.text == "Pizza"

    def test_option_is_immutable(self) -> None:
        option = QuestionOption(option_id="option-1", text="Pizza")

        with pytest.raises(FrozenInstanceError):
            option.text = "Pasta"  # type: ignore[misc]


class TestQuestion:
    def test_valid_question_stores_the_shared_domain_contract(self) -> None:
        question = _question()

        assert question.question_id == "question-1"
        assert question.index == 0
        assert question.total_questions == 5
        assert question.question_type is QuestionType.MULTIPLE_CHOICE
        assert question.options == _options()
        assert question.correct_option_id == "option-pizza"
        assert question.time_limit_seconds == 20

    def test_question_has_no_started_at_domain_field(self) -> None:
        assert not hasattr(_question(), "started_at")

    def test_correct_option_must_be_present(self) -> None:
        with pytest.raises(ValueError, match="exactly one option"):
            _question(correct_option_id="missing-option")

    def test_option_ids_must_be_unique(self) -> None:
        duplicate_options = (
            QuestionOption(option_id="same-id", text="Pizza"),
            QuestionOption(option_id="same-id", text="Pasta"),
        )

        with pytest.raises(ValueError, match="must be unique"):
            _question(options=duplicate_options, correct_option_id="same-id")

    def test_question_is_immutable(self) -> None:
        question = _question()

        with pytest.raises(FrozenInstanceError):
            question.text = "Changed"  # type: ignore[misc]
