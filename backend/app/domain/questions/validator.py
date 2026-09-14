"""Structural candidate validation (MASTER_SPEC.md §12.3)."""

import re

from app.domain.questions.candidate import QuestionCandidate
from app.domain.questions.dataset import ProfileDataset
from app.domain.questions.language import normalize
from app.domain.questions.question import Difficulty


class QuestionValidator:
    """Reject candidates that violate approved correctness and safety rules.

    Enforces shared option, length, metadata and literal-answer constraints.
    Each concrete rule proves its own mathematical uniqueness before emitting
    a candidate; only consent-filtered data is available to either layer.
    """

    def is_valid(
        self,
        candidate: QuestionCandidate,
        dataset: ProfileDataset,
    ) -> bool:
        return self.rejection_reason(candidate, dataset) is None

    def rejection_reason(self, candidate: QuestionCandidate, dataset: ProfileDataset) -> str | None:
        """The first failed check, or ``None`` for a valid candidate."""
        if not isinstance(candidate.difficulty, Difficulty):
            return "difficulty"
        if not 2 <= len(candidate.options) <= 4:
            return "option_count"
        if len(candidate.text) > 600 or any(len(o.text) > 160 for o in candidate.options):
            return "text_length"
        if len(candidate.explanation) > 1200 or len(candidate.knowledge_version) > 64:
            return "explanation_length"
        if not candidate.text.strip():
            return "empty_text"

        option_ids = tuple(option.option_id for option in candidate.options)
        if any(not option_id.strip() for option_id in option_ids):
            return "empty_option_id"
        if len(option_ids) != len(set(option_ids)):
            return "duplicate_option_id"
        if option_ids.count(candidate.correct_option_id) != 1:
            return "correct_option_id"

        normalized_texts = tuple(
            self._normalize(option.text) for option in candidate.options
        )
        if any(not text for text in normalized_texts):
            return "empty_option_text"
        if len(normalized_texts) != len(set(normalized_texts)):
            return "duplicate_option_text"

        answer = next(o.text for o in candidate.options if o.option_id == candidate.correct_option_id)
        answer_key = self._normalize(answer)
        question_key = self._normalize(candidate.text)
        # Avoid clues accidentally naming their own answer. Short tokens and
        # numbers can coincide with grammatical words/counts without a reveal.
        # An either/or question that names every option reveals nothing.
        if (len(answer_key) >= 3 and not answer_key.isdecimal() and self._names(question_key, answer_key)
                and not all(self._names(question_key, text) for text in normalized_texts)):
            return "answer_named_in_question"
        if not set(candidate.focus_player_ids).issubset(dataset.player_ids):
            return "unknown_focus_player"

        if not set(candidate.involved_player_ids).issubset(dataset.player_ids):
            return "unknown_involved_player"
        if not set(candidate.source_field_keys).issubset(dataset.field_keys):
            return "unknown_field"

        return None

    @staticmethod
    def _names(text: str, phrase: str) -> bool:
        return re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text) is not None

    @staticmethod
    def _normalize(value: str) -> str:
        return str(normalize(value))
