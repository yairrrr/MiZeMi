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
import unicodedata

KINDS = ('movies', 'music', 'artists', 'foods', 'hobbies', 'localities')


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

    def label(self, language: str) -> str:
        return (self.hebrew or self.english) if language == 'he' else self.english


@dataclass(frozen=True, slots=True)
class Resolution:
    match: Match
    entity: KnownEntity | None = None


UNKNOWN = Resolution(Match.UNKNOWN)


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
        indexes = {}
        ambiguous = {}
        for kind in KINDS:
            matches: dict[str, set[str]] = {}
            for e in all_entities:
                if e.kind != kind:
                    continue
                for name in (e.english, e.hebrew, *e.aliases):
                    key = normalize_name(name)
                    if key:
                        matches.setdefault(key, set()).add(e.canonical_id)
            indexes[kind] = MappingProxyType({key: self.entities[kind, next(iter(ids))]
                                            for key, ids in matches.items() if len(ids) == 1})
            ambiguous[kind] = frozenset(key for key, ids in matches.items() if len(ids) > 1)
        self._indexes = MappingProxyType(indexes)
        self.ambiguous_names = MappingProxyType(ambiguous)
        self._facets = MappingProxyType({(e.kind, e.canonical_id): MappingProxyType({
            dim: frozenset(c for c in e.category_ids if self.categories[c].dimension == dim)
            for dim in {self.categories[c].dimension for c in e.category_ids}
        }) for e in all_entities})

    def resolve(self, kind: str, text: str) -> Resolution:
        if kind not in self._indexes or not isinstance(text, str) or len(text) > 200:
            return UNKNOWN
        entity = self._indexes[kind].get(normalize_name(text))
        if entity is None:
            return UNKNOWN
        exact = normalize_name(text) in (normalize_name(entity.english), normalize_name(entity.hebrew))
        return Resolution(Match.EXACT if exact else Match.ALIAS, entity)

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

    def resolve_israeli_locality(self, text: str) -> Resolution:
        return self.resolve('localities', text)

    def facts(self, entity: KnownEntity, dimension: str) -> frozenset[str]:
        return self._facets.get((entity.kind, entity.canonical_id), {}).get(dimension, frozenset())

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
