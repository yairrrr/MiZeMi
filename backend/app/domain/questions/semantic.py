"""Consent-only semantic snapshot, shared by all rules during one generation.

UNKNOWN and withheld are never false. A global comparison is eligible only
when every participant supplied a resolvable, consented fact for its dimension.
Reference classifications are positive memberships, not exhaustive exclusions.
"""
from collections import Counter
from functools import cached_property
from itertools import combinations
from types import MappingProxyType

from app.domain.questions.knowledge import KnowledgeBase, distance_km

DIMENSIONS = {
    'movie.genre': ('favorite_movie', 'movies', 'film genres', 'ז׳אנרים בקולנוע', 'movies', 'סרטים'),
    'music.genre': ('favorite_music', 'music', 'music styles', 'סגנונות מוזיקה', 'music selections', 'בחירות מוזיקליות'),
    'food.cuisine': ('favorite_food', 'foods', 'cuisines', 'מטבחים', 'foods', 'מאכלים'),
    'food.format': ('favorite_food', 'foods', 'food families', 'משפחות מאכלים', 'foods', 'מאכלים'),
    'hobby.family': ('hobby', 'hobbies', 'activity families', 'משפחות תחביבים', 'hobbies', 'תחביבים'),
    'artist.genre': ('favorite_artist', 'artists', 'music styles', 'סגנונות מוזיקה', 'artists', 'אמנים'),
    'song.genre': ('favorite_song', 'songs', 'music styles', 'סגנונות מוזיקה', 'songs', 'שירים'),
    'hobby.setting': ('hobby', 'hobbies', 'activity settings', 'מקומות פעילות', 'hobbies', 'תחביבים'),
    'hobby.physical': ('hobby', 'hobbies', 'activity types', 'סוגי פעילות', 'hobbies', 'תחביבים'),
    'place.region': ('city', 'localities', 'regions', 'אזורים בארץ', 'towns', 'יישובים'),
    'place.district': ('city', 'localities', 'districts', 'מחוזות', 'towns', 'יישובים'),
}


class SemanticView:
    def __init__(self, dataset, knowledge: KnowledgeBase):
        self.dataset, self.knowledge = dataset, knowledge
        self.ids = dataset.player_ids
        rows = {}
        for dimension, (field,kind,*_) in DIMENSIONS.items():
            if field in rows:
                continue
            rows[field] = MappingProxyType({pid: result.entity for pid,value in dataset.values_for(field)
                                          if (result := knowledge.resolve(kind,value)).entity is not None})
        self.rows = MappingProxyType(rows)
        self.memberships = MappingProxyType({dim: MappingProxyType({p: knowledge.facts(e, 'music.genre' if dim in ('artist.genre','song.genre') else dim)
            for p,e in rows[field].items() if knowledge.facts(e, 'music.genre' if dim in ('artist.genre','song.genre') else dim)})
            for dim,(field,*_) in DIMENSIONS.items()})

    def complete(self, *dimensions):
        return bool(self.ids) and all(len(self.memberships[d]) == len(self.ids) for d in dimensions)

    def entities(self, dim):
        return self.rows[DIMENSIONS[dim][0]]

    def groups(self, dim, people=None):
        groups = {}
        for p in people if people is not None else self.ids:
            for category in sorted(self.memberships[dim].get(p, ())):
                groups.setdefault(category, []).append(p)
        return groups

    def counts(self, dim, people=None):
        return Counter({cat:len(ids) for cat,ids in self.groups(dim,people).items()})

    def name(self, pid):
        return self.dataset.display_name_for(pid)

    def pair_name(self, pair):
        return ' + '.join(self.name(p) for p in pair)

    def label(self, category):
        return self.knowledge.categories[category].label(self.dataset.language)

    def dimension_label(self, dim):
        return DIMENSIONS[dim][3 if self.dataset.language == 'he' else 2]

    def subject(self, dim):
        return DIMENSIONS[dim][5 if self.dataset.language == 'he' else 4]

    def evidence(self, dim, category, people):
        # Canonical works, not raw/private profiles. Stable order, bounded prose.
        entities = dict.fromkeys(self.entities(dim)[p] for p in people)
        names = ', '.join('“'+e.label(self.dataset.language)+'”' for e in list(entities)[:4])
        suffix = ' ועוד' if self.dataset.language == 'he' else ' and others'
        return names + (suffix if len(entities)>4 else '')

    @cached_property
    def raw_alias_collisions(self):
        """Legacy literal grouping must not split a known bilingual synonym."""
        from app.domain.questions.language import normalize
        collisions=set()
        for field,entities in self.rows.items():
            spellings={}
            for pid,value in self.dataset.values_for(field):
                if pid in entities:
                    spellings.setdefault(entities[pid].canonical_id,set()).add(normalize(value))
            if any(len(names)>1 for names in spellings.values()): collisions.add(field)
        return frozenset(collisions)

    @cached_property
    def distances(self):
        places = self.rows['city']
        if len(places) != len(self.ids):
            return {}
        return {pair: distance_km(places[pair[0]],places[pair[1]]) for pair in combinations(self.ids,2)}


def enrich(dataset, knowledge):
    # The snapshot itself contains only copied consented fields; no Player or
    # raw-profile object is retained. No cache crosses a room boundary.
    cached = getattr(dataset, '_semantic_view', None)
    if cached is None or cached.knowledge is not knowledge or cached.dataset.language != dataset.language:
        cached = SemanticView(dataset, knowledge)
        dataset._semantic_view = cached
    return cached
