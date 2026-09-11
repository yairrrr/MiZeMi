"""Distinct, bounded reasoning families over consented, schema-known fields.

A rule proves its solution before constructing options. Missing values never
satisfy inequality. All loops have classroom bounds; each family emits <=80
candidates and considers <=6,000 clue combinations. No IO or AI.
"""

from collections import Counter
from itertools import combinations, islice, permutations
from random import Random

from app.domain.questions.candidate import QuestionCandidate
from app.domain.questions.language import label, say
from app.domain.questions.question import Difficulty
from app.domain.questions.rule import QuestionRule
from app.domain.questions.rules import _build_options

MAX_CANDIDATES = 80
MAX_COMBINATIONS = 6000


def unique_extreme(values, *, smallest=False):
    if len(values) < 2:
        return None
    target = (min if smallest else max)(values.values())
    winners = [key for key, value in values.items() if value == target]
    return winners[0] if len(winners) == 1 else None


class IndexedRule(QuestionRule):
    rule_id = 'indexed'
    difficulty = Difficulty.MEDIUM

    def generate(self, dataset, rng: Random):
        if dataset.player_count < 3:
            return ()
        return tuple(islice(self.candidates(dataset.index, rng), MAX_CANDIDATES))

    def text(self, ix, en, he, **values):
        return say(ix.dataset.language, en, he, **values)

    def field(self, ix, field):
        return label(field, ix.dataset.language)

    def fields(self, ix, fields):
        return ', '.join(self.field(ix, f) for f in fields)

    def make(self, ix, rng, text, answer, choices, fields, people, *, key=(), focus=()):
        # Real alternatives only; identical display names/text are rejected by
        # the common validator rather than being secretly treated as distinct.
        distractors = [str(v) for v in choices if v != answer]
        if not distractors:
            return
        distractors = rng.sample(distractors, min(3, len(distractors)))
        options, correct = _build_options(str(answer), distractors, rng)
        yield QuestionCandidate(
            text, options, correct, self.rule_id, tuple(fields), tuple(people),
            difficulty=self.difficulty, semantic_key=tuple(str(v) for v in key),
            focus_player_ids=tuple(focus),
        )

    def person(self, ix, rng, text, answer, eligible, fields, *, key=(), focus=()):
        yield from self.make(ix, rng, text, ix.name(answer), [ix.name(p) for p in eligible], fields,
                             (answer, *(p for p in eligible if p != answer)), key=key,
                             focus=focus or (answer,))

    def number(self, ix, rng, text, answer, maximum, fields, people, *, key=(), focus=()):
        nearby = [answer, answer - 1, answer + 1, answer - 2, answer + 2]
        choices = [n for n in nearby if 0 <= n <= maximum][:4]
        yield from self.make(ix, rng, text, answer, choices, fields, people, key=key, focus=focus)

    def comparison_fields(self, ix):
        return self.fields(ix, ix.common_fields)


class MultiAttributeRule(IndexedRule):
    """A/O/F: two individually ambiguous values have one intersection."""
    rule_id = 'multi_attribute'

    def candidates(self, ix, rng):
        for fields in combinations(ix.fields, 2):
            eligible = ix.complete(*fields)
            for pid in eligible:
                if any(len(ix.groups[f][ix.keys[pid][f]]) < 2 for f in fields):
                    continue
                matches = [p for p in eligible if all(ix.equal(p, pid, f) for f in fields)]
                if matches != [pid]:
                    continue
                clues = '; '.join(f'{self.field(ix, f)}: "{ix.rows[pid][f]}"' for f in fields)
                text = self.text(ix, 'Who matches both clues — {clues}?', 'מי מתאים לשני הרמזים — {clues}?', clues=clues)
                yield from self.person(ix, rng, text, pid, eligible, fields, key=('clues', *fields, pid))


class ProfileFingerprintRule(IndexedRule):
    """P: three necessary clues; every pair still has multiple matches."""
    rule_id = 'profile_fingerprint'
    difficulty = Difficulty.HARD

    def candidates(self, ix, rng):
        for fields in combinations(ix.fields, 3):
            eligible = ix.complete(*fields)
            for pid in eligible:
                if any(sum(all(ix.equal(p, pid, f) for f in subset) for p in eligible) < 2
                       for subset in combinations(fields, 2)):
                    continue
                if sum(all(ix.equal(p, pid, f) for f in fields) for p in eligible) != 1:
                    continue
                clues = '; '.join(f'{self.field(ix, f)}: "{ix.rows[pid][f]}"' for f in fields)
                text = self.text(ix, 'Who am I? {clues}.', 'מי אני? {clues}.', clues=clues)
                yield from self.person(ix, rng, text, pid, eligible, fields, key=('clues', *fields, pid))


class MostSimilarPairRule(IndexedRule):
    rule_id = 'most_similar_pair'

    def candidates(self, ix, rng):
        winner = unique_extreme(ix.overlaps)
        if winner is not None and ix.overlaps[winner] >= 2:
            text = self.text(ix, 'Which pair has the most in common when comparing {fields}?',
                             'לאיזה זוג יש הכי הרבה במשותף כשמשווים {fields}?', fields=self.comparison_fields(ix))
            yield from self.make(ix, rng, text, ix.pair_name(winner), [ix.pair_name(p) for p in ix.pairs],
                                 ix.common_fields, ix.ids, focus=winner)


class SimilarToPlayerRule(IndexedRule):
    rule_id = 'similar_to_player'

    def candidates(self, ix, rng):
        if not ix.overlaps:
            return
        for anchor in ix.ids:
            scores = {p: ix.overlap(p, anchor) for p in ix.ids if p != anchor}
            winner = unique_extreme(scores)
            if winner is None or scores[winner] < 1:
                continue
            text = self.text(ix, 'Who has the most in common with {name} when comparing {fields}?',
                             'למי יש הכי הרבה במשותף עם {name} כשמשווים {fields}?',
                             name=ix.name(anchor), fields=self.comparison_fields(ix))
            yield from self.person(ix, rng, text, winner, tuple(scores), ix.common_fields, focus=(anchor, winner))


class OddOneOutRule(IndexedRule):
    """D: among four displayed people exactly three share a named field."""
    rule_id = 'odd_one_out'

    def candidates(self, ix, rng):
        for field in ix.fields:
            for value, holders in ix.groups[field].items():
                if len(holders) < 3:
                    continue
                others = [p for p in ix.complete(field) if ix.keys[p][field] != value]
                for odd in others:
                    group = (*holders[:3], odd)
                    text = self.text(ix, 'Three of these players chose the same {field}. Who chose something different?',
                                     'שלושה מהמשתתפים הבאים נתנו תשובה זהה לגבי {field}. מי בחר משהו אחר?', field=self.field(ix, field))
                    yield from self.person(ix, rng, text, odd, group, (field,), key=('exception', field, *sorted(group)))


class FilteredModeRule(IndexedRule):
    """E/M: a proper subgroup (>=3 complete rows), strict repeated mode."""
    rule_id = 'filtered_mode'
    difficulty = Difficulty.HARD

    def candidates(self, ix, rng):
        for condition, field in permutations(ix.fields, 2):
            for value, holders in ix.groups[condition].items():
                if not 3 <= len(holders) < len(ix.ids) or any(field not in ix.keys[p] for p in holders):
                    continue
                counts = Counter(ix.keys[p][field] for p in holders)
                winner = unique_extreme(counts)
                if winner is None or counts[winner] < 2:
                    continue
                text = self.text(ix, 'Among players whose {condition} is "{value}", what is the most common {field}?',
                                 'מבין המשתתפים שבחרו "{value}" לגבי {condition}, מה הכי נפוץ אצלם לגבי {field}?',
                                 condition=self.field(ix, condition), value=ix.displays[condition][value], field=self.field(ix, field))
                yield from self.make(ix, rng, text, ix.displays[field][winner], [ix.displays[field][v] for v in counts],
                                     (condition, field), holders, key=('filtered_mode', condition, value, field))


class SharedReferenceRule(IndexedRule):
    """F: a unique person shares two explicitly named fields with an anchor."""
    rule_id = 'shared_reference'

    def candidates(self, ix, rng):
        for fields in combinations(ix.fields, 2):
            eligible = ix.complete(*fields)
            for anchor in eligible:
                winners = [p for p in eligible if p != anchor and all(ix.equal(p, anchor, f) for f in fields)]
                if len(winners) != 1 or len(eligible) < 3:
                    continue
                text = self.text(ix, 'Who shares both {fields} with {name}?',
                                 'מי בחר/ה בדיוק כמו {name} גם לגבי {fields}?',
                                 fields=self.fields(ix, fields), name=ix.name(anchor))
                yield from self.person(ix, rng, text, winners[0], [p for p in eligible if p != anchor], fields,
                                       focus=(anchor, winners[0]))


class GroupComparisonRule(IndexedRule):
    rule_id = 'group_comparison'
    difficulty = Difficulty.EASY

    def candidates(self, ix, rng):
        for field in ix.fields:
            for a, b in islice(combinations(ix.groups[field], 2), MAX_COMBINATIONS):
                if len(ix.groups[field][a]) == len(ix.groups[field][b]):
                    continue
                winner = a if len(ix.groups[field][a]) > len(ix.groups[field][b]) else b
                # Values appear as options, never alongside their counts.
                text = self.text(ix, 'Which of these two {field} choices was shared by more players?',
                                 'איזו משתי הבחירות לגבי {field} משותפת ליותר משתתפים?', field=self.field(ix, field))
                yield from self.make(ix, rng, text, ix.displays[field][winner], [ix.displays[field][v] for v in (a, b)],
                                     (field,), (*ix.groups[field][a], *ix.groups[field][b]), key=('group_comparison', field))


class LeastCommonValueRule(IndexedRule):
    rule_id = 'least_common_value'

    def candidates(self, ix, rng):
        for field in ix.fields:
            groups = ix.groups[field]
            winner = unique_extreme({v: len(p) for v, p in groups.items()}, smallest=True)
            if winner is None or len(ix.complete(field)) < 4:
                continue
            text = self.text(ix, 'Which shared {field} choice belongs to the smallest group?',
                             'איזו בחירה לגבי {field} משותפת לקבוצה הקטנה ביותר?', field=self.field(ix, field))
            yield from self.make(ix, rng, text, ix.displays[field][winner], list(ix.displays[field].values()),
                                 (field,), ix.complete(field), key=('least_common', field))


class MinorityFractionRule(IndexedRule):
    rule_id = 'minority_fraction'

    def candidates(self, ix, rng):
        for field in ix.fields:
            participants = ix.complete(field)
            if len(participants) < 5:
                continue
            small = [v for v, p in ix.groups[field].items() if len(p) * 4 < len(participants)]
            if len(small) != 1:
                continue
            text = self.text(ix, 'Which {field} choice was shared by fewer than a quarter of those who answered?',
                             'איזו בחירה לגבי {field} משותפת לפחות מרבע מהמשתתפים שענו?', field=self.field(ix, field))
            yield from self.make(ix, rng, text, ix.displays[field][small[0]], list(ix.displays[field].values()),
                                 (field,), participants, key=('least_common', field))


class AttributeChainRule(IndexedRule):
    rule_id = 'attribute_chain'
    difficulty = Difficulty.HARD

    def candidates(self, ix, rng):
        # Two equality clues from different people, plus a known inequality
        # against both. Set intersections avoid enumerating player triples.
        checks = 0
        for f, g, h in permutations(ix.fields, 3):
            eligible = ix.complete(f, g, h)
            if len(eligible) < 4:
                continue
            for a, b in permutations(eligible, 2):
                checks += 1
                if checks > MAX_COMBINATIONS:
                    return
                pool = [p for p in eligible if p not in (a, b)]
                winners = [p for p in pool if ix.equal(p, a, f) and ix.equal(p, b, g)
                           and ix.different(p, a, h) and ix.different(p, b, h)]
                if len(winners) != 1:
                    continue
                # Both equality anchors must actually narrow the pool.
                if not any(ix.equal(p, a, f) and p != winners[0] for p in pool):
                    continue
                text = self.text(ix,
                    'Who shares {f} with {a} and {g} with {b}, but has a different {h} from both?',
                    'מי דומה ל{a} לגבי {f}, דומה ל{b} לגבי {g}, אבל שונה משניהם לגבי {h}?',
                    f=self.field(ix, f), g=self.field(ix, g), h=self.field(ix, h), a=ix.name(a), b=ix.name(b))
                yield from self.person(ix, rng, text, winners[0], pool, (f, g, h), focus=(winners[0], a, b))


class CrossPersonRule(IndexedRule):
    rule_id = 'cross_person_similarity'
    difficulty = Difficulty.HARD

    def candidates(self, ix, rng):
        if not ix.overlaps or len(ix.ids) < 4:
            return
        for a, b in islice(ix.pairs, MAX_COMBINATIONS):
            scores = {p: ix.overlap(p, a) + ix.overlap(p, b) for p in ix.ids if p not in (a, b)}
            winner = unique_extreme(scores)
            if winner is None or not ix.overlap(winner, a) or not ix.overlap(winner, b):
                continue
            text = self.text(ix,
                'Across {fields}, who has the highest total of matches with {a} plus matches with {b}? Count a match with each person separately.',
                'כשמשווים {fields}, למי יש הכי הרבה במשותף עם {a} ועם {b} יחד? סופרים כל תשובה משותפת עם כל אחד מהם בנפרד.',
                fields=self.comparison_fields(ix), a=ix.name(a), b=ix.name(b))
            yield from self.person(ix, rng, text, winner, tuple(scores), ix.common_fields, focus=(winner, a, b))


class CommonalityCountRule(IndexedRule):
    rule_id = 'commonality_count'

    def candidates(self, ix, rng):
        for (a, b), count in ix.overlaps.items():
            text = self.text(ix, 'How many answers do {a} and {b} have in common when comparing {fields}?',
                             'בכמה תשובות {a} ו{b} דומים כשמשווים {fields}?',
                             a=ix.name(a), b=ix.name(b), fields=self.comparison_fields(ix))
            yield from self.number(ix, rng, text, count, len(ix.common_fields), ix.common_fields, (a, b),
                                   key=('commonality_count', a, b), focus=(a, b))


class ExclusionRule(IndexedRule):
    rule_id = 'group_exception'

    def candidates(self, ix, rng):
        for field in ix.fields:
            eligible = ix.complete(field)
            if len(eligible) < 4:
                continue
            for value, holders in ix.groups[field].items():
                if len(holders) != len(eligible) - 1:
                    continue
                odd = next(p for p in eligible if p not in holders)
                text = self.text(ix, 'Among players who shared their {field}, everyone but one gave the same answer. Who is the exception?',
                                 'מבין מי ששיתפו {field}, כולם חוץ מאחד נתנו אותה תשובה. מי יוצא/ת הדופן?', field=self.field(ix, field))
                yield from self.person(ix, rng, text, odd, eligible, (field,), key=('exception', field, *sorted(eligible)))


class ConditionalYoungestRule(IndexedRule):
    rule_id = 'conditional_youngest'
    difficulty = Difficulty.HARD

    def candidates(self, ix, rng):
        for field in ix.fields:
            for value, holders in ix.groups[field].items():
                if not 3 <= len(holders) < len(ix.ids) or any(type(ix.rows[p].get('age')) is not int for p in holders):
                    continue
                winner = unique_extreme({p: ix.rows[p]['age'] for p in holders}, smallest=True)
                if winner is None:
                    continue
                text = self.text(ix, 'Who is youngest among players whose {field} is "{value}"?',
                                 'מי הצעיר/ה ביותר מבין המשתתפים שבחרו "{value}" לגבי {field}?',
                                 field=self.field(ix, field), value=ix.displays[field][value])
                yield from self.person(ix, rng, text, winner, holders, (field, 'age'))


class AgeRankingRule(IndexedRule):
    rule_id = 'age_ranking'
    difficulty = Difficulty.EASY

    def candidates(self, ix, rng):
        ages = {p: ix.rows[p]['age'] for p in ix.complete('age') if type(ix.rows[p]['age']) is int}
        winner = unique_extreme(ages)
        if winner is not None and len(ages) >= 3:
            text = self.text(ix, 'Who is oldest among the players who shared their age?',
                             'מי המבוגר ביותר מבין המשתתפים ששיתפו את הגיל שלהם?')
            yield from self.person(ix, rng, text, winner, tuple(ages), ('age',))


class SecondLargestGroupRule(IndexedRule):
    rule_id = 'second_largest_group'

    def candidates(self, ix, rng):
        for field in ix.fields:
            groups = ix.groups[field]
            if len(groups) < 3:
                continue
            ranked = sorted(groups, key=lambda v: -len(groups[v]))
            count = len(groups[ranked[1]])
            if sum(len(p) == count for p in groups.values()) != 1 or len(groups[ranked[0]]) == count:
                continue
            text = self.text(ix, 'Which {field} choice has the second-largest group?',
                             'איזו בחירה לגבי {field} שייכת לקבוצה השנייה בגודלה?', field=self.field(ix, field))
            yield from self.make(ix, rng, text, ix.displays[field][ranked[1]], list(ix.displays[field].values()),
                                 (field,), ix.complete(field))


class PairMatchRule(IndexedRule):
    rule_id = 'pair_match'
    difficulty = Difficulty.HARD

    def candidates(self, ix, rng):
        for fields in combinations(ix.fields, 2):
            eligible = ix.complete(*fields)
            pairs = tuple(combinations(eligible, 2))
            winners = [pair for pair in pairs if all(ix.equal(*pair, f) for f in fields)]
            if len(winners) != 1 or len(pairs) < 3:
                continue
            text = self.text(ix, 'Which pair gave matching answers for both {fields}?',
                             'איזה זוג נתנו תשובות זהות גם לגבי {fields}?', fields=self.fields(ix, fields))
            yield from self.make(ix, rng, text, ix.pair_name(winners[0]), [ix.pair_name(p) for p in pairs], fields,
                                 eligible, focus=winners[0])


class SharedButDifferentRule(IndexedRule):
    rule_id = 'shared_but_different'

    def candidates(self, ix, rng):
        for f, g in permutations(ix.fields, 2):
            eligible = ix.complete(f, g)
            for anchor in eligible:
                pool = [p for p in eligible if p != anchor]
                winners = [p for p in pool if ix.equal(p, anchor, f) and ix.different(p, anchor, g)]
                if len(winners) != 1:
                    continue
                text = self.text(ix, 'Who shares {f} with {name}, but has a different {g}?',
                                 'מי דומה ל{name} לגבי {f}, אבל שונה לגבי {g}?',
                                 f=self.field(ix, f), g=self.field(ix, g), name=ix.name(anchor))
                yield from self.person(ix, rng, text, winners[0], pool, (f, g), focus=(anchor, winners[0]))


class CategoryCoverageRule(IndexedRule):
    """S/T: count distinct values of a second dimension, not group size."""
    rule_id = 'category_coverage'
    difficulty = Difficulty.HARD

    def candidates(self, ix, rng):
        for group, field in permutations(ix.fields, 2):
            if any(field not in ix.keys[p] for p in ix.complete(group)):
                continue
            variety = {v: len({ix.keys[p][field] for p in holders}) for v, holders in ix.groups[group].items()}
            winner = unique_extreme(variety)
            if winner is None or variety[winner] < 2 or len(ix.complete(group, field)) < 4:
                continue
            text = self.text(ix, 'Which group sharing the same {group} has the widest variety of {field} choices?',
                             'באיזו קבוצה עם {group} משותף יש את המגוון הגדול ביותר של בחירות לגבי {field}?',
                             group=self.field(ix, group), field=self.field(ix, field))
            yield from self.make(ix, rng, text, ix.displays[group][winner], list(ix.displays[group].values()),
                                 (group, field), ix.complete(group, field), key=('coverage', group, field))


class UniqueConnectionRule(IndexedRule):
    rule_id = 'unique_connection'
    difficulty = Difficulty.HARD

    def candidates(self, ix, rng):
        if not ix.overlaps or len(ix.ids) < 4:
            return
        winners = [p for p in ix.ids if all(ix.overlap(p, q) > 0 for q in ix.ids if q != p)]
        if len(winners) != 1:
            return
        text = self.text(ix, 'When comparing {fields}, who has at least one answer in common with every other player?',
                         'כשמשווים {fields}, למי יש לפחות תשובה אחת במשותף עם כל אחד מהמשתתפים האחרים?', fields=self.comparison_fields(ix))
        yield from self.person(ix, rng, text, winners[0], ix.ids, ix.common_fields)


class TwoStepEliminationRule(IndexedRule):
    rule_id = 'two_step_elimination'

    def candidates(self, ix, rng):
        checks = 0
        for f, g in permutations(ix.fields, 2):
            for value, holders in ix.groups[f].items():
                if len(holders) < 2 or any(g not in ix.keys[p] for p in holders):
                    continue
                for excluded in ix.groups[g]:
                    checks += 1
                    if checks > MAX_COMBINATIONS:
                        return
                    winners = [p for p in holders if ix.keys[p][g] != excluded]
                    if len(winners) != 1:
                        continue
                    text = self.text(ix, 'Who chose "{value}" for {f}, but did not choose "{excluded}" for {g}?',
                                     'מי בחר "{value}" לגבי {f}, אבל בחר משהו אחר מ"{excluded}" לגבי {g}?',
                                     value=ix.displays[f][value], f=self.field(ix, f), excluded=ix.displays[g][excluded], g=self.field(ix, g))
                    yield from self.person(ix, rng, text, winners[0], ix.complete(f, g), (f, g))


class ClosestAgePairRule(IndexedRule):
    """Original family: a unique minimum absolute numeric distance."""
    rule_id = 'closest_age_pair'

    def candidates(self, ix, rng):
        people = [p for p in ix.complete('age') if type(ix.rows[p]['age']) is int]
        if len(people) < 3:
            return
        gaps = {pair: abs(ix.rows[pair[0]]['age'] - ix.rows[pair[1]]['age']) for pair in combinations(people, 2)}
        winner = unique_extreme(gaps, smallest=True)
        if winner is None:
            return
        text = self.text(ix, 'Which pair has the smallest age difference among players who shared their age?',
                         'לאיזה זוג יש הפרש הגילים הקטן ביותר מבין המשתתפים ששיתפו גיל?')
        yield from self.make(ix, rng, text, ix.pair_name(winner), [ix.pair_name(p) for p in gaps], ('age',), people, focus=winner)


class BalancedSplitRule(IndexedRule):
    """Original family: identify a dimension that partitions the group equally."""
    rule_id = 'balanced_split'

    def candidates(self, ix, rng):
        if len(ix.ids) < 4 or len(ix.ids) % 2:
            return
        eligible = ix.common_fields
        winners = [f for f in eligible if len(ix.groups[f]) == 2 and all(len(p) * 2 == len(ix.ids) for p in ix.groups[f].values())]
        if len(winners) != 1 or len(eligible) < 2:
            return
        text = self.text(ix, 'Which topic divides the players into exactly two equally large groups?',
                         'איזה נושא מחלק את המשתתפים בדיוק לשתי קבוצות שוות בגודלן?')
        yield from self.make(ix, rng, text, self.field(ix, winners[0]), [self.field(ix, f) for f in eligible], eligible, ix.ids)


class RarestProfileRule(IndexedRule):
    """Original family: minimize total overlap, counting repeated matches."""
    rule_id = 'rarest_profile'
    difficulty = Difficulty.HARD

    def candidates(self, ix, rng):
        if not ix.overlaps or len(ix.ids) < 4:
            return
        totals = {p: sum(ix.overlap(p, q) for q in ix.ids if q != p) for p in ix.ids}
        winner = unique_extreme(totals, smallest=True)
        if winner is None:
            return
        text = self.text(ix,
            'When comparing {fields}, who has the fewest answers in common with everyone else? Count each shared answer with each other player separately.',
            'כשמשווים {fields}, למי יש הכי מעט במשותף עם שאר הקבוצה? כל תשובה משותפת עם כל משתתף אחר נספרת בנפרד.',
            fields=self.comparison_fields(ix))
        yield from self.person(ix, rng, text, winner, ix.ids, ix.common_fields)


class ExactOverlapPairRule(IndexedRule):
    rule_id = 'exact_overlap_pair'
    difficulty = Difficulty.HARD

    def candidates(self, ix, rng):
        frequencies = Counter(ix.overlaps.values())
        for pair, count in ix.overlaps.items():
            if count < 1 or frequencies[count] != 1:
                continue
            text = self.text(ix, 'When comparing {fields}, which pair has exactly {count} answers in common?',
                             'כשמשווים {fields}, לאיזה זוג יש בדיוק {count} תשובות משותפות?',
                             fields=self.comparison_fields(ix), count=count)
            yield from self.make(ix, rng, text, ix.pair_name(pair), [ix.pair_name(p) for p in ix.pairs],
                                 ix.common_fields, ix.ids, focus=pair)


def advanced_rules():
    return tuple(cls() for cls in (
        MultiAttributeRule, ProfileFingerprintRule, MostSimilarPairRule, SimilarToPlayerRule,
        OddOneOutRule, FilteredModeRule, SharedReferenceRule, GroupComparisonRule,
        LeastCommonValueRule, MinorityFractionRule, AttributeChainRule, CrossPersonRule,
        CommonalityCountRule, ExclusionRule, ConditionalYoungestRule, AgeRankingRule,
        SecondLargestGroupRule, PairMatchRule, SharedButDifferentRule, CategoryCoverageRule,
        UniqueConnectionRule, TwoStepEliminationRule, ClosestAgePairRule, BalancedSplitRule,
        RarestProfileRule, ExactOverlapPairRule,
    ))
