"""Immutable, offline reference facts. This domain module performs no IO.

An entity classification is a fact about a work/activity/place, never evidence
of a player's behavior, personality or unsubmitted preferences. Identity is
returned only after a deterministic high-confidence match; uncertain partial
names and typos never contribute categories to scored questions.
"""

from dataclasses import dataclass
from enum import Enum
from math import asin, cos, radians, sin, sqrt
from types import MappingProxyType
from collections.abc import Iterable
import re
import unicodedata

from app.domain.questions.name_matching import NameSearch, fold_hebrew_spelling

KINDS = ('movies', 'music', 'artists', 'songs', 'foods', 'hobbies', 'localities')
_HEBREW_LETTER = re.compile('[\u05d0-\u05ea]')


class Match(str, Enum):
    EXACT = 'EXACT'
    ALIAS = 'ALIAS'
    NORMALIZED = 'NORMALIZED'
    PARTIAL_HIGH_CONFIDENCE = 'PARTIAL_HIGH_CONFIDENCE'
    FUZZY_HIGH_CONFIDENCE = 'FUZZY_HIGH_CONFIDENCE'
    AMBIGUOUS = 'AMBIGUOUS'
    UNKNOWN = 'UNKNOWN'


def normalize_name(value: str) -> str:
    """Unicode, case, whitespace, Hebrew marks/quotes and punctuation only."""
    text = unicodedata.normalize('NFKC', value).casefold()
    text = ''.join(c for c in text if not ('\u0591' <= c <= '\u05bd' or c in '\u05bf\u05c1\u05c2\u05c4\u05c5\u05c7'))
    text = text.translate(str.maketrans({c: '' for c in "'’‘`´\"“”„״׳"}))
    text = ''.join(' ' if unicodedata.category(c) == 'Pd' or c in ':.,;!?()/\\' else c for c in text)
    return ' '.join(text.split())


@dataclass(frozen=True, slots=True)
class Category:
    category_id: str
    dimension: str
    english: str
    hebrew: str

    def label(self, language: str) -> str:
        return self.hebrew if language == 'he' else self.english


@dataclass(frozen=True, slots=True)
class KnownEntity:
    canonical_id: str
    kind: str
    english: str
    hebrew: str
    aliases: tuple[str, ...]
    category_ids: frozenset[str]
    coordinates: tuple[float, float] | None = None
    source_revision: int = 0
    year: int | None = None
    country_ids: tuple[str, ...] = ()
    series_ids: tuple[str, ...] = ()
    performer_ids: tuple[str, ...] = ()
    locality_type: str = ""

    def label(self, language: str) -> str:
        return (self.hebrew or self.english) if language == 'he' else self.english


@dataclass(frozen=True, slots=True)
class Resolution:
    match: Match
    entity: KnownEntity | None = None
    similarity: float | None = None
    runner_up_similarity: float | None = None
    candidate_count: int = 0
    reason: str = ''

    @property
    def high_confidence(self) -> bool:
        return self.entity is not None and self.match not in (Match.UNKNOWN, Match.AMBIGUOUS)


UNKNOWN = Resolution(Match.UNKNOWN, reason='no_supported_match')


@dataclass(frozen=True, slots=True)
class Classification:
    """Reference categories for one typed name.

    ``entity`` is set only for a unique match. A name shared by several
    reference entities (remakes, homonyms) keeps identity unknown and exposes
    only the categories every contender shares: whichever "Titanic" a player
    meant, it is a drama. Identity-based facts (coordinates, canonical
    titles) stay unavailable for such names.
    """

    entity: KnownEntity | None
    category_ids: frozenset[str]


UNCLASSIFIED = Classification(None, frozenset())


def _index_names(entities: Iterable[KnownEntity]) -> tuple[dict, dict]:
    """Name indexes for one kind, built in a single pass.

    Returns unique name → entity and colliding name → contenders. Additional
    spelling variants belong to the compact NameSearch index.
    """
    index, contenders = {}, {}
    for entity in entities:
        for name in (entity.english, entity.hebrew, *entity.aliases):
            key = normalize_name(name)
            if not key:
                continue
            if key in contenders:
                contenders[key][entity.canonical_id] = entity
                continue
            previous = index.get(key)
            if previous is None:
                index[key] = entity
            elif previous.canonical_id != entity.canonical_id:
                del index[key]
                contenders[key] = {previous.canonical_id: previous, entity.canonical_id: entity}
    return index, contenders


class KnowledgeBase:
    """Read-only entity/category graph with O(1) literal/normalized lookup.

    Name collisions fail closed even when one contender uses a canonical
    label and the other uses an alias. Approximate search is bounded, rejects
    near competitors and returns no entity on ambiguous or unsupported input.
    Construction is pure; the infrastructure loader owns schema validation.
    """

    def __init__(self, entities: Iterable[KnownEntity], categories: Iterable[Category], version: str):
        self.version = version
        self.categories = MappingProxyType({c.category_id: c for c in categories})
        all_entities = tuple(entities)
        self.entities = MappingProxyType({(e.kind, e.canonical_id): e for e in all_entities})
        by_kind = {kind: [] for kind in KINDS}
        for entity in all_entities:
            by_kind[entity.kind].append(entity)
        indexes, contenders = {}, {}
        for kind, members in by_kind.items():
            index, collisions = _index_names(members)
            indexes[kind] = MappingProxyType(index)
            contenders[kind] = MappingProxyType({k: tuple(v.values()) for k, v in collisions.items()})
        self._indexes = MappingProxyType(indexes)
        self._contenders = MappingProxyType(contenders)
        self.ambiguous_names = MappingProxyType({k: frozenset(v) for k, v in contenders.items()})
        gram_pool = {}
        self._search = {kind: NameSearch((*indexes[kind], *contenders[kind]), kind, gram_pool) for kind in KINDS}
        # Thousands of works share a small number of classification combinations.
        # Cache one facet map per combination, not per entity.
        facets = {}
        for entity in all_entities:
            facts = entity.category_ids
            if facts not in facets:
                facets[facts] = MappingProxyType({
                    dim: frozenset(c for c in facts if self.categories[c].dimension == dim)
                    for dim in {self.categories[c].dimension for c in facts}
                })
        self._facets = MappingProxyType(facets)

    def _spelling_group(self, kind: str, key: str) -> tuple[KnownEntity, ...]:
        """Every contender under a conservative Hebrew spelling fold."""
        return self._named_group(kind, self._search[kind].spelling_names(key))

    def _named_group(self, kind: str, names: Iterable[str]) -> tuple[KnownEntity, ...]:
        group = {}
        for name in names:
            entity = self._indexes[kind].get(name)
            if entity is not None:
                group[entity.canonical_id] = entity
            for contender in self._contenders[kind].get(name, ()):
                group[contender.canonical_id] = contender
        return tuple(group[k] for k in sorted(group))

    def resolve(self, kind: str, text: str) -> Resolution:
        if kind not in self._indexes or not isinstance(text, str) or len(text) > 200:
            return UNKNOWN
        key = normalize_name(text)
        if not key or any(unicodedata.category(c) == 'Cc' and not c.isspace() for c in text):
            return UNKNOWN
        if key in self.ambiguous_names[kind]:
            return Resolution(Match.AMBIGUOUS, candidate_count=len(self._contenders[kind][key]), reason='name_collision')
        entity = self._indexes[kind].get(key)
        if entity is not None:
            match = Match.EXACT if text in (entity.english, entity.hebrew) else Match.ALIAS if text in entity.aliases else Match.NORMALIZED
            return Resolution(match, entity, 1.0, candidate_count=1, reason='unique_full_name')
        if _HEBREW_LETTER.search(key):
            group = self._spelling_group(kind, key)
            if len(group) > 1:
                return Resolution(Match.AMBIGUOUS, candidate_count=len(group), reason='spelling_collision')
            if group:
                return Resolution(Match.NORMALIZED, group[0], 1.0, candidate_count=1, reason='hebrew_spelling')
        search = self._search[kind]
        partial = search.partial_names(key)
        if partial is None:
            return Resolution(Match.AMBIGUOUS, reason='partial_search_too_broad')
        group = self._named_group(kind, partial)
        if len(group) > 1:
            return Resolution(Match.AMBIGUOUS, candidate_count=len(group), reason='partial_collision')
        if group and any(search.partial_is_strong(key, name) for name in partial):
            return Resolution(Match.PARTIAL_HIGH_CONFIDENCE, group[0], 1.0, candidate_count=1, reason='unique_token_partial')
        # A weak partial is not promoted by a later fuzzy guess.
        if partial:
            return Resolution(Match.UNKNOWN, reason='partial_too_weak')
        fuzzy = search.fuzzy_names(key)
        if fuzzy is None:
            return Resolution(Match.AMBIGUOUS, reason='fuzzy_search_too_broad')
        scores = {}
        distances = {}
        entities = {}
        for name, distance, score in fuzzy:
            # Approximation cannot use orthography to break a known Hebrew
            # spelling collision that normalization itself would reject.
            names = self._search[kind].spelling_names(name) if _HEBREW_LETTER.search(name) else (name,)
            for entity in self._named_group(kind, (name, *names)):
                eid = entity.canonical_id
                if score > scores.get(eid, -1):
                    scores[eid], distances[eid], entities[eid] = score, distance, entity
        ranked = sorted(scores, key=lambda eid: (-scores[eid], eid))
        if not ranked:
            return UNKNOWN
        best = ranked[0]
        score = scores[best]
        runner = scores[ranked[1]] if len(ranked) > 1 else 0.0
        if distances[best] != 1 or score < search.policy.similarity:
            return Resolution(Match.UNKNOWN, similarity=score, runner_up_similarity=runner,
                              candidate_count=len(ranked), reason='below_fuzzy_threshold')
        if score - runner < search.policy.margin:
            return Resolution(Match.AMBIGUOUS, similarity=score, runner_up_similarity=runner,
                              candidate_count=len(ranked), reason='fuzzy_margin')
        return Resolution(Match.FUZZY_HIGH_CONFIDENCE, entities[best], score, runner, len(ranked), 'one_edit_clear_margin')

    def classify(self, kind: str, text: str) -> Classification:
        """Categories for a typed name: the entity's own, or those all same-name contenders share."""
        resolution = self.resolve(kind, text)
        if resolution.high_confidence:
            return Classification(resolution.entity, resolution.entity.category_ids)
        if kind not in self._indexes or not isinstance(text, str) or len(text) > 200:
            return UNCLASSIFIED
        key = normalize_name(text)
        group = self._contenders[kind].get(key)
        if group is None and _HEBREW_LETTER.search(key):
            group = self._spelling_group(kind, key)
        if not group or len(group) < 2:
            return UNCLASSIFIED
        shared = frozenset.intersection(*(e.category_ids for e in group))
        return Classification(None, shared) if shared else UNCLASSIFIED

    def resolve_movie(self, text: str) -> Resolution:
        return self.resolve('movies', text)

    def resolve_food(self, text: str) -> Resolution:
        return self.resolve('foods', text)

    def resolve_hobby(self, text: str) -> Resolution:
        return self.resolve('hobbies', text)

    def resolve_music_genre(self, text: str) -> Resolution:
        return self.resolve('music', text)

    def resolve_artist(self, text: str) -> Resolution:
        return self.resolve('artists', text)

    def resolve_song(self, text: str) -> Resolution:
        return self.resolve('songs', text)

    def resolve_israeli_locality(self, text: str) -> Resolution:
        return self.resolve('localities', text)

    def facts(self, entity: KnownEntity, dimension: str) -> frozenset[str]:
        return self.facet(entity.category_ids, dimension)

    def facet(self, category_ids: frozenset[str], dimension: str) -> frozenset[str]:
        cached = self._facets.get(category_ids)
        if cached is not None:
            return cached.get(dimension, frozenset())
        return frozenset(c for c in category_ids
                         if c in self.categories and self.categories[c].dimension == dimension)

    def in_kind(self, kind: str) -> tuple[KnownEntity, ...]:
        return tuple(e for e in self.entities.values() if e.kind == kind)


def distance_km(a: KnownEntity, b: KnownEntity) -> float:
    """Great-circle distance between locality reference points, not homes."""
    if a.coordinates is None or b.coordinates is None:
        raise ValueError('coordinates required')
    lat1, lon1 = map(radians, a.coordinates)
    lat2, lon2 = map(radians, b.coordinates)
    h = sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return 6371.0088 * 2 * asin(sqrt(min(1.0, max(0.0, h))))
