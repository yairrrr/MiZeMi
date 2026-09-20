"""Deterministic question selection (MASTER_SPEC.md §12).

Legacy mode targets easy/medium/hard bands, then balances rule use, recently
repeated subjects and fields, total field use, quality and participant spread.

Group-first mode (knowledge-backed games) plans a mix of question kinds from
what the group's data actually supports — about 45% semantic group
discoveries, 25% simple social questions, 15% geography and 15% cross-domain
subgroups — and fills it with the most varied, most informative facts:

* Candidate volume does not buy selection. Candidates collapse to one per fact
  before planning, and families, domains and person-answer questions are
  capped, so a rule that emits hundreds of lookups competes like any other.
* A kind's share is limited to its supply and never padded with weak
  questions; unused share flows to the kinds that have more to offer.
* Raw person lookups are deferred until every eligible non-lookup fact has
  been considered, with a hard one-question limit that never relaxes.
* Within the semantic kind, give each supported movie/artist/song source a first
  genre discovery before repeating other sources; prefer its decisive leader,
  then a comparison or unique outlier. Artists, songs and selected music styles
  have independent budgets. Unsupported sources create no reserved slots.
* After source coverage: fewest questions from the same family and domain first, then
  difficulty spread, then information value (the quality score). Supporting
  families (diversity, minority, distribution, region counts) rank as if
  already used once, so they add variety rather than displace core discoveries.
* No question is answered by one shown before it. Counts and rankings declare
  what they disclose (``reveals``) and what would already answer them
  (``needs``); games are shown easy to hard, so "which hobby type is most
  common?" (easy) rules out a later "sport or reading?" (medium), while an easy
  count may still precede a medium comparison it does not settle. This is
  never relaxed: when too few unsettled facts exist the game is shorter.
* Ties break on language-independent fact keys, so a seeded game selects the
  same facts in Hebrew and English.

All comparisons use local metadata and text, with no AI or external service.
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from math import ceil

from app.domain.questions.candidate import QuestionCandidate
from app.domain.questions.group_summary import DOMAIN_GROUPS
from app.domain.questions.language import normalize
from app.domain.questions.question import Difficulty

KIND_SHARES = (('semantic', 0.45), ('cross_domain', 0.20), ('geographic', 0.13), ('social', 0.12),
               ('direct', 0.10))
DIRECT_RULE_CAP = 2
RAW_LOOKUP_CAP = 1
AGE_CAP = 1
_LEVELS = {Difficulty.EASY: 0, Difficulty.MEDIUM: 1, Difficulty.HARD: 2}
_MIX_KINDS = {'semantic': 'semantic', 'geographic': 'geographic', 'simple': 'direct', 'other': 'direct',
              'social': 'social'}
# Families the legacy raw-answer rules belong to, in the same terms the
# discovery families describe themselves.
_LEGACY_OPERATIONS = {'DIRECT_UNIQUE': 'unique', 'DIRECT_COUNT': 'count', 'DIRECT_COMPARISON': 'comparison',
                      'DIRECT_MAJORITY': 'majority', 'DIRECT_AGE': 'extreme', 'DIRECT_CHOICE': 'literal'}
# Reasoning patterns a player cannot tell apart within one subject: "of these,
# which appears most?" and "which appears least?" read as the same question.
_IDEA_CLASSES = {'distribution': 'ranked_list', 'minority': 'ranked_list',
                 'agreement': 'group_spread', 'variety': 'group_spread',
                 # "X chose this — who else?" and "who chose both?" name one
                 # person from one connection; they read as the same question.
                 'partner': 'connection', 'link': 'connection', 'both': 'connection'}
# Music style, favourite artist and favourite song are classified the same way;
# for "have we asked this already?" they are one subject, not three.
_IDEA_TOPICS = {'artist.genre': 'music.genre', 'song.genre': 'music.genre'}


@dataclass
class _Entry:
    candidate: QuestionCandidate
    score: float
    order: int
    kind: str = ''
    family: str = ''
    domain: str = ''
    domains: tuple[str, ...] = ()
    fact: tuple = ()
    fact_order: str = ''
    text_key: str = ''
    membership: object = None
    person: bool = False
    tier: int = 0
    players: tuple[str, ...] = field(default_factory=tuple)
    level: int = 0
    hops: int = 1
    operation: str = ''
    topic: str = ''
    subgroup: str = ''
    anchor: str = ''
    idea: tuple = ()
    signature: tuple = ()
    group: str = ''
    groups: tuple[str, ...] = ()
    fields: tuple[str, ...] = ()
    reveals: frozenset = frozenset()
    needs: tuple[frozenset, ...] = ()
    topics: frozenset = frozenset()


def _entry(candidate: QuestionCandidate, score: float, order: int) -> _Entry:
    meta = dict(candidate.metadata)
    kind = meta.get('kind') or _MIX_KINDS.get(meta.get('mix'), 'semantic' if candidate.knowledge_version else 'direct')
    domain = meta.get('domain') or (candidate.source_field_keys[0] if candidate.source_field_keys else '')
    fact = candidate.semantic_key or (
        candidate.source_rule_id,
        candidate.source_field_keys,
        candidate.involved_player_ids[0] if candidate.involved_player_ids else None,
    )
    family = meta.get('family') or candidate.source_rule_id
    operation = meta.get('operation') or _LEGACY_OPERATIONS.get(family, family.lower())
    topic = meta.get('topic') or (candidate.source_field_keys[0] if candidate.source_field_keys else family)
    domains = tuple(meta['domains'].split(',')) if meta.get('domains') else (domain,)
    groups = tuple(dict.fromkeys(DOMAIN_GROUPS.get(d, d) for d in domains))
    return _Entry(
        candidate=candidate,
        score=score,
        order=order,
        kind=kind,
        family=family,
        operation=operation,
        topic=topic,
        subgroup=meta.get('subgroup', ''),
        anchor=meta.get('anchor', ''),
        # What the question asks, whatever wording variant it was given, and the
        # idea behind it — the pair that must not appear twice in one game.
        signature=tuple(meta.get('signature') or (operation, topic, *map(str, fact))),
        idea=(_IDEA_CLASSES.get(operation, operation), _IDEA_TOPICS.get(topic, topic)),
        group=groups[-1],
        groups=groups,
        fields=tuple(dict.fromkeys(candidate.source_field_keys)),
        domain=domain,
        domains=domains,
        fact=fact,
        fact_order=repr(fact),
        text_key=str(normalize(candidate.text)),
        membership=meta.get('membership_signature'),
        person=bool(meta.get('person_answer')),
        tier=int(meta.get('tier', 0)),
        players=candidate.focus_player_ids or candidate.involved_player_ids,
        level=_LEVELS[candidate.difficulty],
        hops=int(meta.get('reasoning_hops', 1)),
        reveals=frozenset(meta.get('reveals', ())),
        needs=tuple(frozenset(group) for group in meta.get('needs', ())),
        topics=frozenset(atom[1] for atom in (*meta.get('reveals', ()), *(a for g in meta.get('needs', ()) for a in g))),
    )


def _settled(needs: tuple[frozenset, ...], level: int, earlier: list[_Entry], extra: frozenset = frozenset()) -> bool:
    """Whether facts shown no later than ``level`` already answer a question with these ``needs``.

    Questions of the same difficulty may be shown in either order, so they count as earlier.
    """
    known = set(extra)
    for other in earlier:
        if other.level <= level:
            known |= other.reveals
    return any(group <= known for group in needs)


def plan_quotas(total: int, supply: dict[str, int]) -> dict[str, int]:
    """Split ``total`` questions across kinds by preferred share, limited by supply."""
    shares = dict(KIND_SHARES)
    quotas = {kind: 0 for kind in supply}
    active = [kind for kind in supply if supply[kind] > 0]
    while active and sum(quotas.values()) < total:
        remaining = total - sum(quotas.values())
        weight = sum(shares.get(kind, 0.1) for kind in active)
        raw = {kind: remaining * shares.get(kind, 0.1) / weight for kind in active}
        grant = {kind: min(int(raw[kind]), supply[kind] - quotas[kind]) for kind in active}
        spare = remaining - sum(grant.values())
        for kind in sorted(active, key=lambda k: (-(raw[k] - int(raw[k])), -shares.get(k, 0.1), k)):
            if spare and quotas[kind] + grant[kind] < supply[kind]:
                grant[kind] += 1
                spare -= 1
        if not any(grant.values()):
            break
        for kind, amount in grant.items():
            quotas[kind] += amount
        active = [kind for kind in active if quotas[kind] < supply[kind]]
    return quotas


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
        if self.group_first:
            return self._select_group_first(scored_candidates, question_count)

        remaining = list(scored_candidates)
        selected: list[QuestionCandidate] = []
        seen_texts: set[str] = set()
        seen_signatures: set[tuple] = set()
        rule_pick_counts: dict[str, int] = {}
        field_pick_counts: dict[str, int] = {}
        player_feature_counts: dict[str, int] = {}

        levels = _LEVELS
        while remaining and len(selected) < question_count:
            fraction = len(selected) / question_count
            target = 0 if fraction < 0.25 else 1 if fraction < 0.7 else 2

            def pick_key(entry: tuple[QuestionCandidate, float]):
                candidate, score = entry
                return (
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
            remaining = [(c, score) for c, score in remaining if str(normalize(c.text)) not in seen_texts
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
            seen_texts.add(text_key)
            seen_signatures.add(signature)
            rule_pick_counts[candidate.source_rule_id] = (
                rule_pick_counts.get(candidate.source_rule_id, 0) + 1
            )
            for field_key in set(candidate.source_field_keys):
                field_pick_counts[field_key] = field_pick_counts.get(field_key, 0) + 1
            for pid in candidate.focus_player_ids or candidate.involved_player_ids:
                player_feature_counts[pid] = player_feature_counts.get(pid, 0) + 1

        return tuple(selected)

    def _select_group_first(self, scored, question_count: int) -> tuple[QuestionCandidate, ...]:
        # One entry per fact: the most informative rendering wins, ties by fact key.
        entries = sorted((_entry(c, s, i) for i, (c, s) in enumerate(scored)),
                         key=lambda e: (-round(e.score, 9), e.fact_order, e.order))
        pool: dict[object, _Entry] = {}
        for entry in entries:
            pool.setdefault(entry.fact, entry)
        # Prefer facts that settle others; if that leaves a shorter game, a second
        # pass without the preference may find more unsettled facts. Neither pass
        # ever admits a settled question: fewer questions beat a repeated answer.
        selected = self._fill(list(pool.values()), question_count, prefer_settling=True)
        if len(selected) < question_count:
            retry = self._fill(list(pool.values()), question_count, prefer_settling=False)
            if len(retry) > len(selected):
                selected = retry
        return tuple(entry.candidate for entry in _presentation_order(selected))

    @staticmethod
    def _fill(remaining: list[_Entry], question_count: int, *, prefer_settling: bool) -> list[_Entry]:
        """Greedy staged fill of up to ``question_count`` facts, none settled by another."""
        supply = Counter(entry.kind for entry in remaining)
        quotas = plan_quotas(min(question_count, len(remaining)), dict(supply))
        preference = {kind: index for index, (kind, _) in enumerate(KIND_SHARES)}
        caps = {
            'family': max(2, ceil(question_count / 5)),
            'domain': max(2, ceil(question_count * 0.25)),
            # A subject a player experiences as one topic — music style, artist
            # and song are one — never takes more than a quarter of a game.
            'group': max(2, ceil(question_count * 0.3)),
            'domain_family': max(1, question_count // 12),
            'person': max(2, question_count // 4),
            # No reasoning pattern takes more than a fifth of the game, however
            # much supply it has: that is what made games feel repetitive.
            'operation': max(2, ceil(question_count / 5)),
            'direct': max(1, ceil(question_count * 0.1)),
            'supporting_family': max(1, question_count // 20),
        }
        picked: Counter = Counter()
        families: Counter = Counter()
        domains: Counter = Counter()
        groups: Counter = Counter()
        operations: Counter = Counter()
        styles: Counter = Counter()
        direct_groups: Counter = Counter()
        lookups = [0]  # raw-answer questions chosen so far
        fields: Counter = Counter()
        seen_signatures: set = set()
        seen_ideas: set = set()
        seen_subgroups: set = set()
        seen_anchors: set = set()
        domain_families: Counter = Counter()
        rules: Counter = Counter()
        players: Counter = Counter()
        seen_texts: set[str] = set()
        seen_memberships: set = set()
        by_topic: dict[str, list[_Entry]] = {}
        # A fact that another candidate settles when shown no later ("sport or
        # reading?" beside "which hobby type is most common?") yields to it, if
        # that candidate reasons at least as far: a plain count never pushes out
        # the majority it happens to imply.
        sharing: dict[str, list[_Entry]] = {}
        for entry in remaining:
            for topic in entry.topics:
                sharing.setdefault(topic, []).append(entry)
        # Each subject has a limited budget, so it is spent on that subject's
        # strongest discovery before any weaker question from the same subject.
        settled_elsewhere = {
            id(entry) for entry in remaining
            if prefer_settling and entry.needs and any(
                other is not entry and other.hops >= entry.hops and _settled(entry.needs, entry.level, [other])
                for topic in entry.topics for other in sharing[topic])
        }
        ordered = sorted(remaining, key=lambda e: (-round(e.score, 9), e.fact_order, e.order))
        # A room's strongest discoveries are asked whatever the variety rules
        # would otherwise prefer: a group whose story is "most of us are from
        # the north" must not lose that question to a fresher reasoning pattern.
        # At most two per subject, so this cannot bring back domain dominance.
        headline: dict[int, int] = {}
        reserved: Counter = Counter()
        for entry in ordered:
            if len(headline) >= max(3, question_count // 4):
                break
            # Never reserve a question that a stronger fact already answers.
            if id(entry) in settled_elsewhere or any(reserved[g] >= 2 for g in entry.groups):
                continue
            headline[id(entry)] = len(headline)
            for group in entry.groups:
                reserved[group] += 1
        # Each subject's best remaining fact still outranks its weaker ones.
        best_of_group: dict[str, _Entry] = {}
        for entry in ordered:
            for group in entry.groups:
                best_of_group.setdefault(group, entry)
        finest = {id(entry) for entry in best_of_group.values()}
        people = 0
        selected: list[_Entry] = []

        def answered(entry: _Entry) -> bool:
            """Already answered by a selected question, or would answer one shown after it."""
            if not entry.topics:
                return False
            related = list({id(e): e for topic in entry.topics for e in by_topic.get(topic, ())}.values())
            if not related:
                return False
            if _settled(entry.needs, entry.level, related):
                return True
            return any(entry.level <= other.level and other.needs
                       and _settled(other.needs, other.level, [e for e in related if e is not other], entry.reveals)
                       for other in related)

        def allowed(entry: _Entry, relaxed: bool, variety: int = 0) -> bool:
            if entry.text_key in seen_texts or (entry.membership is not None and entry.membership in seen_memberships):
                return False
            # Wording is not identity: the same idea is never asked twice, and
            # the same reasoning about the same dimension is one idea.
            if entry.signature in seen_signatures or entry.idea in seen_ideas:
                return False
            # "Among the people from the north…" is one discovery, not two, and
            # one person's answer anchors at most one question.
            if entry.subgroup and entry.subgroup in seen_subgroups:
                return False
            if entry.anchor and entry.anchor in seen_anchors:
                return False
            if answered(entry):
                return False
            # Variety staging: a reasoning pattern is used once; it may return
            # only in a subject it has not been applied to, and repeats only
            # when nothing newer is left.
            if variety == 0 and operations[entry.idea[0]] and id(entry) not in headline:
                return False
            if variety < 2 and operations[entry.idea[0]] >= caps['operation']:
                return False
            if variety == 1 and (operations[entry.idea[0]] >= 2
                                 or any(styles[(entry.idea[0], g)] for g in entry.groups)):
                return False
            # The subject ceiling is not relaxed to fill a game: one topic taking
            # a third of the quiz is the problem this exists to prevent.
            if any(groups[g] >= caps.get(g, caps['group']) for g in entry.groups):
                return False
            if entry.person and people >= caps['person'] and id(entry) not in headline:
                return False
            if entry.candidate.source_rule_id == 'unique_value' and rules['unique_value'] >= RAW_LOOKUP_CAP:
                return False
            # Raw-answer lookups ("who chose couscous?") are capped per rule; group facts
            # about a listed choice are limited by their shared family instead.
            if (entry.kind == 'direct' and entry.family != 'DIRECT_CHOICE'
                    and rules[entry.candidate.source_rule_id] >= DIRECT_RULE_CAP):
                return False
            # Reading a raw answer back ("who is the only one from Haifa?") is a
            # warm-up, never a tenth of the game, and the few that are asked come
            # from different subjects. A fact about a listed choice ("how many
            # picked rock?") is a group fact, limited by the variety rules instead.
            lookup = entry.kind == 'direct' and entry.family != 'DIRECT_CHOICE'
            if lookup and variety < 2 and (lookups[0] >= caps['direct']
                                           or any(direct_groups[g] for g in entry.groups)):
                return False
            if 'age' in entry.candidate.source_field_keys and rules['age'] >= AGE_CAP:
                return False
            if relaxed:
                return True
            if entry.tier and families[entry.family] >= caps['supporting_family']:
                return False
            return (families[entry.family] < caps['family']
                    and all(domains[d] < caps['domain'] for d in entry.domains)
                    and domain_families[(entry.domain, entry.family)] < caps['domain_family'])

        def rank(entry: _Entry):
            target = 0 if len(selected) < question_count * 0.3 else 1 if len(selected) < question_count * 0.75 else 2
            return (
                # The headline discoveries first, strongest first; then variety
                # in the order a player notices it: a new kind of reasoning,
                # then a new subject, then a new profile answer, then a family
                # that has not been used yet.
                headline.get(id(entry), len(headline)),
                operations[entry.idea[0]],
                int(id(entry) not in finest),
                max(styles[(entry.idea[0], g)] for g in entry.groups),
                max(groups[g] for g in entry.groups),
                min((fields[f] for f in entry.fields), default=0),
                families[entry.family] + entry.tier,
                max(domains[d] for d in entry.domains),
                domain_families[(entry.domain, entry.family)],
                int(id(entry) in settled_elsewhere),
                int(bool(selected) and selected[-1].group == entry.group),
                abs(_LEVELS[entry.candidate.difficulty] - target),
                -round(entry.score, 6),
                sum(players[p] for p in entry.players),
                entry.fact_order,
            )

        # Kinds still under quota first; then any kind within the caps; only when
        # nothing else fits do family and domain caps relax, and then the most
        # varied remaining fact wins regardless of kind. A question an earlier
        # one already answers is never selected.
        while remaining and len(selected) < question_count:
            # Literal identity lookups are a last resort, never a reserved share
            # of the game. Allow one useful easy clue only when all unsettled
            # non-lookup facts have been considered, including relaxed caps.
            kinds = sorted(supply, key=lambda k: (-(quotas.get(k, 0) - picked[k]), preference.get(k, 99), k))
            choice = None
            # Unused reasoning first; then a pattern in a genuinely different
            # subject; only then a repeat. Caps relax before variety does.
            for variety in (0, 1, 2):
                eligible = [e for e in remaining if allowed(e, True, variety)]
                # Reading answers back fills a game only when discovering
                # something new is no longer possible.
                eligible = [e for e in eligible
                            if e.kind != 'direct' or e.family == 'DIRECT_CHOICE'] or eligible
                non_lookup = [e for e in eligible if e.candidate.source_rule_id != 'unique_value']
                eligible = non_lookup or eligible
                if not eligible:
                    continue
                for within_quota in (True, False):
                    for kind in kinds:
                        if within_quota and picked[kind] >= quotas.get(kind, 0):
                            continue
                        options = [e for e in eligible if e.kind == kind and allowed(e, False, variety)]
                        if options:
                            choice = min(options, key=rank)
                            break
                    if choice is not None:
                        break
                if choice is None:
                    choice = min(eligible, key=lambda e: (rank(e), kinds.index(e.kind)))
                if choice is not None:
                    break
            if choice is None:
                break
            remaining.remove(choice)
            selected.append(choice)
            picked[choice.kind] += 1
            families[choice.family] += 1
            operations[choice.idea[0]] += 1
            if choice.kind == 'direct' and choice.family != 'DIRECT_CHOICE':
                lookups[0] += 1
            for g in choice.groups:
                styles[(choice.idea[0], g)] += 1
                if choice.kind == 'direct' and choice.family != 'DIRECT_CHOICE':
                    direct_groups[g] += 1
            seen_signatures.add(choice.signature)
            seen_ideas.add(choice.idea)
            if choice.subgroup:
                seen_subgroups.add(choice.subgroup)
            if choice.anchor:
                seen_anchors.add(choice.anchor)
            domain_families[(choice.domain, choice.family)] += 1
            for d in choice.domains:
                domains[d] += 1
            for g in choice.groups:
                groups[g] += 1
            for f in choice.fields:
                fields[f] += 1
            rules[choice.candidate.source_rule_id] += 1
            if 'age' in choice.candidate.source_field_keys:
                rules['age'] += 1
            people += choice.person
            seen_texts.add(choice.text_key)
            if choice.membership is not None:
                seen_memberships.add(choice.membership)
            for topic in choice.topics:
                by_topic.setdefault(topic, []).append(choice)
            for p in choice.players:
                players[p] += 1

        return selected


def _presentation_order(selected: list[_Entry]) -> list[_Entry]:
    """Easy to hard; within a band keep selection order but avoid back-to-back domains."""
    ordered: list[_Entry] = []
    for level in (0, 1, 2):
        band = [e for e in selected if _LEVELS[e.candidate.difficulty] == level]
        while band:
            last = ordered[-1].domain if ordered else None
            pick = next((e for e in band if e.domain != last), band[0])
            band.remove(pick)
            ordered.append(pick)
    return ordered
