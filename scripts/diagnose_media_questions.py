#!/usr/bin/env python3
"""Offline before/after media diagnostics using the same realistic synthetic rooms.

--backend can point to an exported earlier backend; fixtures always come from
this checkout. No profile is fetched, and no output is written unless requested.
"""
import argparse
from collections import Counter
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
from statistics import median
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('favorite_movie', 'favorite_artist', 'favorite_song')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', type=Path, default=ROOT / 'backend')
    parser.add_argument('--label', default='current')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--benchmark', action='store_true', help='Measure 20 fresh 30-player generations')
    args = parser.parse_args()
    sys.path.insert(0, str(args.backend.resolve()))
    from app.domain.questions import QuestionGenerator
    from app.infrastructure.knowledge import get_knowledge

    spec = importlib.util.spec_from_file_location('media_fixtures', ROOT / 'backend/tests/fixtures/media.py')
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    knowledge = get_knowledge()
    engine = QuestionGenerator(knowledge=knowledge)
    games = []
    outlier = replace(fixtures.MEDIA_RICH, name='media_movie_outlier', rows=tuple(
        {'values': {**r['values'], 'favorite_movie': movie}, 'hide': ()}
        for r, movie in zip(fixtures.MEDIA_RICH.rows, ('המסור',) * 3 + ('לזמן את הרוע',) * 2 + ('טרון: ארס',))))
    for room in (*fixtures.MEDIA_ROOMS, outlier):
        for language in ('he', 'en'):
            trace = engine.trace(room.dataset(language), question_count=20, time_limit_seconds=20, seed=11)
            stages = {stage: {
                field: dict(Counter(c.source_rule_id for c in getattr(trace, stage)
                                    if c.knowledge_version and c.source_field_keys == (field,)))
                for field in FIELDS} for stage in ('raw', 'valid', 'selected')}
            questions = [dict(index=q.index, rule=q.source_rule_id, fields=c.source_field_keys,
                              kind=dict(c.metadata).get('kind'), text=q.text,
                              options=[o.text for o in q.options],
                              answer=next(o.text for o in q.options if o.option_id == q.correct_option_id),
                              explanation=q.explanation)
                         for q, c in zip(trace.questions, trace.selected)]
            games.append(dict(room=room.name, language=language, seed=11, players=room.rows,
                              stages=stages, final_count=len(questions), questions=questions))
            print(f'{room.name}/{language}: {len(questions)} questions; selected media {stages["selected"]}')
    report = dict(label=args.label, knowledge=knowledge.version, synthetic=True, games=games)
    if args.benchmark:
        room = replace(fixtures.MEDIA_RICH, rows=fixtures.MEDIA_RICH.rows * 3)
        elapsed = []
        for seed in range(20):
            dataset = room.dataset()  # Fresh summary each time; reference knowledge already loaded.
            started = perf_counter()
            questions = engine.generate(dataset, question_count=20, time_limit_seconds=20, seed=seed)
            elapsed.append((perf_counter() - started) * 1000)
            assert len(questions) == 20
        report['performance'] = dict(players=30, questions=20, runs=20,
                                     median_ms=round(median(elapsed), 3), maximum_ms=round(max(elapsed), 3))
        print(report['performance'])
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
