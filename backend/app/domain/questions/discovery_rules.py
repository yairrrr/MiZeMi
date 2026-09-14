"""Production discovery families: questions about what the group's answers reveal.

Each family is one reasoning operation over the category-first group summaries
(``group_summary.py``) — count, majority, comparison, unique member, diversity,
minority, distribution, geography and cross-domain subgroups — applied to every
compatible dimension. Domains differ only in wording. A family proves its
answer (a unique winner, a lead no unknown answer could overturn, enough
recognized answers) before it renders options. Works, dishes and places are
never the subject of general-knowledge trivia; only the players are.

Candidate metadata is internal selection data and is never sent to clients:
``kind`` (semantic / geographic / cross_domain), ``family``, ``domain`` and
``domains``, ``reasoning_hops``, ``coverage``, ``interest`` (how informative the
result is, in [0, 1]), ``tier``, ``person_answer``, ``answer_key``, for facts about who belongs to
a group, ``membership_signature``, and, for counts and rankings, ``reveals`` and ``needs``.

``reveals`` lists what a question and its explanation disclose about one
dimension — a category's exact count (``('count', key, category)``), that the
count is one (``('one', key, category)``), or that it outranks every category
other than those already named (``('rank', key, category)``). Within a subgroup
the key is the scope, ``'place.region:region.central|food.cuisine'``. ``needs``
lists alternative sets of such facts, any one of which already answers the
question. The selector uses them so that no question is
answered by one shown before it: "which hobby type is most common?" is not
followed by "sport or reading?".
"""

from collections import deque
from itertools import combinations
from random import Random

from app.domain.questions.candidate import QuestionCandidate
from app.domain.questions.discovery_language import (
    INTERSECTIONS,
    SUBGROUP_COMPARISONS,
    SUBGROUP_CONDITIONS,
    SUBGROUP_QUESTIONS,
    TEMPLATES,
    Wording,
    stable_index,
)
from app.domain.questions.group_summary import (
    DIMENSIONS_BY_KEY,
    MEDIA_DIMENSIONS,
    POLICY,
    decisive_leader,
    meaningful_leader,
    summarize,
)
from app.domain.questions.question import Difficulty, QuestionOption
from app.domain.questions.rule import QuestionRule
from app.domain.questions.rules import _build_options
from app.domain.questions.semantic_distractors import NEIGHBORS

MIN_PLAYERS = 3
MAX_CANDIDATES = 60
MAX_PAIRS = 12
TASTES = ('movie.genre', 'food.cuisine', 'hobby.family', 'music.genre', 'artist.genre', 'song.genre')
_OPTION_IDS = 'abcd'
_MIX = {'semantic': 'semantic', 'geographic': 'geographic', 'cross_domain': 'geographic', 'direct': 'simple'}


def number_choices(answer: int, *, uncertain: int, maximum: int, minimum: int = 0) -> list[str]:
    """Nearby wrong counts. Counts that unrecognized answers could still make true are skipped."""
    values = [answer - step for step in (1, 2, 3)] + [answer + uncertain + step for step in (1, 2, 3)]
    allowed = sorted((v for v in values if minimum <= v <= maximum), key=lambda v: (abs(v - answer), v))
    return [str(v) for v in allowed[:3]]


def category_distractors(summary, winner: str, counts: dict[str, int], limit: int = 3) -> list[str]:
    """Wrong options at the compared taxonomy level: rivals, then editorial neighbors, then the rest."""
    order = summary.categories
    rivals = sorted((c for c in summary.represented() if c != winner),
                    key=lambda c: (-counts.get(c, 0), order.index(c)))
    neighbors = [c for c in NEIGHBORS.get(winner, ()) if c in order]
    ranked = dict.fromkeys((*rivals, *neighbors, *order))
    return [c for c in ranked if c != winner][:limit]


def balance(n: int, total: int) -> float:
    """1.0 when a count splits the group in half; near 0 for one person or nearly everyone."""
    return min(n, total - n) / (total / 2) if total else 0.0


def closeness(a: int, b: int) -> float:
    """1.0 for a race decided by one; lower as one side dominates."""
    return 1 - abs(a - b) / (a + b)


def clarity(summary, people) -> float:
    """0.5–1.0: how clearly these people's choices sit in a category.

    "Saw" (horror, crime) is clearer horror evidence than an animated film filed
    under four genres; a discovery about clearly classified choices ranks first.
    """
    people = tuple(people)
    if not people:
        return 0.5
    return 0.5 + 0.5 * sum(1 / len(summary.classified[p]) for p in people) / len(people)


def counts_of(key: str, categories) -> tuple[tuple[str, str, str], ...]:
    return tuple(('count', key, c) for c in categories)


def ranks_of(key: str, categories) -> tuple[tuple[str, str, str], ...]:
    return tuple(('rank', key, c) for c in categories)


def ones_of(key: str, categories) -> tuple[tuple[str, str, str], ...]:
    return tuple(('one', key, c) for c in categories)


def scope(condition_key: str, category: str, target_key: str) -> str:
    """The disclosure key of a target dimension within the subgroup of one category."""
    return f'{condition_key}:{category}|{target_key}'


def pair_membership(first, second, people) -> tuple:
    """One signature for the people in two categories, from either side.

    "Among pop fans, which hobby type?" (sport) and "among sport fans, which
    music?" (pop) are about the same two people, as is "how many chose both?".
    """
    return ('both', tuple(sorted((first.dimension.field, second.dimension.field))), tuple(sorted(people)))


def second_place(summary, winner: str, counts: dict[str, int]) -> str | None:
    """The runner-up a leader's explanation names: only when no tie or unknown answer could change it."""
    runners = sorted((c for c in summary.categories if c != winner and counts.get(c)),
                     key=lambda c: (-counts[c], summary.categories.index(c)))
    if not runners:
        return None
    third = counts[runners[1]] if len(runners) > 1 else 0
    return runners[0] if counts[runners[0]] - third > len(summary.unknown) else None


def leader_interest(winner: int, runner_up: int, total: int) -> float:
    """A leader holding a real share of the group, clearly ahead of the runner-up."""
    return min(1.0, winner / total + (winner - runner_up) / total) if total else 0.0


def option_text(words: Wording, category: str, domain: str, form: str = 'label') -> str:
    text = words.forms(category, domain)[form]
    return text if words.he else text[:1].upper() + text[1:]


def comparable_pairs(summary, counts=None, unknown=None, people=None, limit: int = MAX_PAIRS):
    """Category pairs with a decisive difference and genuinely different members.

    Pairs whose members mostly coincide (a subset, or at least half of the
    smaller group in both) compare one discovery with itself and are skipped,
    and so are races where one side has more than three times the other
    ("11 or 2?" answers itself). ``people`` restricts members to a subgroup;
    ``counts`` must match it.
    """
    counts = counts if counts is not None else {c: summary.count(c) for c in summary.categories}
    unknown = len(summary.unknown) if unknown is None else unknown
    scope = None if people is None else frozenset(people)
    answered = len(scope) if scope is not None else len(summary.recognized)
    smaller_side = 2 if answered >= 8 else 1
    found = []
    for a, b in combinations([c for c in summary.categories if counts[c]], 2):
        na, nb = counts[a], counts[b]
        if (na == nb or max(na, nb) < 2 or na + nb < 3 or abs(na - nb) <= unknown or min(na, nb) < smaller_side
                or max(na, nb) > 3 * min(na, nb)):
            continue
        both = frozenset(summary.members[a]) & frozenset(summary.members[b])
        if scope is not None:
            both &= scope
        if 2 * len(both) >= min(na, nb):
            continue
        found.append((a, b, both))
    order = summary.categories
    found.sort(key=lambda p: (-min(counts[p[0]], counts[p[1]]), abs(counts[p[0]] - counts[p[1]]),
                              order.index(p[0]), order.index(p[1])))
    return found[:limit]


class DiscoveryRule(QuestionRule):
    """Base for families that read the category-first group summary."""

    rule_id = 'discovery'
    family = 'DISCOVERY'
    kind = 'semantic'
    difficulty = Difficulty.MEDIUM
    hops = 3
    tier = 0  # 1 marks supporting families, chosen after the core ones

    def __init__(self, knowledge) -> None:
        self.knowledge = knowledge

    def generate(self, dataset, rng: Random) -> tuple[QuestionCandidate, ...]:
        if dataset.player_count < MIN_PLAYERS:
            return ()
        summary = summarize(dataset, self.knowledge)
        words = Wording(dataset.language, self.knowledge)
        # Do not spend the entire family budget on earlier dimensions and drop
        # artist/song candidates solely because they are generated last. Each
        # finite rule already bounds its categories/pairs; retain at most the
        # family budget per field scope, then round-robin those scopes.
        buckets = {}
        for candidate in self.candidates(summary, words, rng):
            if candidate is not None:
                bucket = buckets.setdefault(candidate.source_field_keys, deque())
                if len(bucket) < MAX_CANDIDATES:
                    bucket.append(candidate)
        found = []
        active = deque(buckets.values())
        while active and len(found) < MAX_CANDIDATES:
            bucket = active.popleft()
            found.append(bucket.popleft())
            if bucket:
                active.append(bucket)
        return tuple(found)

    def candidates(self, summary, words: Wording, rng: Random):
        raise NotImplementedError

    def candidate(self, rng: Random, *, text, answer, dimensions, explanation, fact, involved, answer_key,
                  distractors=(), ordered=None, focus=(), coverage=1.0, interest=0.5, person=False,
                  membership=None, literal=False, reveals=(), needs=()) -> QuestionCandidate | None:
        if ordered is not None:
            options = tuple(QuestionOption(_OPTION_IDS[i], t) for i, t in enumerate(ordered))
            correct = _OPTION_IDS[ordered.index(answer)]
        else:
            pool = [d for d in dict.fromkeys(distractors) if d != answer]
            if not pool:
                return None
            options, correct = _build_options(answer, rng.sample(pool, min(3, len(pool))), rng)
        domains = tuple(dict.fromkeys(DIMENSIONS_BY_KEY[d].selection_domain for d in dimensions))
        # A fact about a listed choice that no grouping changed is a simple, direct
        # question; all such facts share one family so they cannot crowd a game.
        kind, family, hops = self.kind, self.family, self.hops
        if literal:
            kind, family, hops = 'direct', 'DIRECT_CHOICE', 1
        metadata = (('kind', kind), ('family', family), ('domain', domains[-1]),
                    ('domains', ','.join(domains)), ('reasoning_hops', hops),
                    ('coverage', round(coverage, 3)), ('interest', round(min(max(interest, 0.0), 1.0), 3)),
                    ('tier', self.tier), ('person_answer', person), ('answer_key', str(answer_key)),
                    ('mix', 'simple' if literal else _MIX[self.kind]))
        if membership is not None:
            metadata += (('membership_signature', membership),)
        if reveals or needs:
            metadata += (('reveals', tuple(dict.fromkeys(reveals))), ('needs', tuple(tuple(n) for n in needs)))
        return QuestionCandidate(
            text=text,
            options=options,
            correct_option_id=correct,
            source_rule_id=self.rule_id,
            source_field_keys=tuple(dict.fromkeys(DIMENSIONS_BY_KEY[d].field for d in dimensions)),
            involved_player_ids=tuple(involved),
            difficulty=self.difficulty,
            semantic_key=(self.family, *map(str, fact)),
            focus_player_ids=tuple(focus),
            metadata=metadata,
            explanation=explanation,
            knowledge_version=self.knowledge.version,
        )


# ----- shared explanation phrasing ----------------------------------------------------


def people(words: Wording, n: int, *, start: bool = False) -> str:
    phrase = words.people(n)
    return phrase[0].upper() + phrase[1:] if start and not words.he else phrase


def chose(words: Wording, key: str, category: str, n: int) -> str:
    """'chose horror movies' / 'גרים בצפון' — the verb phrase for n members of a category."""
    forms = words.forms(category, DIMENSIONS_BY_KEY[key].domain)
    one = n == 1
    if key == 'place.region':
        return words.text('lives in {in}' if one else 'live in {in}', 'גר {in}' if one else 'גרים {in}', **forms)
    if key == 'artist.genre':
        return words.text('chose an artist associated with {items}' if one else 'chose artists associated with {items}',
                          'בחר אמן שמזוהה עם {items}' if one else 'בחרו אמנים שמזוהים עם {items}', **forms)
    if key == 'song.genre':
        return words.text('chose a song in the {style} style' if one else 'chose songs in the {style} style',
                          'בחר שיר בסגנון {style}' if one else 'בחרו שירים בסגנון {style}', **forms)
    if key == 'music.genre':
        return words.text('chose {items}', 'בחר {items}' if one else 'בחרו {items}', **forms)
    return words.text('chose {item}' if one else 'chose {items}', 'בחר {item}' if one else 'בחרו {items}', **forms)


def sentence(words: Wording, key: str, category: str, n: int) -> str:
    return f'{people(words, n, start=True)} {chose(words, key, category, n)}'


def count_explanation(words: Wording, summary, category: str, members) -> str:
    what = sentence(words, summary.dimension.key, category, len(members))
    choices = {summary.evidence_label(p, words.language) for p in members}
    if summary.dimension.key == 'music.genre' and len(choices) == 1:
        # The chosen style is the category itself; listing it again says nothing.
        return words.text('{what}.', '{what}.', what=what) + words.coverage_note(summary)
    text = words.text('{what}: {evidence}.', '{what}: {evidence}.', what=what,
                      evidence=words.evidence(summary, members))
    return text + words.coverage_note(summary)


def leader_explanation(words: Wording, summary, winner: str, counts: dict[str, int]) -> str:
    key = summary.dimension.key
    text = words.text('{what} — more than any other {kind}.', '{what} — יותר מכל {kind} אחר.',
                      what=sentence(words, key, winner, counts[winner]), kind=words.kind(key))
    runner = second_place(summary, winner, counts)
    if runner is not None:
        text += ' ' + words.text('Second: {label} ({n}).', 'במקום השני: {label} ({n}).',
                                 label=words.forms(runner, summary.dimension.domain)['label'], n=counts[runner])
    if key in MEDIA_DIMENSIONS:
        text += ' ' + words.text('Choices included: {evidence}.', 'בין הבחירות: {evidence}.',
                                  evidence=words.evidence(summary, summary.members[winner]))
    return text + words.coverage_note(summary)


def counts_explanation(words: Wording, summary, categories, counts: dict[str, int]) -> str:
    listed = ', '.join(f"{words.forms(c, summary.dimension.domain)['label']} {counts[c]}" for c in categories)
    return words.text('The counts: {listed}.', 'הספירה: {listed}.', listed=listed) + words.coverage_note(summary)


def comparison_explanation(words: Wording, summary, winner, loser, counts, both, *, lead='') -> str:
    key = summary.dimension.key
    text = words.text('{lead}{what}, compared with {others} who {chose_other}.', '{lead}{what}, לעומת {others} ש{chose_other}.',
                      lead=lead, what=sentence(words, key, winner, counts[winner]),
                      others=people(words, counts[loser]), chose_other=chose(words, key, loser, counts[loser]))
    if both:
        text += ' ' + (words.text('One choice counts for both.', 'בחירה אחת שייכת לשניהם.') if len(both) == 1 else
                       words.text('{n} choices count for both.', '{n} בחירות שייכות לשניהם.', n=len(both)))
    return text


# ----- semantic group discoveries ------------------------------------------------------


class GroupCountRule(DiscoveryRule):
    """How many people's answers fall into a category — "Saw" and "The Conjuring" are two horror picks."""

    rule_id = 'group_count'
    family = 'SEMANTIC_COUNT'
    difficulty = Difficulty.EASY
    hops = 2
    dimensions = ('movie.genre', 'food.cuisine', 'hobby.family', 'hobby.physical', 'hobby.setting',
                  'music.genre', 'artist.genre', 'song.genre')
    only = {'hobby.physical': ('activity.physical',), 'hobby.setting': ('setting.outdoor',)}

    def candidates(self, summary, words, rng):
        for key in self.dimensions:
            s = summary.get(key)
            if s is None or not s.eligible_for_count():
                continue
            for category in self.only.get(key, s.categories):
                members = s.members.get(category, ())
                if not 0 < len(members) < len(s.consented):
                    continue
                fact = (key, category)
                n = len(members)
                operation = 'recognized_count' if key in MEDIA_DIMENSIONS and not s.complete else 'count'
                text = words.question(operation, key, fact, (category,), **words.forms(category, s.dimension.domain))
                yield self.candidate(
                    rng, text=text, answer=str(n), fact=fact, dimensions=(key,),
                    distractors=number_choices(n, uncertain=len(s.unknown), maximum=len(s.consented)),
                    explanation=count_explanation(words, s, category, members), involved=s.recognized,
                    answer_key=n, coverage=s.coverage,
                    interest=balance(n, len(s.recognized)) * clarity(s, members) * (1.0 if s.complete else s.coverage),
                    membership=(s.dimension.field, members), literal=s.literal(members),
                    # One member is the fewest possible. Half of the shared answers or more wins
                    # every race that can be asked, since tied races never are.
                    reveals=(*counts_of(key, (category,)), *(ones_of(key, (category,)) if n == 1 else ()),
                             *(ranks_of(key, (category,)) if 2 * n >= len(s.consented) else ())),
                    needs=(counts_of(key, (category,)),))


class GroupMajorityRule(DiscoveryRule):
    """The category that leads the group, decisively and with enough recognized answers."""

    rule_id = 'group_mode'
    family = 'SEMANTIC_MAJORITY'
    difficulty = Difficulty.EASY
    hops = 3
    dimensions = TASTES
    character = ('food.cuisine', 'hobby.family', 'music.genre')

    def candidates(self, summary, words, rng):
        for key in self.dimensions:
            s = summary.get(key)
            if s is None or not (s.eligible_for_media_leader() if key in MEDIA_DIMENSIONS
                                 else s.eligible_for_strong_claim()):
                continue
            counts = {c: s.count(c) for c in s.categories}
            leader = meaningful_leader(s, counts)
            if leader is None:
                continue
            winner, runner_up = leader
            domain = s.dimension.domain
            fact = (key,)
            label = words.forms(winner, domain)['label']
            explanation = leader_explanation(words, s, winner, counts)
            interest = leader_interest(counts[winner], runner_up, len(s.recognized)) * clarity(s, s.members[winner])
            disclosed = tuple(c for c in (winner, second_place(s, winner, counts)) if c is not None)
            disclosure = {'reveals': (*ranks_of(key, disclosed), *counts_of(key, disclosed)),
                          'needs': (ranks_of(key, (winner,)),)}
            rivals = sorted((c for c in s.represented() if c != winner),
                            key=lambda c: (-counts[c], s.categories.index(c)))
            variants = len(TEMPLATES[('majority', key)])
            if key in self.character and len(rivals) >= 2 and stable_index(fact, variants + 1) == variants:
                named = sorted((winner, *rivals[:2]), key=s.categories.index)
                labels = [words.forms(c, domain)['label'] for c in named]
                text = words.question('character', key, fact, named, a=labels[0], b=labels[1], c=labels[2])
                yield self.candidate(rng, text=text, answer=label, ordered=labels, fact=fact, dimensions=(key,),
                                     explanation=explanation, involved=s.recognized, answer_key=winner,
                                     coverage=s.coverage, interest=interest,
                                     membership=(s.dimension.field, s.members[winner]),
                                     literal=s.literal(s.members[winner]), **disclosure)
                continue
            text = words.question('majority', key, fact, (winner,))
            distractors = [words.forms(c, domain)['label'] for c in category_distractors(s, winner, counts)]
            yield self.candidate(rng, text=text, answer=label, distractors=distractors, fact=fact,
                                 dimensions=(key,), explanation=explanation, involved=s.recognized,
                                 answer_key=winner, coverage=s.coverage, interest=interest,
                                 membership=(s.dimension.field, s.members[winner]), **disclosure,
                                 literal=s.literal(s.members[winner]))


class GroupComparisonRule(DiscoveryRule):
    """Which of two categories is better represented — "horror or science fiction?"."""

    rule_id = 'group_comparison_semantic'
    family = 'SEMANTIC_COMPARISON'
    difficulty = Difficulty.MEDIUM
    hops = 3
    dimensions = ('movie.genre', 'food.cuisine', 'hobby.family', 'hobby.setting', 'hobby.physical',
                  'music.genre', 'artist.genre', 'song.genre')
    item_options = ('hobby.family', 'hobby.setting', 'hobby.physical')

    def candidates(self, summary, words, rng):
        for key in self.dimensions:
            s = summary.get(key)
            if s is None or not s.eligible_for_comparison():
                continue
            counts = {c: s.count(c) for c in s.categories}
            for a, b, both in comparable_pairs(s, counts):
                yield self.compare(s, words, rng, a, b, both, counts)

    def compare(self, s, words, rng, a, b, both, counts):
        key, domain = s.dimension.key, s.dimension.domain
        winner, loser = (a, b) if counts[a] > counts[b] else (b, a)
        forms_a, forms_b = words.forms(a, domain, '_a'), words.forms(b, domain, '_b')
        fact = (key, a, b)
        operation = 'overlap' if both and ('overlap', key) in TEMPLATES else 'comparison'
        text = words.question(operation, key, fact, (a, b), a=forms_a['label_a'], b=forms_b['label_b'],
                              **forms_a, **forms_b)
        option = 'items' if key in self.item_options else 'label'
        texts = [option_text(words, c, domain, option) for c in (a, b)]
        return self.candidate(
            rng, text=text, answer=option_text(words, winner, domain, option), ordered=texts, fact=fact,
            dimensions=(key,), explanation=comparison_explanation(words, s, winner, loser, counts, both)
            + words.coverage_note(s), involved=(*s.members[a], *s.members[b]), answer_key=winner,
            coverage=s.coverage, interest=closeness(counts[a], counts[b]) * clarity(s, (*s.members[a], *s.members[b])),
            literal=s.literal(s.members[a]) and s.literal(s.members[b]), reveals=counts_of(key, (a, b)),
            needs=(ranks_of(key, (a,)), ranks_of(key, (b,)), counts_of(key, (a, b))))


class GroupUniqueRule(DiscoveryRule):
    """The one person whose answer falls into a category — only asked when every answer is recognized."""

    rule_id = 'group_unique'
    family = 'SEMANTIC_UNIQUE'
    difficulty = Difficulty.MEDIUM
    hops = 2
    dimensions = TASTES

    def candidates(self, summary, words, rng):
        for key in self.dimensions:
            s = summary.get(key)
            if s is None or not s.complete or len(s.consented) < POLICY.min_answers:
                continue
            for category in s.represented():
                members = s.members[category]
                others = s.non_members(category)
                if len(members) != 1 or len(others) < 2:
                    continue
                player = members[0]
                fact = (key, category)
                text = words.question('unique', key, fact, (category,), **words.forms(category, s.dimension.domain))
                explanation = words.text('{name}: {evidence}.', '{name}: {evidence}.', name=summary.name(player),
                                         evidence=words.evidence(s, members))
                yield self.candidate(rng, text=text, answer=summary.name(player),
                                     distractors=[summary.name(p) for p in others], fact=fact, dimensions=(key,),
                                     explanation=explanation, involved=(player, *others), answer_key=player,
                                     focus=(player,), person=True, interest=clarity(s, members),
                                     membership=(s.dimension.field, members), literal=s.literal(members),
                                     reveals=(*counts_of(key, (category,)), *ones_of(key, (category,))))


class MediaGenreOutlierRule(DiscoveryRule):
    """One person has any unshared media genre; reject multiple such people.

    Several exclusive genres can identify the same person. Different people
    with different exclusive genres are not a unique answer to this question.
    """

    rule_id = 'group_genre_outlier'
    family = 'SEMANTIC_UNIQUE'
    hops = 3

    def candidates(self, summary, words, rng):
        for key in MEDIA_DIMENSIONS:
            s = summary.get(key)
            if (s is None or not s.complete or len(s.recognized) < POLICY.min_answers
                    or len(s.entities) != len(s.consented)):
                # A colliding title may share some genres across its versions,
                # but their intersection cannot prove other genres absent.
                continue
            exclusive = tuple(c for c in s.represented() if s.count(c) == 1)
            holders = {s.members[c][0] for c in exclusive}
            if len(holders) != 1:
                continue
            player = next(iter(holders))
            labels = words.join(words.forms(c, s.dimension.domain)['label'] for c in exclusive)
            explanation = words.text(
                '{name} chose {choice}. Only their choice represents these genres: {genres}.',
                '{name} בחר/ה {choice}. רק הבחירה הזאת מייצגת את הסגנונות האלה: {genres}.',
                name=summary.name(player), choice=s.evidence_label(player, words.language), genres=labels)
            yield self.candidate(rng, text=words.question('genre_outlier', key, (key,)),
                                 answer=summary.name(player), dimensions=(key,), explanation=explanation,
                                 fact=(key, 'exclusive_genres'), involved=s.recognized, answer_key=player,
                                 distractors=[summary.name(p) for p in s.recognized if p != player],
                                 focus=(player,), person=True, interest=clarity(s, (player,)),
                                 membership=(s.dimension.field, (player,)),
                                 reveals=(*counts_of(key, exclusive), *ones_of(key, exclusive)))


class GroupDiversityRule(DiscoveryRule):
    """How many different categories the group's answers cover — only when every answer is recognized."""

    tier = 1

    rule_id = 'group_diversity'
    family = 'SEMANTIC_DIVERSITY'
    difficulty = Difficulty.MEDIUM
    hops = 3
    dimensions = ('food.cuisine', 'hobby.family', 'music.genre', *MEDIA_DIMENSIONS)
    maximum = 6

    def candidates(self, summary, words, rng):
        for key in self.dimensions:
            s = summary.get(key)
            if s is None or not s.complete or len(s.consented) < POLICY.min_answers:
                continue
            if key in MEDIA_DIMENSIONS and len(s.entities) != len(s.consented):
                continue  # Shared genres of ambiguous titles are not a complete genre inventory.
            represented = s.represented()
            n = len(represented)
            if not 2 <= n <= self.maximum:
                continue
            form = 'from' if s.dimension.domain == 'place' and not words.he else 'label'
            labels = [words.forms(c, s.dimension.domain)[form] for c in represented]
            explanation = words.text('{n} {kinds}: {labels}.', '{n} {kinds}: {labels}.', n=n,
                                     kinds=words.kind(key, plural=True), labels=words.join(labels))
            if key in MEDIA_DIMENSIONS:
                explanation += ' ' + words.text('One choice can belong to several genres; each genre counts once.',
                                                'בחירה אחת יכולה להשתייך לכמה סגנונות; כל סגנון נספר פעם אחת.')
            yield self.candidate(rng, text=words.question('diversity', key, (key,)), answer=str(n),
                                 distractors=number_choices(n, uncertain=0, maximum=len(s.categories), minimum=1),
                                 fact=(key,), dimensions=(key,), explanation=explanation, involved=s.recognized,
                                 answer_key=n, interest=0.6,
                                 literal=all(s.literal(s.members[c]) for c in represented))


class GroupMinorityRule(DiscoveryRule):
    """Among a few represented categories, the clearly least common one."""

    tier = 1

    rule_id = 'group_minority'
    family = 'SEMANTIC_MINORITY'
    difficulty = Difficulty.MEDIUM
    hops = 3
    dimensions = ('movie.genre', 'food.cuisine', 'hobby.family', 'music.genre')

    def candidates(self, summary, words, rng):
        for key in self.dimensions:
            s = summary.get(key)
            if s is None or not s.eligible_for_strong_claim() or len(s.consented) < 6:
                continue
            counts = {c: s.count(c) for c in s.categories}
            represented = sorted(s.represented(), key=lambda c: (counts[c], s.categories.index(c)))
            if len(represented) < 3:
                continue
            smallest = represented[0]
            if counts[represented[1]] <= counts[smallest] + len(s.unknown):
                continue  # Tied, or an unknown answer could tie it: no single least common category.
            rivals = represented[1:4]
            if len(rivals) < 2:
                continue
            shown = sorted((smallest, *rivals), key=s.categories.index)
            labels = [words.forms(c, s.dimension.domain)['label'] for c in shown]
            yield self.candidate(rng, text=words.question('minority', key, (key, smallest)),
                                 answer=words.forms(smallest, s.dimension.domain)['label'], ordered=labels,
                                 fact=(key, *shown), dimensions=(key,),
                                 explanation=counts_explanation(words, s, shown, counts), involved=s.recognized,
                                 answer_key=smallest, coverage=s.coverage, interest=0.5,
                                 literal=all(s.literal(s.members[c]) for c in shown),
                                 reveals=counts_of(key, shown),
                                 needs=(ones_of(key, (smallest,)), counts_of(key, shown)))


class GroupDistributionRule(DiscoveryRule):
    """Among a few categories other than the overall leader, the clearly most common one."""

    tier = 1

    rule_id = 'group_distribution'
    family = 'SEMANTIC_DISTRIBUTION'
    difficulty = Difficulty.MEDIUM
    hops = 3
    dimensions = TASTES

    def candidates(self, summary, words, rng):
        for key in self.dimensions:
            s = summary.get(key)
            if s is None or not s.eligible_for_strong_claim():
                continue
            counts = {c: s.count(c) for c in s.categories}
            represented = sorted(s.represented(), key=lambda c: (-counts[c], s.categories.index(c)))
            if len(represented) < 5:
                continue
            top = counts[represented[0]]
            rest = [c for c in represented if counts[c] < top]
            if len(rest) < 3:
                continue
            best = rest[0]
            if counts[rest[1]] + len(s.unknown) >= counts[best]:
                continue  # Tied, or an unknown answer could tie it.
            others = rest[1:4]
            if len(others) < 2:
                continue
            shown = sorted((best, *others), key=s.categories.index)
            labels = [words.forms(c, s.dimension.domain)['label'] for c in shown]
            yield self.candidate(rng, text=words.question('distribution', key, (key, best)),
                                 answer=words.forms(best, s.dimension.domain)['label'], ordered=labels,
                                 fact=(key, *shown), dimensions=(key,),
                                 explanation=counts_explanation(words, s, shown, counts), involved=s.recognized,
                                 answer_key=best, coverage=s.coverage, interest=0.5,
                                 literal=all(s.literal(s.members[c]) for c in shown),
                                 reveals=(*ranks_of(key, (best,)), *counts_of(key, shown)),
                                 needs=(ranks_of(key, (best,)), counts_of(key, shown)))


# ----- geography ---------------------------------------------------------------------


class RegionMajorityRule(DiscoveryRule):
    """Where most of the group comes from; "majority" wording only for more than half."""

    rule_id = 'region_majority'
    family = 'GEO_REGION_MAJORITY'
    kind = 'geographic'
    difficulty = Difficulty.EASY
    hops = 3

    def candidates(self, summary, words, rng):
        s = summary.get('place.region')
        if s is None or not s.eligible_for_strong_claim():
            return
        counts = {c: s.count(c) for c in s.categories}
        leader = meaningful_leader(s, counts)
        if leader is None:
            return
        winner, runner_up = leader
        n = counts[winner]
        # "Most of the group" means more than half of everyone in the room.
        majority = 2 * n > s.group_size
        operation = 'region_majority' if majority else 'region_plurality'
        forms = words.forms(winner, 'place')
        key = s.dimension.key
        disclosed = (winner,) if majority else tuple(c for c in (winner, second_place(s, winner, counts)) if c is not None)
        if majority:
            explanation = words.text('{n} people live in {in} — more than half the group.',
                                     '{n} אנשים גרים {in} — יותר ממחצית הקבוצה.', n=n, **forms)
        else:
            explanation = leader_explanation(words, s, winner, counts)
        yield self.candidate(rng, text=words.question(operation, 'place.region', ('place.region',), (winner,)),
                             answer=forms['label'], fact=('place.region', operation), dimensions=('place.region',),
                             distractors=[words.forms(c, 'place')['label'] for c in category_distractors(s, winner, counts)],
                             explanation=explanation + (words.coverage_note(s) if majority else ''),
                             involved=s.recognized, answer_key=winner, coverage=s.coverage,
                             interest=leader_interest(n, runner_up, len(s.recognized)),
                             membership=(s.dimension.field, s.members[winner]),
                             reveals=(*ranks_of(key, disclosed), *counts_of(key, disclosed)),
                             needs=(ranks_of(key, (winner,)),))


class RegionComparisonRule(GroupComparisonRule):
    rule_id = 'region_comparison'
    family = 'GEO_REGION_COMPARISON'
    kind = 'geographic'
    dimensions = ('place.region',)


class RegionCountRule(GroupCountRule):
    tier = 1
    rule_id = 'region_count'
    family = 'GEO_REGION_COUNT'
    kind = 'geographic'
    dimensions = ('place.region',)
    only = {}


class RegionUniqueRule(GroupUniqueRule):
    tier = 1
    rule_id = 'region_unique'
    family = 'GEO_REGION_UNIQUE'
    kind = 'geographic'
    dimensions = ('place.region',)


class RegionDiversityRule(GroupDiversityRule):
    tier = 1
    rule_id = 'region_diversity'
    family = 'GEO_REGION_DIVERSITY'
    kind = 'geographic'
    dimensions = ('place.region',)
    maximum = 4


class LocalityExtremeRule(DiscoveryRule):
    """Who lives furthest north or south, by town reference points — every town must be identified."""

    rule_id = 'locality_extreme'
    family = 'GEO_EXTREME'
    kind = 'geographic'
    difficulty = Difficulty.EASY
    hops = 2
    minimum_gap_degrees = 0.02

    def candidates(self, summary, words, rng):
        places = summary.places
        if len(places) < POLICY.min_answers:
            return
        latitude = {p: e.coordinates[0] for p, e in places.items()}
        for direction in ('north', 'south'):
            ordered = sorted(places, key=lambda p: (-latitude[p] if direction == 'north' else latitude[p], p))
            first, second = ordered[0], ordered[1]
            if abs(latitude[first] - latitude[second]) < self.minimum_gap_degrees:
                continue
            town = summary.get('place.region').town(first, words.language)
            explanation = words.text(
                '{town}, where {name} lives, is the {direction}ernmost town in the group.',
                '{town}, היישוב של {name}, הוא ה{adjective} ביותר בקבוצה.', town=town, name=summary.name(first),
                direction=direction, adjective='צפוני' if direction == 'north' else 'דרומי')
            yield self.candidate(rng, text=words.question(direction, 'place.region', (direction,)),
                                 answer=summary.name(first), distractors=[summary.name(p) for p in ordered[1:]],
                                 fact=(direction,), dimensions=('place.region',), explanation=explanation,
                                 involved=tuple(places), answer_key=first, focus=(first,), person=True, interest=1.0)


class ClosestPairRule(DiscoveryRule):
    """The two people whose towns are closest, when that pair is clearly closest."""

    rule_id = 'locality_distance_pair'
    family = 'GEO_CLOSEST_PAIR'
    kind = 'geographic'
    difficulty = Difficulty.MEDIUM
    hops = 3
    minimum_gap_km = 2.0

    def candidates(self, summary, words, rng):
        if len(summary.places) < POLICY.min_answers:
            return
        distances = summary.distances
        ordered = sorted(distances, key=lambda pair: (distances[pair], pair))
        best, second = ordered[0], ordered[1]
        if distances[best] < 1.0 or distances[second] - distances[best] < self.minimum_gap_km:
            return
        pair_name = lambda pair: f'{summary.name(pair[0])} + {summary.name(pair[1])}'
        places = summary.places
        explanation = words.text(
            '{a} and {b} live in {town_a} and {town_b}, about {km} km apart as the crow flies.',
            '{a} ו{b} גרים ב{town_a} וב{town_b}, כ־{km} ק״מ זה מזה בקו אווירי.',
            a=summary.name(best[0]), b=summary.name(best[1]),
            town_a=summary.get('place.region').town(best[0], words.language),
            town_b=summary.get('place.region').town(best[1], words.language), km=round(distances[best]))
        yield self.candidate(rng, text=words.question('closest_pair', 'place.region', ('closest',)),
                             answer=pair_name(best), distractors=[pair_name(p) for p in ordered[1:8]],
                             fact=('closest',), dimensions=('place.region',), explanation=explanation,
                             involved=tuple(places), answer_key='+'.join(best), focus=best, person=True, interest=1.0)


class GeographicOutlierRule(DiscoveryRule):
    """Who lives furthest from everyone else on average, when clearly so."""

    tier = 1

    rule_id = 'geographic_outlier'
    family = 'GEO_OUTLIER'
    kind = 'geographic'
    difficulty = Difficulty.MEDIUM
    hops = 3
    minimum_gap_km = 5.0

    def candidates(self, summary, words, rng):
        places = summary.places
        if len(places) < POLICY.min_answers:
            return
        distances = summary.distances
        average = {p: sum(d for pair, d in distances.items() if p in pair) / (len(places) - 1) for p in places}
        ordered = sorted(places, key=lambda p: (-average[p], p))
        if average[ordered[0]] - average[ordered[1]] < self.minimum_gap_km:
            return
        winner = ordered[0]
        explanation = words.text(
            '{name} lives in {town}, on average about {km} km from the other towns in the group, as the crow flies.',
            '{name} גר/ה ב{town}, בממוצע כ־{km} ק״מ בקו אווירי משאר היישובים בקבוצה.',
            name=summary.name(winner), town=summary.get('place.region').town(winner, words.language),
            km=round(average[winner]))
        yield self.candidate(rng, text=words.question('outlier', 'place.region', ('outlier',)),
                             answer=summary.name(winner), distractors=[summary.name(p) for p in ordered[1:]],
                             fact=('outlier',), dimensions=('place.region',), explanation=explanation,
                             involved=tuple(places), answer_key=winner, focus=(winner,), person=True, interest=0.8)


# ----- cross-domain ------------------------------------------------------------------


def subgroups(summary, condition_key: str):
    """Large enough, proper subgroups defined by one category of a well-recognized dimension."""
    condition = summary.get(condition_key)
    if condition is None or not condition.eligible_for_count():
        return
    minimum = summary.subgroup_min_size()
    for category in condition.categories:
        members = condition.members[category]
        if minimum <= len(members) < len(condition.consented):
            yield condition, category, members


def subgroup_target(summary, target_key: str, members):
    """The target dimension restricted to a subgroup, if its answers are well recognized there."""
    target = summary.get(target_key)
    if target is None:
        return None
    shared = [p for p in members if p in target.consented]
    known = [p for p in shared if p in target.recognized]
    if len(shared) < POLICY.subgroup_min_size or len(known) < POLICY.strong_coverage * len(shared):
        return None
    return target, known, len(shared) - len(known)


def condition_text(words: Wording, condition, category) -> str:
    key = condition.dimension.key
    return words.render(SUBGROUP_CONDITIONS[key], **words.forms(category, condition.dimension.domain))


class SubgroupMajorityRule(DiscoveryRule):
    """Within a subgroup, the leading category of another domain — "among horror fans, which hobbies?"."""

    rule_id = 'group_filtered_mode'
    family = 'CROSS_SUBGROUP_MAJORITY'
    kind = 'cross_domain'
    difficulty = Difficulty.HARD
    hops = 4
    pairs = (('movie.genre', 'hobby.family'), ('hobby.family', 'movie.genre'), ('food.cuisine', 'place.region'),
             ('place.region', 'food.cuisine'), ('music.genre', 'hobby.family'), ('place.region', 'hobby.family'),
             ('place.region', 'music.genre'), ('hobby.family', 'music.genre'),
             ('artist.genre', 'hobby.family'), ('hobby.family', 'artist.genre'),
             ('song.genre', 'movie.genre'), ('movie.genre', 'song.genre'),
             ('movie.genre', 'artist.genre'), ('artist.genre', 'movie.genre'))

    def candidates(self, summary, words, rng):
        for condition_key, target_key in self.pairs:
            for condition, category, members in subgroups(summary, condition_key):
                if (condition_key in MEDIA_DIMENSIONS or target_key in MEDIA_DIMENSIONS) and not condition.complete:
                    continue  # An unresolved condition must not silently exclude a potential subgroup member.
                scoped = subgroup_target(summary, target_key, members)
                if scoped is None:
                    continue
                target, known, unknown = scoped
                counts = target.counts_within(known)
                leader = decisive_leader(counts, unknown, target.categories)
                if leader is None or counts[leader[0]] < 2:
                    continue
                winner, runner_up = leader
                domain = target.dimension.domain
                within = scope(condition_key, category, target_key)
                text = words.text('{condition}, {question}', '{condition}, {question}',
                                  condition=condition_text(words, condition, category),
                                  question=words.render(SUBGROUP_QUESTIONS[target_key]))
                explanation = words.text(
                    '{group}. Of them, {what} — more than any other {kind}.',
                    '{group}. מתוכם, {what} — יותר מכל {kind} אחר.',
                    group=sentence(words, condition_key, category, len(members)),
                    what=f'{counts[winner]} {chose(words, target_key, winner, counts[winner])}',
                    kind=words.kind(target_key))
                distractors = [words.forms(c, domain)['label'] for c in category_distractors(target, winner, counts)]
                yield self.candidate(rng, text=text, answer=words.forms(winner, domain)['label'],
                                     distractors=distractors, fact=(condition_key, category, target_key),
                                     dimensions=(condition_key, target_key), explanation=explanation,
                                     involved=known, answer_key=winner, coverage=len(known) / len(members),
                                     interest=leader_interest(counts[winner], runner_up, len(known)),
                                     reveals=(*ranks_of(within, (winner,)), *counts_of(within, (winner,)),
                                              *counts_of(condition_key, (category,))),
                                     needs=(ranks_of(within, (winner,)),),
                                     membership=pair_membership(condition, target,
                                                                (p for p in known if p in target.members[winner])))


class SubgroupComparisonRule(DiscoveryRule):
    """Within a subgroup, which of two categories of another domain leads."""

    rule_id = 'group_subgroup_comparison'
    family = 'CROSS_SUBGROUP_COMPARISON'
    kind = 'cross_domain'
    difficulty = Difficulty.HARD
    hops = 4
    pairs = (('music.genre', 'hobby.family'), ('movie.genre', 'hobby.family'), ('place.region', 'food.cuisine'),
             ('food.cuisine', 'hobby.family'), ('hobby.family', 'movie.genre'), ('place.region', 'hobby.setting'),
             ('hobby.family', 'artist.genre'), ('movie.genre', 'song.genre'), ('artist.genre', 'movie.genre'))

    def candidates(self, summary, words, rng):
        for condition_key, target_key in self.pairs:
            for condition, category, members in subgroups(summary, condition_key):
                if (condition_key in MEDIA_DIMENSIONS or target_key in MEDIA_DIMENSIONS) and not condition.complete:
                    continue
                scoped = subgroup_target(summary, target_key, members)
                if scoped is None:
                    continue
                target, known, unknown = scoped
                counts = target.counts_within(known)
                for a, b, _ in comparable_pairs(target, counts, unknown, people=known, limit=2):
                    yield self.compare(summary, words, rng, condition, category, members, target, known,
                                       counts, a, b)

    def compare(self, summary, words, rng, condition, category, members, target, known, counts, a, b):
        target_key, domain = target.dimension.key, target.dimension.domain
        within = scope(condition.dimension.key, category, target_key)
        winner, loser = (a, b) if counts[a] > counts[b] else (b, a)
        forms = {**words.forms(a, domain, '_a'), **words.forms(b, domain, '_b')}
        question = words.render(SUBGROUP_COMPARISONS[target_key], a=forms['label_a'], b=forms['label_b'], **forms)
        text = words.text('{condition}, {question}', '{condition}, {question}',
                          condition=condition_text(words, condition, category), question=question)
        option = 'items' if target_key in ('hobby.setting', 'hobby.family') else 'label'
        texts = [option_text(words, c, domain, option) for c in (a, b)]
        explanation = words.text(
            '{group}. Of them, {n_w} {chose_w} and {n_l} {chose_l}.', '{group}. מתוכם, {n_w} {chose_w} ו־{n_l} {chose_l}.',
            group=sentence(words, condition.dimension.key, category, len(members)), n_w=counts[winner],
            chose_w=chose(words, target_key, winner, counts[winner]), n_l=counts[loser],
            chose_l=chose(words, target_key, loser, counts[loser]))
        return self.candidate(rng, text=text, answer=option_text(words, winner, domain, option), ordered=texts,
                              fact=(condition.dimension.key, category, target_key, a, b),
                              dimensions=(condition.dimension.key, target_key), explanation=explanation,
                              involved=known, answer_key=winner, coverage=len(known) / len(members),
                              interest=closeness(counts[a], counts[b]),
                              reveals=(*counts_of(within, (a, b)), *counts_of(condition.dimension.key, (category,))),
                              needs=(ranks_of(within, (a,)), ranks_of(within, (b,)), counts_of(within, (a, b))))


class IntersectionCountRule(DiscoveryRule):
    """How many people's answers fall into two categories of different domains at once."""

    rule_id = 'group_intersection_count'
    family = 'CROSS_INTERSECTION_COUNT'
    kind = 'cross_domain'
    difficulty = Difficulty.HARD
    hops = 3
    pairs = (('movie.genre', 'hobby.family'), ('food.cuisine', 'hobby.family'), ('music.genre', 'hobby.family'),
             ('place.region', 'food.cuisine'), ('place.region', 'hobby.family'), ('movie.genre', 'food.cuisine'))
    per_pair = 4

    def candidates(self, summary, words, rng):
        for key_a, key_b in self.pairs:
            first, second = summary.get(key_a), summary.get(key_b)
            if first is None or second is None or not (first.eligible_for_count() and second.eligible_for_count()):
                continue
            found = []
            for category_a in first.represented():
                for category_b in second.represented():
                    members_a, members_b = first.members[category_a], second.members[category_b]
                    if len(members_a) < 2 or len(members_b) < 2:
                        continue
                    both = tuple(p for p in members_a if p in set(members_b))
                    if 0 < len(both) < min(len(members_a), len(members_b)):
                        found.append((category_a, category_b, both))
            found.sort(key=lambda f: (-len(f[2]), first.categories.index(f[0]), second.categories.index(f[1])))
            for category_a, category_b, both in found[:self.per_pair]:
                yield self.intersect(summary, words, rng, first, second, category_a, category_b, both)

    def intersect(self, summary, words, rng, first, second, category_a, category_b, both):
        key_a, key_b = first.dimension.key, second.dimension.key
        forms = {**words.forms(category_a, first.dimension.domain, '_a'),
                 **words.forms(category_b, second.dimension.domain, '_b')}
        template = INTERSECTIONS.get(key_a, INTERSECTIONS[None])
        n = len(both)
        disclosed = (*counts_of(scope(key_a, category_a, key_b), (category_b,)),
                     *counts_of(scope(key_b, category_b, key_a), (category_a,)))
        uncertain = len(set(first.unknown) | set(second.unknown))
        if first.literal(both):
            pairs = words.evidence(second, both)
        else:
            pairs = ', '.join(f'{first.evidence_label(p, words.language)} + {second.evidence_label(p, words.language)}'
                              for p in both[:3])
        one = n == 1
        what = (words.text('{people} lives in {in_a} and chose {item_b}' if one else '{people} live in {in_a} and chose {item_b}',
                           '{people} גר {in_a} ובחר {item_b}' if one else '{people} גרים {in_a} ובחרו {item_b}', **forms,
                           people=people(words, n, start=True))
                if key_a == 'place.region' else
                words.text('{people} chose both {item_a} and {item_b}',
                           '{people} בחר גם {item_a} וגם {item_b}' if one else '{people} בחרו גם {item_a} וגם {item_b}',
                           **forms, people=people(words, n, start=True)))
        return self.candidate(rng, text=words.render(template, **forms), answer=str(n),
                              distractors=number_choices(n, uncertain=uncertain, maximum=len(summary.dataset.player_ids)),
                              fact=(key_a, category_a, key_b, category_b), dimensions=(key_a, key_b),
                              explanation=words.text('{what}: {pairs}.', '{what}: {pairs}.', what=what, pairs=pairs),
                              involved=tuple(dict.fromkeys((*first.recognized, *second.recognized))), answer_key=n,
                              coverage=min(first.coverage, second.coverage),
                              interest=balance(n, len(summary.dataset.player_ids)),
                              membership=pair_membership(first, second, both),
                              reveals=disclosed, needs=tuple((atom,) for atom in disclosed))


def discovery_rules(knowledge) -> tuple[DiscoveryRule, ...]:
    """Category-first families, in a stable order (the order candidates are generated)."""
    return tuple(rule(knowledge) for rule in (
        GroupCountRule, GroupMajorityRule, GroupComparisonRule, GroupUniqueRule, MediaGenreOutlierRule, GroupDiversityRule,
        GroupMinorityRule, GroupDistributionRule,
        RegionMajorityRule, RegionComparisonRule, RegionCountRule, RegionUniqueRule, RegionDiversityRule,
        LocalityExtremeRule, ClosestPairRule, GeographicOutlierRule,
        SubgroupMajorityRule, SubgroupComparisonRule, IntersectionCountRule,
    ))


def production_rules(knowledge) -> tuple[QuestionRule, ...]:
    """The knowledge-backed production registry: simple social questions plus group discoveries."""
    from app.domain.questions.group_rules import social_legacy_rules
    from app.domain.questions.rules import default_rules

    return (*social_legacy_rules(default_rules(), knowledge), *discovery_rules(knowledge))
