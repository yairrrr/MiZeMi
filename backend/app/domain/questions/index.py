"""Cached consent-only indexes; equality keys and display values stay separate."""

from itertools import combinations

from app.domain.questions.language import PREFERENCE_FIELDS, normalize


class DatasetIndex:
    def __init__(self, dataset):
        self.dataset = dataset
        self.ids = dataset.player_ids
        self.rows = {pid: {f.field_key: f.value for f in dataset.fields_for(pid)} for pid in self.ids}
        self.keys = {pid: {k: normalize(v) for k, v in row.items()} for pid, row in self.rows.items()}
        self.fields = tuple(k for k in PREFERENCE_FIELDS if dataset.values_for(k))
        self.groups = {}
        self.displays = {}
        for field in (*self.fields, 'age'):
            groups = {}
            displays = {}
            for pid, value in dataset.values_for(field):
                key = normalize(value)
                groups.setdefault(key, []).append(pid)
                displays.setdefault(key, value)
            self.groups[field] = {k: tuple(v) for k, v in groups.items()}
            self.displays[field] = displays
        # Comparisons use exactly the same consented dimensions for everyone.
        self.common_fields = tuple(f for f in self.fields if all(f in self.keys[p] for p in self.ids))
        self.pairs = tuple(combinations(self.ids, 2))
        self.overlaps = {
            pair: sum(self.keys[pair[0]][f] == self.keys[pair[1]][f] for f in self.common_fields)
            for pair in self.pairs
        } if len(self.common_fields) >= 2 else {}

    def complete(self, *fields):
        return tuple(pid for pid in self.ids if all(f in self.keys[pid] for f in fields))

    def equal(self, a, b, field):
        return field in self.keys[a] and field in self.keys[b] and self.keys[a][field] == self.keys[b][field]

    def different(self, a, b, field):
        return field in self.keys[a] and field in self.keys[b] and self.keys[a][field] != self.keys[b][field]

    def overlap(self, a, b):
        return self.overlaps.get((a, b), self.overlaps.get((b, a), 0))

    def name(self, pid):
        return self.dataset.display_name_for(pid)

    def pair_name(self, pair):
        return ' + '.join(self.name(p) for p in pair)
