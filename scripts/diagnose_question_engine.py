#!/usr/bin/env python3
"""Trace the Question Engine pipeline stage by stage for realistic rooms.

For every room: knowledge coverage per dimension, raw candidates per rule,
validation rejections (with reasons), quality scores, selection survival and
the final ordered quiz. ``--backend`` points at another checkout (for example
an exported pre-fix revision) so before/after numbers come from real engines.

    python scripts/diagnose_question_engine.py --output scripts/knowledge/diagnostic-after.json
"""
import argparse
import importlib.util
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from random import Random

ROOT = Path(__file__).resolve().parents[1]

LEGACY = {'unique_value', 'most_common_value', 'value_count', 'group_comparison', 'age_ranking',
          'second_largest_group', 'filtered_mode', 'category_coverage', 'balanced_split',
          'group_exception', 'least_common_value'}
SEMANTIC = {'group_count', 'group_scoped_count', 'group_mode', 'group_unique',
            'group_comparison_semantic', 'group_diversity', 'group_different_pair'}
GEOGRAPHIC = {'region_majority', 'region_unique', 'geographic_outlier', 'locality_distance_pair',
              'locality_extreme', 'locality_distinct'}
CROSS = {'group_filtered_mode', 'group_intersection_count', 'region_hobby_diversity'}
FIELDS = {'favorite_movie': ('movies', ('movie.genre',)),
          'favorite_food': ('foods', ('food.cuisine', 'food.format')),
          'hobby': ('hobbies', ('hobby.family', 'hobby.setting', 'hobby.physical')),
          'favorite_music': ('music', ('music.genre',)),
          'favorite_artist': ('artists', ('music.genre',)),
          'favorite_song': ('songs', ('music.genre',)),
          'city': ('localities', ('place.region', 'place.district'))}


def kind_of(candidate):
    """direct / semantic / geographic / cross_domain, from metadata or rule id."""
    meta = dict(candidate.metadata)
    if 'kind' in meta:
        return meta['kind']
    rule = candidate.source_rule_id
    if rule in SEMANTIC:
        return 'semantic'
    if rule in GEOGRAPHIC:
        return 'geographic'
    if rule in CROSS:
        return 'cross_domain'
    return 'direct'


def family_of(candidate):
    return dict(candidate.metadata).get('family', candidate.source_rule_id)


def rejection_reason(validator, candidate, dataset, normalize):
    """Mirror of QuestionValidator's checks, reporting the first failing one."""
    c = candidate
    if not 2 <= len(c.options) <= 4:
        return 'option_count'
    if len(c.text) > 600 or any(len(o.text) > 160 for o in c.options):
        return 'text_length'
    ids = [o.option_id for o in c.options]
    if len(ids) != len(set(ids)) or ids.count(c.correct_option_id) != 1:
        return 'option_ids'
    texts = [str(normalize(o.text)) for o in c.options]
    if any(not t for t in texts) or len(texts) != len(set(texts)):
        return 'duplicate_option_text'
    answer = str(normalize(next(o.text for o in c.options if o.option_id == c.correct_option_id)))
    if len(answer) >= 3 and not answer.isdecimal() and re.search(
            r'(?<!\w)' + re.escape(answer) + r'(?!\w)', str(normalize(c.text))):
        return 'answer_named_in_question'
    if not set(c.source_field_keys).issubset(dataset.field_keys):
        return 'unknown_field'
    if not set(c.involved_player_ids) | set(c.focus_player_ids) <= set(dataset.player_ids):
        return 'unknown_player'
    return 'other:' + type(validator).__name__


def coverage(dataset, knowledge):
    """Recognition per dimension: the engine's own group summaries when it has them."""
    try:
        from app.domain.questions.group_summary import summarize
    except ImportError:  # Pre-fix engine: exact identity resolution only.
        return identity_coverage(dataset, knowledge)
    return {key: {'shared': len(s.consented), 'players': dataset.player_count, 'recognized': len(s.recognized),
                  'unknown': len(s.unknown), 'coverage': round(s.coverage, 3)}
            for key, s in summarize(dataset, knowledge).dimensions.items()}


def identity_coverage(dataset, knowledge):
    report = {}
    for field, (kind, dims) in FIELDS.items():
        values = dataset.values_for(field)
        if not values:
            continue
        entities = {pid: r.entity for pid, v in values if (r := knowledge.resolve(kind, v)).entity}
        report[field] = {
            'consented': len(values), 'players': dataset.player_count, 'recognized': len(entities),
            'unknown': sorted({str(v) for pid, v in values if pid not in entities}),
            'dimensions': {d: sum(bool(knowledge.facts(e, d)) for e in entities.values()) for d in dims},
        }
        report[field]['all_players_complete'] = {
            d: n == dataset.player_count for d, n in report[field]['dimensions'].items()}
    return report


def trace_room(generator, room, language, seed, knowledge, question_count):
    from app.domain.questions.language import normalize
    dataset = room.dataset(language)
    started = time.perf_counter()
    final = generator.generate(dataset, question_count=question_count, time_limit_seconds=20, seed=seed)
    elapsed_ms = (time.perf_counter() - started) * 1000

    if hasattr(generator, 'trace'):
        trace = generator.trace(dataset, question_count=question_count, time_limit_seconds=20, seed=seed)
        raw, valid, scored, selected = trace.raw, trace.valid, trace.scored, trace.selected
        rejected = trace.rejected
    else:  # Pre-fix engine: replay QuestionGenerator.generate stage by stage.
        ds = dataset.with_language(language)
        rng = Random(seed)
        raw = [c for rule in generator._rules for c in rule.generate(ds, rng)]
        valid, rejected = [], []
        for c in raw:
            if generator._validator.is_valid(c, ds):
                valid.append(c)
            else:
                rejected.append((c, rejection_reason(generator._validator, c, ds, normalize)))
        scored = [(c, generator._scorer.score(c, ds)) for c in valid]
        selected = generator._selector.select(scored, question_count=question_count)

    # One rule can emit several kinds (a music-choice count is direct, a genre count semantic),
    # so every stage is tallied per candidate under (rule, kind, family).
    rules = defaultdict(lambda: {'raw': 0, 'valid': 0, 'selected': 0, 'scores': [], 'rejected': Counter()})
    key = lambda c: (c.source_rule_id, kind_of(c), family_of(c))
    for c in raw:
        rules[key(c)]['raw'] += 1
    for c, reason in rejected:
        rules[key(c)]['rejected'][reason] += 1
    for c, score in scored:
        rules[key(c)]['valid'] += 1
        rules[key(c)]['scores'].append(score)
    for c in selected:
        rules[key(c)]['selected'] += 1

    kinds = defaultdict(Counter)
    domains = defaultdict(Counter)
    for (rule_id, kind, family), r in rules.items():
        for stage in ('raw', 'valid', 'selected'):
            kinds[kind][stage] += r[stage]
    for c in selected:
        for domain in (dict(c.metadata).get('domains') or dict(c.metadata).get('domain') or 'unlabelled').split(','):
            domains[domain]['selected'] += 1
    semantic_pool = [(c, s) for c, s in scored if kind_of(c) != 'direct']
    selector = generator._selector if hasattr(generator, '_selector') else None
    semantic_capacity = len(selector.select(semantic_pool, question_count=question_count)) if (
        selector is not None and semantic_pool) else 0
    return {
        'room': room.name, 'language': language, 'players': dataset.player_count,
        'generation_ms': round(elapsed_ms, 1), 'final_count': len(final),
        'coverage': coverage(dataset, knowledge),
        'kinds': {k: dict(v) for k, v in sorted(kinds.items())},
        'domains_selected': {d: v['selected'] for d, v in sorted(domains.items())},
        'semantic_only_selectable': semantic_capacity,
        'rules': [{'rule_id': rule_id, 'kind': kind, 'family': family, 'raw': r['raw'], 'valid': r['valid'],
                   'rejected': dict(r['rejected']), 'selected': r['selected'],
                   'mean_score': round(sum(r['scores']) / len(r['scores']), 3) if r['scores'] else None}
                  for (rule_id, kind, family), r in sorted(rules.items())],
        'final': [{'index': i + 1, 'difficulty': q.difficulty.value, 'rule_id': q.source_rule_id,
                   'family': family_of(c), 'kind': kind_of(c),
                   'domain': dict(c.metadata).get('domains') or dict(c.metadata).get('domain', ''), 'text': q.text,
                   'correct': next(o.text for o in q.options if o.option_id == q.correct_option_id)}
                  for i, (q, c) in enumerate(zip(final, selected))],
    }


def load_rooms():
    spec = importlib.util.spec_from_file_location('diagnostic_rooms', ROOT / 'backend/tests/fixtures/rooms.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--backend', type=Path, default=ROOT / 'backend')
    parser.add_argument('--label', default='after')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--questions', type=int, default=20)
    args = parser.parse_args()
    sys.path.insert(0, str(args.backend.resolve()))
    from app.domain.questions import QuestionGenerator
    from app.infrastructure.knowledge import load_knowledge

    knowledge = load_knowledge()
    generator = QuestionGenerator(knowledge=knowledge)
    rooms = load_rooms()
    report = {'engine': args.label, 'knowledge_version': knowledge.version, 'question_count': args.questions,
              'rooms': []}
    for index, room in enumerate(rooms.DIAGNOSTIC_ROOMS):
        for language in dict.fromkeys((room.language, 'en' if room.language == 'he' else 'he')):
            result = trace_room(generator, room, language, 1000 + index, knowledge, args.questions)
            report['rooms'].append(result)
            kinds = result['kinds']
            summary = ', '.join(f"{k}: raw {v.get('raw', 0)} → valid {v.get('valid', 0)} → final {v.get('selected', 0)}"
                                for k, v in kinds.items())
            print(f"{room.name}/{language} ({result['players']} players, {result['generation_ms']} ms, "
                  f"{result['final_count']} questions) {summary}")
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
