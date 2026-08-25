"""Deterministic candidate quality scoring (MASTER_SPEC.md §12.4)."""

from app.domain.questions.candidate import QuestionCandidate
from app.domain.questions.dataset import ProfileDataset


class QuestionQualityScorer:
    """Score candidate group coverage on a normalized zero-to-one scale.

    Coverage is the only approved initial signal. Additional signals and
    weights require their own design decision once concrete rules expose the
    necessary metadata.
    """

    def score(
        self,
        candidate: QuestionCandidate,
        dataset: ProfileDataset,
    ) -> float:
        if dataset.player_count == 0:
            return 0.0

        current_player_ids = set(dataset.player_ids)
        covered_player_ids = set(candidate.involved_player_ids) & current_player_ids
        return len(covered_player_ids) / dataset.player_count
