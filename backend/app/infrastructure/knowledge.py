"""Validate and load the committed offline bundle once; no network or DB IO."""

from functools import lru_cache
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re

from app.domain.questions.knowledge import Category, KINDS, KnownEntity, KnowledgeBase

BUNDLE_DIR = Path(__file__).resolve().parents[1] / 'data' / 'knowledge'
MAX_BUNDLE_BYTES = 4_000_000
MAX_ENTITIES = 10_000


class KnowledgeDataError(ValueError):
    """Safe startup error: corrupt reference data must not become game facts."""


def _require(condition: bool) -> None:
    if not condition:
        raise KnowledgeDataError('Invalid offline knowledge bundle; rebuild and validate the committed assets.')


def _text(value: object, *, maximum: int = 200, empty: bool = False) -> bool:
    return (isinstance(value, str) and (empty or bool(value.strip())) and len(value) <= maximum
            and all(c.isprintable() for c in value))


def _read(path: Path, remaining: int) -> tuple[object, bytes]:
    _require(path.is_file() and not path.is_symlink() and path.stat().st_size <= remaining)
    raw = path.read_bytes()
    _require(len(raw) <= remaining)
    try:
        def unique_keys(pairs):
            result = {}
            for key, value in pairs:
                _require(key not in result)
                result[key] = value
            return result
        value = json.loads(raw, object_pairs_hook=unique_keys,
                           parse_constant=lambda _: (_require(False)))
    except (ValueError, UnicodeError, RecursionError):
        raise KnowledgeDataError('Invalid offline knowledge JSON.') from None
    return value, raw


def load_knowledge(directory: Path = BUNDLE_DIR) -> KnowledgeBase:
    """Uncached entry point for build checks/corruption tests. Fixed filenames."""
    _require(directory.is_dir() and not directory.is_symlink())
    manifest, raw = _read(directory / 'manifest.json', MAX_BUNDLE_BYTES)
    _require(isinstance(manifest, dict) and type(manifest.get('schema')) is int and manifest.get('schema') == 1)
    _require(isinstance(manifest.get('files'), dict))
    expected = {'categories.json', *(f'{kind}.json' for kind in KINDS)}
    _require(set(manifest['files']) == expected)
    _require(_text(manifest.get('version'), maximum=64))
    _require(isinstance(manifest.get('sources'), list) and bool(manifest['sources']))
    _require(all(isinstance(s, dict) and s.get('license') in ('CC0-1.0', 'CC-BY-4.0')
                 and _text(s.get('url'), maximum=500) and _text(s.get('retrieved'), maximum=10)
                 for s in manifest['sources']))
    for source in manifest['sources']:
        try:
            date.fromisoformat(source['retrieved'])
        except ValueError:
            _require(False)
        _require(source['url'].startswith('https://'))
    remaining = MAX_BUNDLE_BYTES - len(raw)
    documents = {}
    for name in sorted(expected):
        document, content = _read(directory / name, remaining)
        remaining -= len(content)
        description = manifest['files'][name]
        _require(isinstance(description, dict) and description.get('sha256') == hashlib.sha256(content).hexdigest())
        _require(description.get('bytes') == len(content))
        _require(isinstance(document, list))
        documents[name] = document

    categories = []
    seen_categories = set()
    _require(1 <= len(documents['categories.json']) <= 300)
    for row in documents['categories.json']:
        _require(isinstance(row, list) and len(row) == 4)
        key, dimension, english, hebrew = row
        _require(all(_text(t, maximum=100) for t in row))
        _require(bool(re.fullmatch('[a-z][a-z0-9_.]+', key)))
        _require(dimension in ('movie.genre', 'music.genre', 'food.cuisine', 'food.format', 'hobby.family', 'place.district'))
        _require(key not in seen_categories)
        seen_categories.add(key)
        categories.append(Category(key, dimension, english, hebrew))
    _require(1 <= len(categories) <= 300)
    by_category = {c.category_id: c for c in categories}
    allowed_dimensions = {
        'movies': {'movie.genre'}, 'music': {'music.genre'}, 'artists': {'music.genre'},
        'foods': {'food.cuisine', 'food.format'}, 'hobbies': {'hobby.family'}, 'localities': {'place.district'},
    }
    entities = []
    for kind in KINDS:
        seen = set()
        for row in documents[f'{kind}.json']:
            _require(isinstance(row, list) and len(row) == 7)
            eid, english, hebrew, aliases, facts, coordinates, revision = row
            _require(_text(eid, maximum=64) and bool(re.fullmatch(r'(?:Q[1-9]\d*|G[1-9]\d*|local_[a-z0-9_]+)', eid)))
            _require(eid not in seen)
            seen.add(eid)
            _require(_text(english) and _text(hebrew, empty=True))
            _require(isinstance(aliases, list) and len(aliases) <= 30 and all(_text(a) for a in aliases))
            _require(len(set(aliases)) == len(aliases))
            _require(isinstance(facts, list) and len(facts) <= 30 and all(isinstance(f, str) and f in by_category for f in facts))
            _require(len(set(facts)) == len(facts))
            _require(all(by_category[f].dimension in allowed_dimensions[kind] for f in facts))
            _require(type(revision) is int and revision >= 0)
            if kind == 'localities':
                _require(isinstance(coordinates, list) and len(coordinates) == 2
                         and all(type(v) in (float, int) and math.isfinite(v) for v in coordinates))
                _require(28.5 <= coordinates[0] <= 34.5 and 33.5 <= coordinates[1] <= 36.5)
                _require(len(facts) <= 1)
            else:
                _require(coordinates is None and bool(facts))
            _require(len(entities) < MAX_ENTITIES)
            entities.append(KnownEntity(eid, kind, english, hebrew, tuple(aliases), frozenset(facts),
                                        tuple(coordinates) if coordinates is not None else None, revision))
        _require(bool(seen))
    _require(len(entities) <= MAX_ENTITIES)
    return KnowledgeBase(entities, categories, manifest['version'])


@lru_cache(maxsize=1)
def get_knowledge() -> KnowledgeBase:
    return load_knowledge()
