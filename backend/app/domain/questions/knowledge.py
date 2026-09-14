"""Immutable, offline reference facts. This domain module performs no IO.

An entity classification is a fact about a work/activity/place, never evidence
of a player's behavior, personality or unsubmitted preferences. Only exact
normalized names and explicitly reviewed aliases are eligible for scoring.
"""

from dataclasses import dataclass
from enum import Enum
from math import asin, cos, radians, sin, sqrt
from types import MappingProxyType
from collections.abc import Iterable
import re
import unicodedata

KINDS = ('movies', 'music', 'artists', 'songs', 'foods', 'hobbies', 'localities')
_HEBREW_LETTER = re.compile('[\u05d0-\u05ea]')
_DOUBLED_HEBREW_LETTER = re.compile('(?<=[\u05d0-\u05ea])(\u05d5\u05d5|\u05d9\u05d9)(?=[\u05d0-\u05ea])')


class Match(str, Enum):
    EXACT = 'EXACT'
    ALIAS = 'ALIAS'
    UNKNOWN = 'UNKNOWN'


def normalize_name(value: str) -> str:
    """Conservative token normalization, with no edit distance or guessing."""
    text = unicodedata.normalize('NFKC', value).casefold()
    text = ''.join(c for c in text if not ('\u0591' <= c <= '\u05bd' or c in '\u05bf\u05c1\u05c2\u05c4\u05c5\u05c7'))
    text = text.translate(str.maketrans({c: '' for c in "'’‘\"״׳"}))
    text = text.translate(str.maketrans({c: ' ' for c in '-‐‑‒–—־:.,'}))
    return ' '.join(text.split())


def fold_hebrew_spelling(key: str) -> str:
    """Treat full and defective Hebrew spellings alike (קריית/קרית, תקווה/תקוה).

    Only a doubled vav or yod between two Hebrew letters collapses. Used as a
    secondary lookup after the exact key misses; folded collisions fail closed.
    """
    return _DOUBLED_HEBREW_LETTER.sub(lambda match: match.group(0)[0], key)


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


UNKNOWN = Resolution(Match.UNKNOWN)


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


def _index_names(entities: Iterable[KnownEntity]) -> tuple[dict, dict, dict]:
    """Name indexes for one kind, built in a single pass.

    Returns unique name → entity, colliding name → contenders, and — only for
    names spelled with a doubled vav or yod — folded spelling → entities, so a
    defectively spelled lookup can still find them.
    """
    index, contenders, doubled = {}, {}, {}
    for entity in entities:
        for name in (entity.english, entity.hebrew, *entity.aliases):
            key = normalize_name(name)
            if not key:
                continue
            if _DOUBLED_HEBREW_LETTER.search(key):
                doubled.setdefault(fold_hebrew_spelling(key), {})[entity.canonical_id] = entity
            if key in contenders:
                contenders[key][entity.canonical_id] = entity
                continue
            previous = index.get(key)
            if previous is None:
                index[key] = entity
            elif previous.canonical_id != entity.canonical_id:
                del index[key]
                contenders[key] = {previous.canonical_id: previous, entity.canonical_id: entity}
    return index, contenders, doubled


class KnowledgeBase:
    """Read-only entity/category graph with O(1) normalized-name lookup.

    Name collisions fail closed even when one contender uses a canonical
    label and the other uses an alias. There is deliberately no fuzzy API.
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
        indexes, contenders, doubled = {}, {}, {}
        for kind, members in by_kind.items():
            index, collisions, spellings = _index_names(members)
            indexes[kind] = MappingProxyType(index)
            contenders[kind] = MappingProxyType({k: tuple(v.values()) for k, v in collisions.items()})
            doubled[kind] = MappingProxyType({k: tuple(v.values()) for k, v in spellings.items()})
        self._indexes = MappingProxyType(indexes)
        self._contenders = MappingProxyType(contenders)
        self._doubled = MappingProxyType(doubled)
        self.ambiguous_names = MappingProxyType({k: frozenset(v) for k, v in contenders.items()})
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
        """Every entity named ``key`` under another Hebrew spelling (קרית/קריית)."""
        folded = fold_hebrew_spelling(key)
        group = {e.canonical_id: e for e in self._doubled[kind].get(folded, ())}
        entity = self._indexes[kind].get(folded)
        if entity is not None:
            group[entity.canonical_id] = entity
        for contender in self._contenders[kind].get(folded, ()):
            group[contender.canonical_id] = contender
        return tuple(group.values())

    def resolve(self, kind: str, text: str) -> Resolution:
        if kind not in self._indexes or not isinstance(text, str) or len(text) > 200:
            return UNKNOWN
        key = normalize_name(text)
        entity = self._indexes[kind].get(key)
        if entity is None:
            # A different Hebrew spelling of a unique name; never of an ambiguous one.
            if key in self.ambiguous_names[kind] or not _HEBREW_LETTER.search(key):
                return UNKNOWN
            group = self._spelling_group(kind, key)
            return Resolution(Match.ALIAS, group[0]) if len(group) == 1 else UNKNOWN
        exact = key in (normalize_name(entity.english), normalize_name(entity.hebrew))
        return Resolution(Match.EXACT if exact else Match.ALIAS, entity)

    def classify(self, kind: str, text: str) -> Classification:
        """Categories for a typed name: the entity's own, or those all same-name contenders share."""
        resolution = self.resolve(kind, text)
        if resolution.entity is not None:
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
