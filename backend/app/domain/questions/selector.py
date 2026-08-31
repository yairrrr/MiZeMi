"""Deterministic candidate selection (MASTER_SPEC.md §12.5).

Greedy selection: every pick minimizes, in order — how often the candidate's
rule was already picked (rule diversity), how often its source fields were
already used (field diversity), negative quality score, how often its involved
players were already featured (player spread), then question text as the final
tiebreak. Exact normalized-text duplicates and repeats of
the §12.5 near-duplicate signature (rule_id, source_field_keys, subject
player — the first involved player, or None) are never picked. All
comparisons are deterministic local metadata/text — no semantic similarity.
"""

from collections.abc import Sequence

from app.domain.questions.candidate import QuestionCandidate


class QuestionSelector:
    def select(
        self,
        scored_candidates: Sequence[tuple[QuestionCandidate, float]],
        *,
        question_count: int,
    ) -> tuple[QuestionCandidate, ...]:
        """Pick up to ``question_count`` candidates; fewer if fewer are selectable."""
        if question_count < 1:
            raise ValueError("question_count must be at least 1")

        remaining = list(scored_candidates)
        selected: list[QuestionCandidate] = []
        seen_texts: set[str] = set()
        seen_signatures: set[tuple[str, tuple[str, ...], str | None]] = set()
        rule_pick_counts: dict[str, int] = {}
        field_pick_counts: dict[str, int] = {}
        player_feature_counts: dict[str, int] = {}

        while remaining and len(selected) < question_count:
            def pick_key(entry: tuple[QuestionCandidate, float]):
                candidate, score = entry
                return (
                    rule_pick_counts.get(candidate.source_rule_id, 0),
                    sum(
                        field_pick_counts.get(field_key, 0)
                        for field_key in set(candidate.source_field_keys)
                    ),
                    -score,
                    sum(
                        player_feature_counts.get(pid, 0)
                        for pid in candidate.involved_player_ids
                    ),
                    candidate.text,
                )

            best = min(remaining, key=pick_key)
            remaining.remove(best)
            candidate, _ = best

            text_key = candidate.text.strip().casefold()
            signature = (
                candidate.source_rule_id,
                candidate.source_field_keys,
                candidate.involved_player_ids[0] if candidate.involved_player_ids else None,
            )
            if text_key in seen_texts or signature in seen_signatures:
                continue

            selected.append(candidate)
            seen_texts.add(text_key)
            seen_signatures.add(signature)
            rule_pick_counts[candidate.source_rule_id] = (
                rule_pick_counts.get(candidate.source_rule_id, 0) + 1
            )
            for field_key in set(candidate.source_field_keys):
                field_pick_counts[field_key] = field_pick_counts.get(field_key, 0) + 1
            for pid in candidate.involved_player_ids:
                player_feature_counts[pid] = player_feature_counts.get(pid, 0) + 1

        return tuple(selected)
