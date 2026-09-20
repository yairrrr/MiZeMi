#!/usr/bin/env python3
"""Diversity report for generated games: subjects, reasoning, fields, repeats.

Run from the repository root:

    .venv/bin/python scripts/analyze_question_variety.py

Generates one 20-question game per room in ``tests/fixtures/variety_rooms.py``
and classifies every final question by subject, semantic dimension, question
family, reasoning pattern, profile fields and answer type. Writes
``scripts/knowledge/variety-report.json`` and prints a per-game table.

``--backend`` points the same analysis at another checkout of the engine, so
before/after numbers come from the same rooms and the same classifier.
No network, no AI, no application database.
"""
import argparse
import json
import sys
from collections import Counter
from math import ceil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FIELD_OF_DIMENSION = {
    'movie.genre': 'favorite_movie', 'food.cuisine': 'favorite_food', 'food.format': 'favorite_food',
    'hobby.family': 'hobby', 'hobby.physical': 'hobby', 'hobby.setting': 'hobby',
    'hobby.making_music': 'hobby', 'music.genre': 'favorite_music', 'artist.genre': 'favorite_artist',
    'song.genre': 'favorite_song', 'place.region': 'city', 'age.band': 'age',
}
SUBJECTS = {'movie': 'film', 'music': 'music', 'artist': 'music', 'song': 'music', 'food': 'food',
            'hobby': 'hobby', 'place': 'place', 'age': 'age', 'social': 'personal'}
# Reasoning patterns of the families that predate the ``operation`` metadata.
LEGACY = {'DIRECT_UNIQUE': 'unique', 'DIRECT_COUNT': 'count', 'DIRECT_COMPARISON': 'comparison',
          'DIRECT_MAJORITY': 'majority', 'DIRECT_AGE': 'extreme', 'DIRECT_CHOICE': 'literal',
          'SEMANTIC_COUNT': 'count', 'SEMANTIC_MAJORITY': 'majority', 'SEMANTIC_COMPARISON': 'comparison',
          'SEMANTIC_UNIQUE': 'unique', 'SEMANTIC_DIVERSITY': 'diversity', 'SEMANTIC_MINORITY': 'minority',
          'SEMANTIC_DISTRIBUTION': 'distribution', 'GEO_REGION_MAJORITY': 'majority',
          'GEO_REGION_COMPARISON': 'comparison', 'GEO_REGION_COUNT': 'count', 'GEO_REGION_UNIQUE': 'unique',
          'GEO_REGION_DIVERSITY': 'diversity', 'GEO_EXTREME': 'extreme', 'GEO_CLOSEST_PAIR': 'closest_pair',
          'GEO_OUTLIER': 'outlier', 'CROSS_SUBGROUP_MAJORITY': 'majority',
          'CROSS_SUBGROUP_COMPARISON': 'comparison', 'CROSS_INTERSECTION_COUNT': 'count'}


def classify(question, candidate):
    meta = dict(candidate.metadata)
    family = meta.get('family') or candidate.source_rule_id
    key = tuple(candidate.semantic_key or ())
    dimensions = tuple(part for part in key[1:] if part in FIELD_OF_DIMENSION)
    fields = {FIELD_OF_DIMENSION[d] for d in dimensions} | {
        f for f in candidate.source_field_keys if f in set(FIELD_OF_DIMENSION.values()) | {'personal_fact'}}
    domains = tuple(d for d in (meta.get('domains') or meta.get('domain', '')).split(',') if d)
    answer = next(o.text for o in question.options if o.option_id == question.correct_option_id)
    return {
        'index': question.index + 1, 'difficulty': question.difficulty.value,
        'rule': question.source_rule_id, 'family': family, 'kind': meta.get('kind', 'direct'),
        'operation': meta.get('operation') or LEGACY.get(family, family.lower()),
        'topic': meta.get('topic', ''), 'signature': list(meta.get('signature') or (family, *key[1:])),
        'subjects': sorted({SUBJECTS.get(d, d) for d in domains}), 'dimensions': list(dimensions),
        'fields': sorted(fields), 'participants': len(candidate.involved_player_ids),
        'answer_type': ('person' if meta.get('person_answer') else
                        'number' if answer.strip().isdigit() else 'category'),
        'text': question.text, 'answer': answer, 'explanation': question.explanation,
    }


def summarize(rows, room, players, requested):
    subjects = Counter(s for row in rows for s in row['subjects'])
    operations = Counter(row['operation'] for row in rows)
    fields = Counter(f for row in rows for f in row['fields'])
    kinds = Counter(row['kind'] for row in rows)
    signatures = Counter(tuple(row['signature']) for row in rows)
    ideas = Counter((row['operation'], row['topic']) for row in rows)
    total = len(rows) or 1
    return {
        'room': room, 'players': players, 'questions': len(rows),
        'subjects': dict(subjects.most_common()), 'fields': dict(fields.most_common()),
        'families': dict(Counter(row['family'] for row in rows).most_common()),
        'operations': dict(operations.most_common()), 'kinds': dict(kinds),
        'distinct_subjects': len(subjects), 'distinct_fields': len(fields),
        'distinct_operations': len(operations),
        'largest_subject_share': round(max(subjects.values()) / total, 3) if subjects else 0.0,
        'largest_subject_questions': max(subjects.values()) if subjects else 0,
        'repeated_signatures': sum(n - 1 for n in signatures.values() if n > 1),
        'repeated_ideas': sum(n - 1 for n in ideas.values() if n > 1),
        'direct_share': round(kinds.get('direct', 0) / total, 3),
        'raw_lookups': sum(1 for row in rows if row['kind'] == 'direct' and row['family'] != 'DIRECT_CHOICE'),
        'cross_domain': kinds.get('cross_domain', 0), 'semantic': kinds.get('semantic', 0),
        'social': kinds.get('social', 0), 'geographic': kinds.get('geographic', 0),
        'meets_targets': {
            'six_reasoning_families': len(operations) >= 6,
            'five_profile_fields': len(fields) >= 5,
            'subject_under_30_percent': max(subjects.values(), default=0) <= ceil(0.3 * requested),
            'no_repeated_signature': not any(n > 1 for n in signatures.values()),
            'lookups_at_most_10_percent': sum(
                1 for row in rows if row['kind'] == 'direct' and row['family'] != 'DIRECT_CHOICE'
            ) <= max(2, requested // 10),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--backend', type=Path, default=ROOT / 'backend')
    parser.add_argument('--output', type=Path, default=ROOT / 'scripts/knowledge/variety-report.json')
    parser.add_argument('--questions', type=int, default=20)
    args = parser.parse_args()
    sys.path.insert(0, str(args.backend))
    from app.domain.questions import QuestionGenerator
    from app.infrastructure.knowledge import get_knowledge
    from tests.fixtures.variety_rooms import VARIETY_ROOMS

    engine = QuestionGenerator(knowledge=get_knowledge())
    games, every = [], []
    for index, room in enumerate(VARIETY_ROOMS):
        dataset = room.dataset()
        trace = engine.trace(dataset, question_count=args.questions, time_limit_seconds=20, seed=300 + index)
        rows = [classify(q, c) for q, c in zip(trace.questions, trace.selected)]
        every.extend(rows)
        games.append({**summarize(rows, room.name, dataset.player_count, args.questions),
                      'language': room.language, 'questions_detail': rows})

    totals = summarize(every, 'all rooms', 0, args.questions)
    args.output.write_text(json.dumps({'games': games, 'totals': totals}, ensure_ascii=False, indent=1) + '\n')
    print(f"{'room':20} {'q':>3} {'patterns':>9} {'subjects':>9} {'fields':>7} {'largest':>8} "
          f"{'dup sig':>8} {'dup idea':>9} {'lookups':>7}")
    for game in games:
        print(f"{game['room']:20} {game['questions']:3} {game['distinct_operations']:9} "
              f"{game['distinct_subjects']:9} {game['distinct_fields']:7} "
              f"{game['largest_subject_questions']:8} {game['repeated_signatures']:8} "
              f"{game['repeated_ideas']:9} {game['raw_lookups']:7}")
    print(f"\n{len(every)} questions in {len(games)} games")
    print('subjects  ', totals['subjects'])
    print('fields    ', totals['fields'])
    print('reasoning ', totals['operations'])
    failed = {name: [g['room'] for g in games if not g['meets_targets'][name]]
              for name in games[0]['meets_targets']}
    for name, rooms in failed.items():
        print(f"{name:28} {'all rooms meet it' if not rooms else 'missed by: ' + ', '.join(rooms)}")


if __name__ == '__main__':
    main()
