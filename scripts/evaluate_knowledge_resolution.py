#!/usr/bin/env python3
"""Fixed offline resolution/FINAL-quiz evaluation; synthetic profiles only.

Use --backend with an exported baseline backend to replay the same inputs.
No network, dataset refresh, or writes other than the explicit --output.
"""
import argparse
from collections import Counter
import gc
import hashlib
import json
from pathlib import Path
from statistics import median
import sys
from time import perf_counter
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'scripts/knowledge/resolution-evaluation.json'
FIELDS = dict(favorite_movie='movies', favorite_song='songs', favorite_artist='artists',
              favorite_music='music', favorite_food='foods', hobby='hobbies', city='localities')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', type=Path, default=ROOT / 'backend')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--label', default='current')
    parser.add_argument('--memory', action='store_true')
    args = parser.parse_args()
    sys.path.insert(0, str(args.backend.resolve()))
    from app.domain.game import Player, PlayerProfile, ProfileField
    from app.domain.questions import QuestionGenerator, ProfileDataset
    from app.domain.questions.knowledge import normalize_name
    from app.infrastructure.knowledge import load_knowledge

    raw = FIXTURE.read_bytes()
    data = json.loads(raw)
    start = perf_counter()
    kb = load_knowledge()
    load_ms = (perf_counter() - start) * 1000
    results = []
    for case in data['cases']:
        r = kb.resolve(case['kind'], case['text'])
        identity = r.entity.canonical_id if r.entity else None
        ambiguous = r.match.value == 'AMBIGUOUS' or normalize_name(case['text']) in kb.ambiguous_names[case['kind']]
        outcome = ('correct' if identity == case['expected_id'] else 'incorrect') if identity else ('ambiguous' if ambiguous else 'unknown')
        results.append({**case, 'actual_id': identity, 'match': r.match.value, 'outcome': outcome})

    def dataset(room, language='he'):
        players = []
        for i, row in enumerate(room['rows']):
            pid = f'p{i:02d}'
            fields = tuple(ProfileField(k, v, k not in row['hide']) for k, v in row['values'].items())
            players.append(Player(pid, row['name'], profile=PlayerProfile(pid, fields)))
        return ProfileDataset(players, language=language)

    engine = QuestionGenerator(knowledge=kb)
    games = []
    for room in data['rooms']:
        unresolved = sum(kb.resolve(FIELDS[k], v).entity is None for row in room['rows']
                         for k, v in row['values'].items() if k in FIELDS and k not in row['hide'])
        unclassified = sum(not kb.classify(FIELDS[k], v).category_ids for row in room['rows']
                           for k, v in row['values'].items() if k in FIELDS and k not in row['hide'])
        for language in ('he', 'en'):
            for seed in (1, 11, 37):
                t = engine.trace(dataset(room, language), question_count=20, time_limit_seconds=20, seed=seed)
                questions = []
                for q, c in zip(t.questions, t.selected):
                    meta = dict(c.metadata)
                    questions.append(dict(rule=q.source_rule_id, kind=meta.get('kind', meta.get('mix', 'direct')),
                                          family=meta.get('family'), semantic=bool(c.knowledge_version and meta.get('kind') != 'direct'),
                                          text=q.text, answer=next(o.text for o in q.options if o.option_id == q.correct_option_id)))
                lookups = sum(q['rule'] == 'unique_value' for q in questions)
                semantic = sum(q['semantic'] for q in questions)
                games.append(dict(room=room['name'], language=language, seed=seed, unknown_identities=unresolved,
                                  unclassified_values=unclassified,
                                  total=len(questions), semantic=semantic, direct_basic=len(questions)-semantic,
                                  raw_lookups=lookups, non_lookup=len(questions)-lookups, questions=questions))

    times = []
    room = next(r for r in data['rooms'] if r['name'] == 'imperfect_30')
    for seed in range(20):
        start = perf_counter()
        engine.generate(dataset(room), question_count=20, time_limit_seconds=20, seed=seed)
        times.append((perf_counter()-start)*1000)
    twenty_times = []
    twenty_room = next(r for r in data['rooms'] if r['name'] == 'imperfect_20')
    for seed in range(20):
        start = perf_counter()
        engine.generate(dataset(twenty_room), question_count=20, time_limit_seconds=20, seed=seed)
        twenty_times.append((perf_counter()-start)*1000)
    start = perf_counter()
    for _ in range(10):
        for case in data['cases']:
            kb.resolve(case['kind'], case['text'])
    lookup_us = (perf_counter()-start)*1e6/(10*len(data['cases']))
    memory = {}
    if args.memory:
        gc.collect(); tracemalloc.start()
        measured = load_knowledge()
        gc.collect(); retained, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
        memory = dict(retained_bytes=retained, peak_bytes=peak, entities=len(measured.entities))
    output = dict(label=args.label, fixture_sha256=hashlib.sha256(raw).hexdigest(),
                  counts=dict(Counter(r['outcome'] for r in results)),
                  outcomes_by_group={group: dict(Counter(r['outcome'] for r in results if r['group']==group))
                                     for group in sorted({r['group'] for r in results})},
                  load_ms=round(load_ms, 3), lookup_mean_us=round(lookup_us, 3),
                  generation_30_players_20_requested=dict(runs=20, median_ms=round(median(times),3), max_ms=round(max(times),3),
                                                         total_ms=round(sum(times),3)),
                  generation_20_players_20_requested=dict(runs=20, median_ms=round(median(twenty_times),3),
                                                         max_ms=round(max(twenty_times),3)),
                  memory=memory, cases=results, games=games)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k not in ('cases','games')}, indent=2))
    for name in (r['name'] for r in data['rooms']):
        group = [g for g in games if g['room']==name]
        print(name, {k:sorted({g[k] for g in group}) for k in ('total','semantic','direct_basic','raw_lookups','unknown_identities')})


if __name__ == '__main__':
    main()
