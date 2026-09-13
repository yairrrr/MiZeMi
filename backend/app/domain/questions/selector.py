"""Deterministic progressive selection (MASTER_SPEC.md §12).

Target easy/medium/hard bands, then balance rule use, recent repeated subjects
and fields, total field use, quality and participant spread. Normalized text
and rule-provided semantic keys suppress equivalent questions across families;
legacy rules fall back to a rule/field/subject signature. All comparisons use
local metadata and text, with no AI or external similarity service.
"""

from collections.abc import Sequence

from app.domain.questions.candidate import QuestionCandidate
from app.domain.questions.question import Difficulty
from app.domain.questions.language import normalize


class QuestionSelector:
    def __init__(self, *, group_first: bool = False):
        self.group_first = group_first

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
        seen_signatures: set[tuple] = set()
        seen_memberships: set[tuple] = set()
        rule_pick_counts: dict[str, int] = {}
        field_pick_counts: dict[str, int] = {}
        player_feature_counts: dict[str, int] = {}

        mix_counts = {}
        person_count = 0
        mix_weights = {'simple': .30, 'semantic': .35, 'geographic': .20, 'other': .15}
        caps = {'category_coverage': max(1, question_count // 20), 'age_ranking': 1, 'most_common_value': max(1, question_count // 10), 'group_diversity': max(2, question_count // 10), 'unique_value': max(1, question_count // 10), 'value_count': max(2, question_count // 10),
                'group_different_pair': max(1, question_count // 20), 'group_scoped_count': max(1, question_count // 10),
                'group_count': max(2, question_count // 4), 'group_mode': max(2, question_count // 4)}
        metadata = {id(c): dict(c.metadata) for c, _ in remaining}
        def eligible(c):
            if not self.group_first: return True
            if metadata[id(c)].get('membership_signature') in seen_memberships:
                return False
            if rule_pick_counts.get(c.source_rule_id, 0) >= caps.get(c.source_rule_id, max(2, question_count // 6)):
                return False
            return not metadata[id(c)].get('person_answer') or person_count < max(2, question_count // 4)

        levels = {Difficulty.EASY: 0, Difficulty.MEDIUM: 1, Difficulty.HARD: 2}
        while remaining and len(selected) < question_count:
            fraction = len(selected) / question_count
            target = 0 if fraction < 0.25 else 1 if fraction < 0.7 else 2
            def pick_key(entry: tuple[QuestionCandidate, float]):
                candidate, score = entry
                mix = metadata[id(candidate)].get('mix', 'other')
                deficit = mix_weights.get(mix, 0) * (len(selected) + 1) - mix_counts.get(mix, 0)
                return (
                    -round(deficit, 6) if self.group_first else 0,
                    int(candidate.source_rule_id in ('unique_value','value_count','group_scoped_count')) if self.group_first else 0,
                    abs(levels[candidate.difficulty] - target),
                    rule_pick_counts.get(candidate.source_rule_id, 0),
                    sum(bool(set(candidate.focus_player_ids) & set(previous.focus_player_ids))
                        and bool(set(candidate.source_field_keys) & set(previous.source_field_keys))
                        for previous in selected[-2:]),
                    sum(
                        field_pick_counts.get(field_key, 0)
                        for field_key in set(candidate.source_field_keys)
                    ),
                    -int(dict(candidate.metadata).get("reasoning_hops", 0)),
                    -score,
                    sum(
                        player_feature_counts.get(pid, 0)
                        for pid in candidate.focus_player_ids or candidate.involved_player_ids
                    ),
                    candidate.text,
                )

            # Skip duplicates before ranking; never burn repeated minimum
            # searches over thousands of already-used semantic signatures.
            remaining = [(c, score) for c, score in remaining if eligible(c) and str(normalize(c.text)) not in seen_texts
                         and (c.semantic_key or (c.source_rule_id, c.source_field_keys,
                              c.involved_player_ids[0] if c.involved_player_ids else None)) not in seen_signatures]
            if not remaining:
                break
            best = min(remaining, key=pick_key)
            remaining.remove(best)
            candidate, _ = best

            text_key = str(normalize(candidate.text))
            signature = candidate.semantic_key or (
                candidate.source_rule_id,
                candidate.source_field_keys,
                candidate.involved_player_ids[0] if candidate.involved_player_ids else None,
            )
            if text_key in seen_texts or signature in seen_signatures:
                continue

            selected.append(candidate)
            mix = metadata[id(candidate)].get('mix', 'other')
            mix_counts[mix] = mix_counts.get(mix, 0) + 1
            person_count += bool(metadata[id(candidate)].get('person_answer'))
            seen_texts.add(text_key)
            seen_signatures.add(signature)
            membership=metadata[id(candidate)].get('membership_signature')
            if membership is not None: seen_memberships.add(membership)
            rule_pick_counts[candidate.source_rule_id] = (
                rule_pick_counts.get(candidate.source_rule_id, 0) + 1
            )
            for field_key in set(candidate.source_field_keys):
                field_pick_counts[field_key] = field_pick_counts.get(field_key, 0) + 1
            for pid in candidate.focus_player_ids or candidate.involved_player_ids:
                player_feature_counts[pid] = player_feature_counts.get(pid, 0) + 1

        if self.group_first:
            selected.sort(key=lambda c: levels[c.difficulty])
        return tuple(selected)
