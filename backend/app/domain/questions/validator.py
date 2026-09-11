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
        if not isinstance(candidate.difficulty, Difficulty):
            return False
        if not 2 <= len(candidate.options) <= 4:
            return False
        if len(candidate.text) > 600 or any(len(o.text) > 160 for o in candidate.options):
            return False
        if not candidate.text.strip():
            return False

        option_ids = tuple(option.option_id for option in candidate.options)
        if any(not option_id.strip() for option_id in option_ids):
            return False
        if len(option_ids) != len(set(option_ids)):
            return False
        if option_ids.count(candidate.correct_option_id) != 1:
            return False

        normalized_texts = tuple(
            self._normalize(option.text) for option in candidate.options
        )
        if any(not text for text in normalized_texts):
            return False
        if len(normalized_texts) != len(set(normalized_texts)):
            return False

        answer = next(o.text for o in candidate.options if o.option_id == candidate.correct_option_id)
        answer_key = self._normalize(answer)
        # Avoid clues accidentally naming their own answer. Short tokens and
        # numbers can coincide with grammatical words/counts without a reveal.
        if len(answer_key) >= 3 and not answer_key.isdecimal() and re.search(
            r"(?<!\w)" + re.escape(answer_key) + r"(?!\w)", self._normalize(candidate.text)
        ):
            return False
        if not set(candidate.focus_player_ids).issubset(dataset.player_ids):
            return False

        if not set(candidate.involved_player_ids).issubset(dataset.player_ids):
            return False
        if not set(candidate.source_field_keys).issubset(dataset.field_keys):
            return False

        return True

    @staticmethod
    def _normalize(value: str) -> str:
        return str(normalize(value))
