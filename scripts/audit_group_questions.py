#!/usr/bin/env python3
"""Reproducible offline sample games for human question-style review.

Generates one complete 20-question game per audit room (``backend/tests/fixtures/
rooms.py``) in the room's language, and records every profile answer, question,
option, correct answer, explanation and the internal family/kind/domain used for
selection. The script reproduces the games; it does not grade them — ratings live
in QUESTION_STYLE_AUDIT.md.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.domain.questions import QuestionGenerator  # noqa: E402
from app.infrastructure.knowledge import BUNDLE_DIR, load_knowledge  # noqa: E402
from tests.fixtures.rooms import AUDIT_ROOMS  # noqa: E402

SEED = 41


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--bundle', type=Path, default=BUNDLE_DIR)
    parser.add_argument('--output', type=Path, default=ROOT / 'scripts/knowledge/group-games.json')
    args = parser.parse_args()
    kb = load_knowledge(args.bundle)
    engine = QuestionGenerator(knowledge=kb)
    games = []
    for index, room in enumerate(AUDIT_ROOMS):
        trace = engine.trace(room.dataset(), question_count=20, time_limit_seconds=20, seed=SEED + index)
        questions = []
        for number, (question, candidate) in enumerate(zip(trace.questions, trace.selected), start=1):
            meta = dict(candidate.metadata)
            questions.append({
                'number': number, 'rule': question.source_rule_id, 'family': meta.get('family'),
                'kind': meta.get('kind'), 'domain': meta.get('domains') or meta.get('domain'),
                'difficulty': question.difficulty.value, 'text': question.text,
                'options': [o.text for o in question.options],
                'correct': next(o.text for o in question.options if o.option_id == question.correct_option_id),
                'explanation': question.explanation,
            })
        games.append({
            'group': room.name, 'language': room.language, 'seed': SEED + index, 'description': room.description,
            'profiles': [{**row['values'], 'withheld': list(row['hide'])} for row in room.rows],
            'kinds': dict(Counter(q['kind'] for q in questions)),
            'questions': questions,
        })
    payload = {'version': kb.version, 'synthetic': True, 'games': games}
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps([{'group': g['group'], 'language': g['language'], 'count': len(g['questions']),
                       'kinds': g['kinds']} for g in games], ensure_ascii=False))


if __name__ == '__main__':
    main()
