"""Structural candidate validation (MASTER_SPEC.md §12.3)."""

from app.domain.questions.candidate import QuestionCandidate
from app.domain.questions.dataset import ProfileDataset


class QuestionValidator:
    """Reject candidates that violate approved correctness and safety rules.

    Option-count and maximum-length checks remain absent until their deferred
    bounds are approved. Rule-specific semantic correctness is added alongside
    concrete rules; this validator enforces the shared structural invariants.
    """

    def is_valid(
        self,
        candidate: QuestionCandidate,
        dataset: ProfileDataset,
    ) -> bool:
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

        if not set(candidate.involved_player_ids).issubset(dataset.player_ids):
            return False
        if not set(candidate.source_field_keys).issubset(dataset.field_keys):
            return False

        return True

    @staticmethod
    def _normalize(value: str) -> str:
        return value.strip().casefold()
