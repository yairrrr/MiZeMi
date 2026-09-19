"""Media discoveries must survive the entire pipeline into public Question[]."""
from dataclasses import replace
from random import Random
from time import perf_counter

import pytest

from app.domain.questions import QuestionGenerator, QuestionValidator
from app.domain.questions.discovery_rules import GroupCountRule, MediaGenreOutlierRule
from app.domain.questions.group_summary import summarize
from app.infrastructure.knowledge import get_knowledge
from tests.fixtures.media import MEDIA_RICH, MEDIA_ROOMS
from tests.unit.test_category_first_questions import answered_by_earlier_questions

KB = get_knowledge()
ENGINE = QuestionGenerator(knowledge=KB)
FIELDS = ('favorite_movie', 'favorite_artist', 'favorite_song')


def trace(room=MEDIA_RICH, language='he', seed=11, count=20):
    return ENGINE.trace(room.dataset(language), question_count=count, time_limit_seconds=20, seed=seed)


def answer(question):
    return next(o.text for o in question.options if o.option_id == question.correct_option_id)


def selected_media(t, field, rule=None):
    return [(q, c) for q, c in zip(t.questions, t.selected)
            if c.knowledge_version and c.source_field_keys == (field,)
            and (rule is None or q.source_rule_id == rule)]


def choices(field, values, *, room=MEDIA_RICH):
    return replace(room, rows=tuple(
        {'values': {**row['values'], field: value}, 'hide': row['hide']}
        for row, value in zip(room.rows, values)))


@pytest.mark.parametrize('room', MEDIA_ROOMS, ids=lambda r: r.name)
@pytest.mark.parametrize('language', ['he', 'en'])
@pytest.mark.parametrize('seed', [1, 11, 37])
def test_all_three_supported_media_leaders_reach_final_questions(room, language, seed):
    t = trace(room, language, seed)
    assert len(t.questions) == 20
    expected = ('אימה', 'מזרחית', 'פופ') if language == 'he' else ('Horror', 'Mizrahi', 'Pop')
    for field, correct in zip(FIELDS, expected):
        q, c = next(iter(selected_media(t, field, 'group_mode')))
        assert answer(q) == correct
        assert q.explanation and q.knowledge_version == KB.version
        assert dict(c.metadata)['domain'] == field.removeprefix('favorite_')
        assert any(word in q.text for word in (
            ('סרט', 'אמנים', 'שירים') if language == 'he' else ('movie', 'artist', 'song')))
        # A supported choice is shown as evidence, not just a generic genre label.
        assert 'בין הבחירות:' in q.explanation if language == 'he' else 'Choices included:' in q.explanation


def test_final_media_comparison_survives_when_no_genre_has_a_unique_lead():
    room = choices('favorite_movie', ('המסור', 'המסור', 'היומן', 'היומן', 'היומן',
                                      'טרון: ארס', 'טרון: ארס', 'שרק', 'שרק', 'שכחו אותי בבית'))
    t = trace(room)
    assert not selected_media(t, 'favorite_movie', 'group_mode')  # Several genres tie at three.
    q, c = next(iter(selected_media(t, 'favorite_movie', 'group_comparison_semantic')))
    s = summarize(room.dataset(), KB).get('movie.genre')
    _, _, a, b = c.semantic_key
    assert abs(s.count(a) - s.count(b)) > 0
    winner = a if s.count(a) > s.count(b) else b
    assert dict(c.metadata)['answer_key'] == winner and 'סרט' in q.text


@pytest.mark.parametrize('field,values,player', [
    ('favorite_movie', ('המסור', 'המסור', 'המסור', 'לזמן את הרוע', 'לזמן את הרוע', 'טרון: ארס'), 'p06'),
    ('favorite_artist', ('שרית חדד', 'שרית חדד', 'שרית חדד', 'משה פרץ', 'משה פרץ', 'Metallica'), 'p06'),
    ('favorite_song', tuple(r['values']['favorite_song'] for r in MEDIA_RICH.rows), 'p03'),
])
def test_unique_genre_person_reaches_the_final_quiz(field, values, player):
    room = choices(field, values)
    # Isolate this identity insight: other domains can legitimately win the
    # limited person slots now that literal lookups no longer reserve any slots.
    # Rich-room coverage/mix is tested separately above and in resolution tests.
    room = replace(room, rows=tuple({**row, 'hide': tuple(f for f in row['values'] if f != field)}
                                   for row in room.rows))
    t = trace(room)
    q, c = next(iter(selected_media(t, field, 'group_genre_outlier')))
    assert c.focus_player_ids == (player,)
    assert answer(q) == room.dataset().display_name_for(player)
    assert 'שאף אחד אחר' in q.text
    assert q.explanation and len({o.text for o in q.options}) == len(q.options)


def test_generic_outlier_is_rejected_if_two_people_have_exclusive_genres():
    room = choices('favorite_movie', ('המסור', 'המסור', 'לזמן את הרוע', 'לזמן את הרוע', 'טרון: ארס', 'היומן'))
    found = MediaGenreOutlierRule(KB).generate(room.dataset(), Random(11))
    assert not [c for c in found if c.source_field_keys == ('favorite_movie',)]
    assert not selected_media(trace(room), 'favorite_movie', 'group_genre_outlier')


@pytest.mark.parametrize('rule', ['group_genre_outlier', 'group_diversity'])
def test_common_genres_of_an_ambiguous_title_cannot_prove_exclusivity_or_total_diversity(rule):
    # Every Titanic is classified as drama, but a specific version may also be
    # romance. Do not call The Notebook the only romance pick or claim a full
    # genre inventory by treating the common intersection as exhaustive.
    room = choices('favorite_movie', ('Titanic', 'היומן', 'המסור', 'המסור', 'לזמן את הרוע', 'לזמן את הרוע'))
    summary = summarize(room.dataset(), KB).get('movie.genre')
    assert summary.complete and 'p01' not in summary.entities
    assert 'movie.drama' in summary.classified['p01']  # Safe positive facts are preserved.
    assert not [c for c in trace(room).raw if c.source_rule_id == rule and c.source_field_keys == ('favorite_movie',)]


def test_genre_count_and_diversity_reach_final_quizzes_and_count_people_not_distinct_works():
    rich, small = trace(MEDIA_ROOMS[0]), trace(MEDIA_ROOMS[1])
    counts = [(q, c) for q, c in zip(rich.questions, rich.selected)
              if q.source_rule_id == 'group_count' and c.source_field_keys[0] in FIELDS]
    assert counts
    s = summarize(MEDIA_RICH.dataset(), KB)
    for q, c in counts:
        _, dim, genre = c.semantic_key
        assert int(answer(q)) == s.get(dim).count(genre)
        assert 'אנשים' in q.text or 'מכם' in q.text
    diversity = [(q, c) for q, c in zip(small.questions, small.selected)
                 if q.source_rule_id == 'group_diversity' and c.source_field_keys[0] in FIELDS]
    assert diversity
    for q, c in diversity:
        dim = c.semantic_key[1]
        assert int(answer(q)) == len(summarize(MEDIA_ROOMS[1].dataset(), KB).get(dim).represented())


@pytest.mark.parametrize('field,values', [
    ('favorite_movie', ('המסור',) * 3 + ('לזמן את הרוע',) * 3),
    ('favorite_artist', ('שרית חדד',) * 3 + ('Metallica',) * 2 + ('Taylor Swift',)),
    ('favorite_song', ('Shake It Off - Taylor Swift',) * 3 + ('Enter Sandman',) * 2 + ('Paradise - Coldplay',)),
])
def test_each_media_domain_can_supply_a_final_diversity_question_with_other_fields_withheld(field, values):
    room = choices(field, values)
    room = replace(room, rows=tuple({'values': r['values'], 'hide': tuple(k for k in r['values'] if k != field)}
                                   for r in room.rows))
    t = trace(room)
    assert 0 < len(t.questions) < 20  # Consent-limited room: no padding.
    q, c = next(iter(selected_media(t, field, 'group_diversity')))
    s = summarize(room.dataset(), KB).get(c.semantic_key[1])
    assert int(answer(q)) == len(s.represented())
    assert 'כל סגנון נספר פעם אחת' in q.explanation


def test_artist_and_song_subgroup_discoveries_reach_the_final_quiz():
    t = trace()
    questions = [(q, c) for q, c in zip(t.questions, t.selected)
                 if q.source_rule_id in ('group_filtered_mode', 'group_subgroup_comparison')
                 and {'favorite_artist', 'favorite_song'}.intersection(c.source_field_keys)]
    assert questions
    summary = summarize(MEDIA_RICH.dataset(), KB)
    for q, c in questions:
        condition, category, target = c.semantic_key[1:4]
        subgroup = set(summary.get(condition).members[category])
        target_summary = summary.get(target)
        counts = target_summary.counts_within(subgroup)
        winner = dict(c.metadata)['answer_key']
        competitors = c.semantic_key[4:] if q.source_rule_id == 'group_subgroup_comparison' else counts
        assert all(counts[winner] > counts[other] for other in competitors if other != winner)
        assert len(subgroup) >= 3 and q.explanation


@pytest.mark.parametrize('field', FIELDS)
def test_withheld_media_never_changes_any_final_question(field):
    rows = tuple({'values': {**r['values']}, 'hide': (field,) if i < 3 else ()}
                 for i, r in enumerate(MEDIA_RICH.rows))
    hidden = replace(MEDIA_RICH, rows=rows)
    changed = replace(hidden, rows=tuple({'values': {**r['values'], field: 'PRIVATE_UNRECOGNIZED_97'} if i < 3 else r['values'],
                                         'hide': r['hide']} for i, r in enumerate(rows)))
    assert trace(hidden).questions == trace(changed).questions


@pytest.mark.parametrize('field', FIELDS)
def test_missing_and_unknown_media_are_not_forced_into_final_questions(field):
    for omit in (True, False):
        rows = tuple({'values': {k: v for k, v in r['values'].items() if k != field} if omit
                      else {**r['values'], field: 'Unlisted classroom media 9f4d'}, 'hide': ()}
                     for r in MEDIA_RICH.rows)
        t = trace(replace(MEDIA_RICH, rows=rows))
        assert not any(c.knowledge_version and field in c.source_field_keys for c in t.selected)
        assert t.questions


@pytest.mark.parametrize('field', FIELDS)
def test_two_shared_media_answers_are_too_few_for_a_group_discovery(field):
    room = replace(MEDIA_RICH, rows=tuple({'values': r['values'], 'hide': (field,) if i >= 2 else ()}
                                         for i, r in enumerate(MEDIA_RICH.rows)))
    assert not any(c.knowledge_version and field in c.source_field_keys for c in trace(room).raw)


@pytest.mark.parametrize('field,values', [
    ('favorite_movie', ('המסור',) * 2 + ('לזמן את הרוע',) + ('טרון: ארס',) * 2),
    ('favorite_artist', ('שרית חדד', 'משה פרץ', 'זהבה בן', 'Metallica', 'Metallica')),
    ('favorite_song', ('Shake It Off - Taylor Swift',) * 3 + ('Enter Sandman',) * 2),
])
def test_one_unknown_that_could_tie_a_media_lead_rejects_the_majority(field, values):
    room = choices(field, (*values, 'Unlisted classroom media 9f4d'))
    s = next(s for s in summarize(room.dataset(), KB).dimensions.values() if s.dimension.field == field)
    assert s.eligible_for_media_leader() and len(s.unknown) == 1  # Coverage alone is not proof.
    assert not selected_media(trace(room), field, 'group_mode')
    assert not [c for c in trace(room).raw if c.source_rule_id == 'group_mode' and c.source_field_keys == (field,)]


def test_tied_or_ambiguous_media_leaders_are_never_invented():
    room = choices('favorite_artist', ('עומר אדם', 'אייל גולן', 'Metallica', 'Metallica'))
    room = choices('favorite_song', ('Shake It Off - Taylor Swift',) * 2 + ('Enter Sandman',) * 2, room=room)
    room = choices('favorite_movie', ('It',) * 4, room=room)
    t = trace(room)
    assert not [c for c in t.raw if c.source_rule_id == 'group_mode' and c.source_field_keys[0] in FIELDS]
    assert not any(c.knowledge_version and 'favorite_movie' in c.source_field_keys for c in t.selected)


def test_unknown_media_count_has_an_explicit_recognized_scope_and_no_exclusive_claim():
    room = choices('favorite_movie', ('המסור', 'המסור', 'לזמן את הרוע', 'טרון: ארס', 'Unlisted classroom media 9f4d'))
    ds = room.dataset()
    candidates = GroupCountRule(KB).generate(ds, Random(1))
    horror = next(c for c in candidates if c.semantic_key == ('SEMANTIC_COUNT', 'movie.genre', 'movie.horror'))
    assert answer(horror) == '3' and 'שזוהו' in horror.text
    assert '4 מתוך 5' in horror.explanation
    assert not selected_media(trace(room), 'favorite_movie', 'group_genre_outlier')


def test_family_candidate_budget_cannot_be_consumed_before_artists_and_songs(monkeypatch):
    import app.domain.questions.discovery_rules as rules
    monkeypatch.setattr(rules, 'MAX_CANDIDATES', 8)
    candidates = GroupCountRule(KB).generate(MEDIA_RICH.dataset(), Random(1))
    assert len(candidates) == 8
    assert set(FIELDS) <= {c.source_field_keys[0] for c in candidates}


@pytest.mark.parametrize('room', MEDIA_ROOMS, ids=lambda r: r.name)
def test_final_media_quizzes_are_deterministic_bilingual_and_do_not_repeat_settled_questions(room):
    he, en = trace(room), trace(room, 'en')
    assert he.questions == trace(room).questions
    assert [(c.semantic_key, c.correct_option_id) for c in he.selected] == [(c.semantic_key, c.correct_option_id) for c in en.selected]
    assert not answered_by_earlier_questions(he, room.dataset())
    validator = QuestionValidator()
    assert all(validator.is_valid(c, room.dataset()) for c in he.selected)
    for q in he.questions:
        assert not any(word in q.text for word in ('שדה', 'רשומה', 'מיפוי', 'קטגוריה סמנטית', 'באיזו שנה', 'באיזה עשור'))
        assert 'בסגנון אלקטרונית' not in q.text + q.explanation


def test_thirty_media_players_remain_fast_without_runtime_reference_io(monkeypatch):
    import builtins
    import socket
    from pathlib import Path
    room = replace(MEDIA_RICH, rows=MEDIA_RICH.rows * 3)
    ds = room.dataset()

    def forbidden(*args, **kwargs):
        raise AssertionError('Question generation must not read files or open a network connection')

    started = perf_counter()
    with monkeypatch.context() as patch:
        patch.setattr(builtins, 'open', forbidden)
        patch.setattr(Path, 'open', forbidden)
        patch.setattr(socket, 'create_connection', forbidden)
        patch.setattr(socket.socket, 'connect', forbidden)
        t = ENGINE.trace(ds, question_count=20, time_limit_seconds=20, seed=11)
    assert perf_counter() - started < 0.5
    assert len(t.questions) == 20
    assert all(selected_media(t, field) for field in FIELDS)
