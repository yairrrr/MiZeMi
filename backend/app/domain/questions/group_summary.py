"""Category-first stage: consented answers → classifications → per-dimension group facts.

Every question-approved answer is classified once per generation into the
comparable categories of each semantic dimension ("Saw" → horror, "ריצה" →
sport, "חיפה" → the north). Discovery families then reason over these group
summaries instead of raw answers, so coverage, unknowns and consent are
handled in exactly one place.

Answer accounting, per dimension (thresholds live in ``CoveragePolicy``):

* consented — the field was shared for questions. A withheld answer is not an
  unknown; it does not exist here and changes no count or denominator.
* classified — belongs to one or more compared categories.
* neutral — recognized, but deliberately in none of them (a hobby done
  anywhere, the "Other" music choice). A known non-member.
* unknown — shared but not classifiable: unrecognized text, a name without a
  shared classification, or a work too broadly classified to count. Unknown
  is never read as "not a member".

Categories are compared only at one taxonomy level per dimension: broad hobby
families (running's "fitness" label folds into sport), cuisine families
(Japanese, Chinese, Thai, Korean and Indian dishes are Asian food; the
reference tag that also files hummus under "Asian" is not used), music
families (trance is electronic music).
"""

import re
from dataclasses import dataclass
from functools import cached_property
from math import ceil
from types import MappingProxyType

from app.domain.questions.knowledge import KnowledgeBase, KnownEntity, distance_km
from app.domain.questions.semantic import classify_shared

_DISAMBIGUATION = re.compile(r'\s*\([^()]*\)$')  # "Titanic (1997 film)", "לה לה לנד (סרט)"
_HEBREW = re.compile('[\u05d0-\u05ea]')


@dataclass(frozen=True)
class CoveragePolicy:
    """When a group summary is strong enough for a given kind of claim.

    * ``min_answers``: shared answers before any group question about a dimension.
      Small groups still get neutral counts and comparisons; strong wording
      ("the most popular in the group") needs ``strong_min_recognized``.
    * ``count_coverage``: counts ("how many chose a horror movie?") state
      recognized members and explain the recognition rate when below 100%.
    * ``comparison_coverage`` and ``strong_coverage`` (majority, "most popular",
      minority): these claims also need a decisive lead — larger than the number
      of unknown answers — so no classification of those unknowns could change
      the correct option. Claims about "the group" also need at least
      ``strong_min_participation`` of the room to have shared the answer, and
      "most of the group" is only said of more than half of the visible room
      (room size is public; no withheld value is ever read).
    * Exclusive claims ("only one person…", "how many different…", "who lives
      furthest north") are only made when every shared answer is recognized.
    """

    min_answers: int = 3
    count_coverage: float = 0.75
    comparison_coverage: float = 0.70
    strong_coverage: float = 0.80
    strong_min_recognized: int = 5
    strong_min_share: float = 0.20
    strong_min_participation: float = 0.50
    subgroup_min_share: float = 0.20
    subgroup_min_size: int = 3


POLICY = CoveragePolicy()
MEDIA_DIMENSIONS = ('movie.genre', 'artist.genre', 'song.genre')
MEDIA_DOMAINS = ('movie', 'artist', 'song')

MOVIE_MAX_GENRES = 5
CUISINES = ('food.italian', 'food.asian', 'food.middle_eastern', 'food.american', 'food.mexican',
            'food.french', 'food.greek', 'food.spanish', 'food.north_african', 'food.jewish',
            'food.eastern_european', 'food.british', 'food.south_american')
ASIAN_CUISINES = tuple((c, 'food.asian') for c in
                       ('food.japanese', 'food.chinese', 'food.thai', 'food.korean', 'food.indian'))
HOBBY_FAMILIES = ('hobby.sport', 'hobby.creative', 'hobby.digital', 'hobby.table_games', 'hobby.nature',
                  'hobby.learning', 'hobby.cooking', 'hobby.collecting', 'hobby.wellbeing',
                  'hobby.social', 'hobby.travel')
MUSIC_FAMILIES = ('music.pop', 'music.rock', 'music.hiphop', 'music.electronic', 'music.mizrahi',
                  'music.mediterranean', 'music.classical', 'music.jazz', 'music.indie', 'music.rnb',
                  'music.reggae', 'music.folk', 'music.country', 'music.blues', 'music.soul',
                  'music.funk', 'music.gospel', 'music.latin', 'music.disco', 'music.ska')
MUSIC_PARENTS = (('music.house', 'music.electronic'), ('music.techno', 'music.electronic'),
                 ('music.trance', 'music.electronic'), ('music.metal', 'music.rock'))
REGIONS = ('region.north', 'region.central', 'region.south', 'region.jerusalem')


@dataclass(frozen=True)
class SemanticDimension:
    """One way of grouping a profile field through reference classifications."""

    key: str
    domain: str
    field: str
    kind: str
    facet: str
    comparable: tuple[str, ...] = ()  # empty: every category the knowledge base defines for ``facet``
    parents: tuple[tuple[str, str], ...] = ()
    ignored: frozenset[str] = frozenset()
    neutral: frozenset[str] = frozenset()
    neutral_values: frozenset[str] = frozenset()
    max_labels: int = 0

    @property
    def selection_domain(self) -> str:
        """Artists and songs share a taxonomy, but represent independent player choices."""
        return self.key.split('.')[0] if self.key in MEDIA_DIMENSIONS else self.domain


DIMENSIONS = (
    SemanticDimension('movie.genre', 'movie', 'favorite_movie', 'movies', 'movie.genre',
                      max_labels=MOVIE_MAX_GENRES),
    SemanticDimension('food.cuisine', 'food', 'favorite_food', 'foods', 'food.cuisine', CUISINES,
                      parents=ASIAN_CUISINES, ignored=frozenset({'food.asian'}), max_labels=2),
    SemanticDimension('hobby.family', 'hobby', 'hobby', 'hobbies', 'hobby.family', HOBBY_FAMILIES,
                      max_labels=3),
    SemanticDimension('hobby.physical', 'hobby', 'hobby', 'hobbies', 'hobby.physical',
                      ('activity.physical', 'activity.nonphysical')),
    SemanticDimension('hobby.setting', 'hobby', 'hobby', 'hobbies', 'hobby.setting',
                      ('setting.outdoor', 'setting.indoor'), neutral=frozenset({'setting.flexible'})),
    SemanticDimension('music.genre', 'music', 'favorite_music', 'music', 'music.genre', MUSIC_FAMILIES,
                      parents=MUSIC_PARENTS, neutral_values=frozenset({'Other'}), max_labels=3),
    SemanticDimension('artist.genre', 'music', 'favorite_artist', 'artists', 'music.genre', MUSIC_FAMILIES,
                      parents=MUSIC_PARENTS, max_labels=3),
    SemanticDimension('song.genre', 'music', 'favorite_song', 'songs', 'music.genre', MUSIC_FAMILIES,
                      parents=MUSIC_PARENTS, max_labels=3),
    SemanticDimension('place.region', 'place', 'city', 'localities', 'place.region', REGIONS),
)
DIMENSIONS_BY_KEY = MappingProxyType({d.key: d for d in DIMENSIONS})


class DimensionSummary:
    """Who belongs to which comparable category of one dimension, and how sure we are."""

    def __init__(self, dimension: SemanticDimension, dataset, knowledge: KnowledgeBase) -> None:
        self.dimension = dimension
        self.group_size = dataset.player_count
        defined = dimension.comparable or tuple(sorted(
            c.category_id for c in knowledge.categories.values() if c.dimension == dimension.facet))
        self.categories = tuple(c for c in defined if c in knowledge.categories)
        allowed, parents = frozenset(self.categories), dict(dimension.parents)
        consented, classified, neutral, unknown = [], {}, [], []
        evidence, entities, typed = {}, {}, {}
        for player_id, value in dataset.values_for(dimension.field):
            consented.append(player_id)
            typed[player_id] = ' '.join(str(value).split())
            if not isinstance(value, str):
                unknown.append(player_id)
                continue
            if value in dimension.neutral_values:
                neutral.append(player_id)
                continue
            result = classify_shared(dataset, knowledge, dimension.kind, value)
            facts = knowledge.facet(result.category_ids, dimension.facet) - dimension.ignored
            labels = frozenset(parents.get(c, c) for c in facts) & allowed
            if result.entity is not None:
                entities[player_id] = result.entity
            if labels and (not dimension.max_labels or len(labels) <= dimension.max_labels):
                classified[player_id] = labels
                evidence[player_id] = result.entity if result.entity is not None else value
            elif not labels and facts & dimension.neutral:
                neutral.append(player_id)
            else:
                unknown.append(player_id)
        self.consented = tuple(consented)
        self.classified = MappingProxyType(classified)
        self.neutral = tuple(neutral)
        self.unknown = tuple(unknown)
        self.recognized = tuple(p for p in consented if p in classified or p in neutral)
        self._evidence = MappingProxyType(evidence)
        self._typed = MappingProxyType(typed)
        self.entities = MappingProxyType(entities)
        self.members = MappingProxyType({
            category: tuple(p for p in consented if category in classified.get(p, ()))
            for category in self.categories
        })

    @property
    def coverage(self) -> float:
        return len(self.recognized) / len(self.consented) if self.consented else 0.0

    def count(self, category: str) -> int:
        return len(self.members.get(category, ()))

    def represented(self) -> tuple[str, ...]:
        """Categories with at least one member, in taxonomy order."""
        return tuple(c for c in self.categories if self.members[c])

    def evidence_label(self, player_id: str, language: str) -> str:
        """A recognized choice as the group knows it: what the player typed.

        The reference label (without disambiguation such as "(1997 film)") is
        used only when the typed text is in the other game language's script.
        """
        typed = self._typed[player_id]
        choice = self._evidence.get(player_id)
        if not isinstance(choice, KnownEntity) or bool(_HEBREW.search(typed)) == (language == 'he'):
            return typed
        label = choice.label(language)
        return _DISAMBIGUATION.sub('', label) or label

    def town(self, player_id: str, language: str) -> str:
        """A shared town as the player wrote it (or its reference name in the game's script)."""
        typed = self._typed[player_id]
        entity = self.entities.get(player_id)
        if entity is None or bool(_HEBREW.search(typed)) == (language == 'he'):
            return typed
        return _DISAMBIGUATION.sub('', entity.label(language)) or entity.label(language)

    def choice_key(self, player_id: str) -> str:
        """Identity of what the player actually chose: a reference entity or the typed text."""
        choice = self._evidence[player_id]
        return choice.canonical_id if isinstance(choice, KnownEntity) else str(choice).casefold()

    def literal(self, people) -> bool:
        """True when grouping adds nothing: these people all picked the very same listed choice.

        Only fixed-choice fields qualify (favorite music): "how many chose pop?"
        about a pop-choice field is a direct question, not a discovery.
        """
        return bool(self.dimension.neutral_values) and len({self.choice_key(p) for p in people}) <= 1

    def non_members(self, category: str) -> tuple[str, ...]:
        """Recognized players known not to belong to ``category``."""
        return tuple(p for p in self.recognized if p not in self.members.get(category, ()))

    def counts_within(self, people) -> dict[str, int]:
        chosen = set(people)
        return {c: sum(p in chosen for p in self.members[c]) for c in self.categories}

    def eligible_for_count(self, policy: CoveragePolicy = POLICY) -> bool:
        return (len(self.consented) >= policy.min_answers and len(self.recognized) >= policy.min_answers
                and self.coverage >= policy.count_coverage)

    def eligible_for_comparison(self, policy: CoveragePolicy = POLICY) -> bool:
        return (len(self.consented) >= policy.min_answers and len(self.recognized) >= policy.min_answers
                and self.coverage >= policy.comparison_coverage)

    def eligible_for_strong_claim(self, policy: CoveragePolicy = POLICY) -> bool:
        return (len(self.recognized) >= policy.strong_min_recognized
                and self.coverage >= policy.strong_coverage
                and len(self.consented) >= policy.strong_min_participation * self.group_size)

    def eligible_for_media_leader(self, policy: CoveragePolicy = POLICY) -> bool:
        """A leader among shared media choices, not a claim about everyone's taste.

        Three recognized choices can support this even when other participants
        skip the optional field. A decisive lead is still proved separately;
        neither an unknown nor a withheld answer becomes a negative membership.
        """
        return (self.dimension.key in MEDIA_DIMENSIONS
                and len(self.recognized) >= policy.min_answers
                and self.coverage >= policy.strong_coverage)

    @property
    def complete(self) -> bool:
        """Every shared answer recognized — required for exclusive claims."""
        return bool(self.consented) and not self.unknown


def decisive_leader(counts: dict[str, int], unknown: int, order: tuple[str, ...]) -> tuple[str, int] | None:
    """The top category and its runner-up count, if unknown answers cannot overturn it."""
    ranked = sorted(counts, key=lambda c: (-counts[c], order.index(c)))
    if not ranked or counts[ranked[0]] == 0:
        return None
    runner_up = counts[ranked[1]] if len(ranked) > 1 else 0
    if counts[ranked[0]] - runner_up <= unknown:
        return None
    return ranked[0], runner_up


def meaningful_leader(summary: DimensionSummary, counts: dict[str, int], policy: CoveragePolicy = POLICY):
    """A decisive leader that also represents a real share of the recognized answers."""
    leader = decisive_leader(counts, len(summary.unknown), summary.categories)
    if leader is None:
        return None
    needed = max(2, ceil(policy.strong_min_share * len(summary.recognized)))
    return leader if counts[leader[0]] >= needed else None


class GroupSummary:
    """All dimension summaries for one consent-safe dataset; built once per generation."""

    def __init__(self, dataset, knowledge: KnowledgeBase) -> None:
        self.dataset = dataset
        self.knowledge = knowledge
        self.dimensions = MappingProxyType({
            d.key: DimensionSummary(d, dataset, knowledge)
            for d in DIMENSIONS if dataset.values_for(d.field)
        })

    def get(self, key: str) -> DimensionSummary | None:
        return self.dimensions.get(key)

    def name(self, player_id: str) -> str:
        return self.dataset.display_name_for(player_id)

    def subgroup_min_size(self, policy: CoveragePolicy = POLICY) -> int:
        return max(policy.subgroup_min_size, ceil(policy.subgroup_min_share * self.dataset.player_count))

    @cached_property
    def places(self) -> dict[str, KnownEntity]:
        """Uniquely identified towns for coordinate questions; empty unless every shared town is."""
        region = self.get('place.region')
        if region is None or len(region.entities) != len(region.consented):
            return {}
        return {p: region.entities[p] for p in region.consented
                if region.entities[p].coordinates is not None}

    @cached_property
    def distances(self) -> dict[tuple[str, str], float]:
        places = self.places
        ids = tuple(places)
        return {(a, b): distance_km(places[a], places[b])
                for i, a in enumerate(ids) for b in ids[i + 1:]}


def summarize(dataset, knowledge: KnowledgeBase) -> GroupSummary:
    """The shared summary for this dataset, cached on the dataset object itself.

    The summary holds only data copied from the consent-safe dataset and is
    language independent, so rules generating in either language share it.
    No cache crosses a room boundary.
    """
    cached = getattr(dataset, '_group_summary', None)
    if cached is None or cached.knowledge is not knowledge:
        cached = GroupSummary(dataset, knowledge)
        dataset._group_summary = cached
    return cached


__all__ = ['POLICY', 'CoveragePolicy', 'DIMENSIONS', 'DIMENSIONS_BY_KEY',
           'DimensionSummary', 'GroupSummary', 'SemanticDimension', 'decisive_leader',
           'meaningful_leader', 'summarize']
