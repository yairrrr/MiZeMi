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


class DiscoveryValueScorer:
    """Information value of a candidate on a zero-to-one scale, for group-first games.

    A question is worth more when answering it requires more than one lookup,
    rests on more of the group, and states a clearer result:

    * 0.40 × reasoning depth — 1 hop is a direct lookup ("who chose pizza?");
      2 resolves and classifies answers ("how many chose Italian food?");
      3 also aggregates and compares ("which cuisine leads?"); 4 does that
      inside a subgroup defined by another domain.
    * 0.30 × share of the group whose answers the question depends on.
    * 0.20 × how informative the result is, as recorded by the rule: a count
      that splits the group, a close but decided race, a leader with a real
      share of the group. Facts without that metadata count as 0.5.
    * 0.10 × recognition coverage of the dimensions involved (direct facts 1.0).

    Deterministic and bounded; no weight dominates so much that a weak
    discovery outranks a strong simple question on depth alone.
    """

    DEPTH = {1: 0.25, 2: 0.55, 3: 0.80, 4: 1.0}

    def score(self, candidate: QuestionCandidate, dataset: ProfileDataset) -> float:
        if dataset.player_count == 0:
            return 0.0
        metadata = dict(candidate.metadata)
        hops = min(max(int(metadata.get("reasoning_hops", 1)), 1), 4)
        represented = len(set(candidate.involved_player_ids) & set(dataset.player_ids)) / dataset.player_count
        interest = min(max(float(metadata.get("interest", 0.5)), 0.0), 1.0)
        coverage = min(max(float(metadata.get("coverage", 1.0)), 0.0), 1.0)
        return round(0.40 * self.DEPTH[hops] + 0.30 * represented + 0.20 * interest + 0.10 * coverage, 6)
