"""The browser fixture must exercise media semantics across seeds and reject regressions."""
from dataclasses import replace

import pytest

from app.domain.questions import ProfileDataset, QuestionGenerator
from app.infrastructure.knowledge import get_knowledge
from tests.classroom_knowledge import fixture_players, verify_trace


def generate(seed=11):
    players = fixture_players()
    trace = QuestionGenerator(knowledge=get_knowledge()).trace(
        ProfileDataset(players, 'he'), question_count=20, time_limit_seconds=20, seed=seed)
    return trace, players


@pytest.mark.parametrize('seed', [1, 11, 37, 99, 1024])
def test_browser_fixture_has_correct_final_media_and_group_questions_across_seeds(seed):
    trace, players = generate(seed)
    assert trace == generate(seed)[0]
    report = verify_trace(trace, players)
    assert report['semantic_rounds'] >= 9


@pytest.mark.parametrize('mutation', ['no_movie', 'no_artist', 'no_song', 'no_hobby',
                                    'wrong_answer', 'wrong_fact', 'empty_explanation', 'technical_explanation'])
def test_browser_oracle_rejects_lost_semantics_and_wrong_answers(mutation):
    trace, players = generate()
    questions, selected = list(trace.questions), list(trace.selected)
    if mutation.startswith('no_'):
        domain = mutation.removeprefix('no_')
        selected = [replace(c, metadata=tuple({**dict(c.metadata), 'kind': 'direct'}.items()))
                    if dict(c.metadata)['domain'] == domain else c for c in selected]
    else:
        index = next(i for i, c in enumerate(selected) if c.source_rule_id == 'group_mode'
                     and dict(c.metadata)['domain'] == 'artist')
        q, c = questions[index], selected[index]
        if mutation == 'wrong_answer':
            questions[index] = replace(q, correct_option_id=next(o.option_id for o in q.options if o.option_id != q.correct_option_id))
        elif mutation == 'wrong_fact':
            selected[index] = replace(c, metadata=tuple({**dict(c.metadata), 'answer_key': 'music.rock'}.items()))
        else:
            questions[index] = replace(q, explanation='' if mutation == 'empty_explanation' else 'SQL מאגר נתונים')
    with pytest.raises(AssertionError):
        verify_trace(replace(trace, questions=tuple(questions), selected=tuple(selected)), players)
