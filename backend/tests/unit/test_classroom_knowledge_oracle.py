"""The browser fixture must exercise media semantics across seeds and reject regressions."""
from dataclasses import replace

import pytest

from app.domain.questions import ProfileDataset, QuestionGenerator
from app.infrastructure.knowledge import get_knowledge
from tests.classroom_knowledge import MEDIA, fixture_players, verify_trace


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
                                    'wrong_answer', 'wrong_fact', 'empty_explanation', 'technical_explanation',
                                    'swapped_media_explanation', 'wrong_genre_explanation', 'unrelated_hebrew_explanation'])
def test_browser_oracle_rejects_lost_semantics_and_wrong_answers(mutation):
    trace, players = generate()
    questions, selected = list(trace.questions), list(trace.selected)
    if mutation.startswith('no_'):
        domain = mutation.removeprefix('no_')
        selected = [replace(c, metadata=tuple({**dict(c.metadata), 'kind': 'direct'}.items()))
                    if dict(c.metadata)['domain'] == domain else c for c in selected]
    else:
        # A media discovery whose explanation states the group's shared
        # category and cites a choice behind it. Media fields share one
        # subject budget, so a quiz holds no genre leader per field.
        index = next(i for i, c in enumerate(selected)
                     if dict(c.metadata)['family'] == 'SEMANTIC_COUNT'
                     and dict(c.metadata)['domain'] in MEDIA)
        q, c = questions[index], selected[index]
        if mutation == 'wrong_answer':
            questions[index] = replace(q, correct_option_id=next(o.option_id for o in q.options if o.option_id != q.correct_option_id))
        elif mutation == 'wrong_fact':
            selected[index] = replace(c, metadata=tuple({**dict(c.metadata), 'answer_key': 'music.rock'}.items()))
        else:
            if mutation == 'swapped_media_explanation':
                explanation = next(other.explanation for other, candidate in zip(questions, selected)
                                   if dict(candidate.metadata)['domain'] in MEDIA - {dict(c.metadata)['domain']}
                                   and other.explanation)
            elif mutation == 'wrong_genre_explanation':
                label = get_knowledge().categories[c.semantic_key[2]].label('he')
                explanation = q.explanation.replace(label, 'פופ')
                assert explanation != q.explanation, 'The mutation must really change the claimed genre'
            elif mutation == 'unrelated_hebrew_explanation':
                explanation = '4 אנשים העדיפו לבלות יותר זמן יחד.'
            else:
                explanation = '' if mutation == 'empty_explanation' else 'SQL מאגר נתונים'
            # Model a faulty rule, not merely a mismatch between its candidate
            # and serialized question: both carry the same wrong explanation.
            questions[index] = replace(q, explanation=explanation)
            selected[index] = replace(c, explanation=explanation)
    with pytest.raises(AssertionError):
        verify_trace(replace(trace, questions=tuple(questions), selected=tuple(selected)), players)


@pytest.mark.parametrize('omitted', [('favorite_movie',), ('favorite_artist',), ('favorite_song',),
                                   ('favorite_movie', 'favorite_artist', 'favorite_song')])
def test_oracle_fails_when_the_pipeline_stops_generating_media(omitted):
    players = fixture_players()
    generator = QuestionGenerator(knowledge=get_knowledge())
    original_rules = generator._rules

    class DropMediaCandidates:
        def generate(self, dataset, rng):
            for rule in original_rules:
                for candidate in rule.generate(dataset, rng):
                    if not set(omitted).intersection(candidate.source_field_keys):
                        yield candidate

    # Test-only fault injection: unchanged profiles, real validation/scoring/
    # final selection, but a media source stops supplying candidates entirely.
    generator._rules = (DropMediaCandidates(),)
    trace = generator.trace(ProfileDataset(players, 'he'), question_count=20,
                            time_limit_seconds=20, seed=11)
    with pytest.raises(AssertionError):
        verify_trace(trace, players)
