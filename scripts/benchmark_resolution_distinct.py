#!/usr/bin/env python3
"""Offline performance control: 30 distinct choices in each of seven domains.

Unlike the realistic repeated-favorites fixtures, this prevents repeated input
values from making the per-room classification cache hide matching costs.
Every eligible canonical spelling receives one adjacent-character swap.
"""
import argparse
import json
from pathlib import Path
from statistics import median
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
from app.domain.game import Player, PlayerProfile, ProfileField
from app.domain.questions import ProfileDataset, QuestionGenerator
from app.infrastructure.knowledge import get_knowledge


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    kb = get_knowledge()
    fields = dict(favorite_movie='movies',favorite_song='songs',favorite_artist='artists',
                  favorite_music='music',favorite_food='foods',hobby='hobbies',city='localities')
    choices, checks = {}, []
    for field, kind in fields.items():
        entries = []
        for entity in kb.in_kind(kind):
            label = entity.english
            if not (8 <= len(label) <= 45 and label.isascii() and all(c.isalpha() or c==' ' for c in label)):
                continue
            exact = kb.resolve(kind, label)
            if not exact.entity or exact.entity.canonical_id != entity.canonical_id:
                continue
            index = next((i for i in range(2,len(label)-1)
                          if label[i].isalpha() and label[i+1].isalpha() and label[i]!=label[i+1]), None)
            if index is None:
                continue
            typo = label[:index]+label[index+1]+label[index]+label[index+2:]
            entries.append(typo)
            result = kb.resolve(kind, typo)
            checks.append(dict(kind=kind, canonical=label, typed=typo, expected_id=entity.canonical_id,
                               actual_id=result.entity.canonical_id if result.entity else None, match=result.match.value))
            if len(entries)==30:
                break
        assert len(entries)==30 and len(set(entries))==30
        choices[field] = entries
    assert not any(c['actual_id'] and c['actual_id']!=c['expected_id'] for c in checks)
    engine = QuestionGenerator(knowledge=kb)
    times, counts = [], []
    for seed in range(10):
        players = [Player(str(i), f'Person {i}', profile=PlayerProfile(str(i), tuple(
            ProfileField(key, values[i], True) for key, values in choices.items()))) for i in range(30)]
        start = perf_counter()
        questions = engine.generate(ProfileDataset(players), question_count=20, time_limit_seconds=20, seed=seed)
        times.append((perf_counter()-start)*1000)
        counts.append(len(questions))
    report = dict(typed_inputs=len(checks), correct=sum(c['actual_id']==c['expected_id'] for c in checks),
                  incorrect=0, unresolved=sum(c['actual_id'] is None for c in checks),
                  median_ms=round(median(times),3), max_ms=round(max(times),3), runs=10,
                  question_counts=counts, inputs=checks)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='inputs'},indent=2))


if __name__ == '__main__':
    main()
