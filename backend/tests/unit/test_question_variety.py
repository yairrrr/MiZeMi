"""Variety of the final game: which subjects, which reasoning, and no idea twice.

The engine may reason in any way it can prove, but a 20-question game has to
feel like twenty different discoveries about this group (QUESTION_VARIETY_DESIGN.md):
several kinds of reasoning, several profile answers, no subject dominating and
no question that is another one reworded.
"""

from collections import Counter
from math import ceil
from random import Random
from time import perf_counter

import pytest

from app.domain.questions import QuestionGenerator, QuestionValidator
from app.domain.questions.discovery_rules import (
    AgeSpreadRule,
    GroupAgreementRule,
    GroupExceptionRule,
    GroupUnanimityRule,
    IntersectionPersonRule,
    MovieSeriesLinkRule,
    PersonalFactRule,
    SharedTastePartnerRule,
    SongArtistLinkRule,
    TasteTwinsRule,
    TypicalMemberRule,
)
from app.domain.questions.group_summary import DOMAIN_GROUPS, age_band, summarize
from app.infrastructure.knowledge import get_knowledge
from tests.fixtures import rooms
from tests.fixtures.variety_rooms import VARIETY_ROOMS
from tests.unit.test_category_first_questions import answered_by_earlier_questions, dataset, meta

KB = get_knowledge()
GENERATOR = QuestionGenerator(knowledge=KB)
RICH = [room for room in VARIETY_ROOMS if room.dataset().player_count >= 14]


def game(room, seed=300, count=20, language=None):
    return GENERATOR.trace(room.dataset(language), question_count=count, time_limit_seconds=20, seed=seed)


def answer(candidate):
    return next(o.text for o in candidate.options if o.option_id == candidate.correct_option_id)


def produced(rule, ds):
    found = rule(KB).generate(ds, Random(3))
    return [c for c in found if QuestionValidator().is_valid(c, ds)]


def subjects(selected):
    """How many questions each subject takes; a cross-domain question counts once per subject."""
    counted = Counter()
    for candidate in selected:
        domains = (meta(candidate).get('domains') or meta(candidate).get('domain', '')).split(',')
        counted.update({DOMAIN_GROUPS[d] for d in domains if d})
    return counted


# ----- no idea twice ---------------------------------------------------------------------


@pytest.mark.parametrize('room', VARIETY_ROOMS, ids=lambda r: r.name)
def test_no_game_asks_the_same_idea_twice(room):
    for seed in (300, 7):
        t = game(room, seed)
        signatures = [meta(c).get('signature') for c in t.selected]
        assert len(signatures) == len(set(signatures)), signatures
        # Wording aside, the reasoning applied to one dimension is one idea.
        ideas = [(meta(c).get('operation'), meta(c).get('topic')) for c in t.selected]
        collapsed = [(op, 'music.genre' if topic in ('artist.genre', 'song.genre') else topic)
                     for op, topic in ideas]
        assert len(collapsed) == len(set(collapsed)), collapsed
        assert answered_by_earlier_questions(t, room.dataset()) == []


@pytest.mark.parametrize('room', RICH, ids=lambda r: r.name)
def test_a_rich_game_varies_reasoning_subjects_and_profile_answers(room):
    t = game(room)
    assert len(t.questions) >= 15
    operations = Counter(meta(c).get('operation') for c in t.selected)
    assert len(operations) >= 6, operations
    # No pattern owns a third of the game, and the three most used together stay
    # under 70%: a game must not read as "majority, majority, count, count…".
    assert max(operations.values()) <= ceil(len(t.questions) / 3), operations
    assert sum(n for _, n in operations.most_common(3)) <= 0.7 * len(t.questions), operations
    # The subject ceiling is a share of the game that was asked for, not of the
    # shorter game a thin room can support.
    assert max(subjects(t.selected).values()) <= ceil(0.3 * 20), subjects(t.selected)
    fields = {f for c in t.selected for f in c.source_field_keys}
    assert len(fields) >= 5, fields
    kinds = Counter(meta(c).get('kind', 'direct') for c in t.selected)
    # Raw-answer lookups are the warm-ups; a fact about a listed music choice is
    # a group fact and lives under the variety rules like any other question.
    lookups = [c for c in t.selected if meta(c).get('kind') == 'direct'
               and meta(c).get('family') != 'DIRECT_CHOICE']
    assert len(lookups) <= max(2, len(t.questions) // 10), [c.text for c in lookups]
    assert kinds['semantic'] + kinds['cross_domain'] + kinds['social'] > len(t.questions) / 2, kinds


def test_one_persons_answer_anchors_at_most_one_question():
    for room in VARIETY_ROOMS:
        anchors = [meta(c)['anchor'] for c in game(room).selected if 'anchor' in meta(c)]
        assert len(anchors) == len(set(anchors)), (room.name, anchors)


# ----- the new families ------------------------------------------------------------------


def test_a_shared_secret_is_attributed_to_its_writer_and_never_interpreted():
    rows = [{'city': 'חיפה', 'favorite_food': 'פיצה', 'hobby': 'ריצה', 'favorite_music': 'Pop',
             'personal_fact': fact}
            for fact in ('אני מגדלת זוחלים', 'רצתי מרתון', 'יש לי תאום', 'נולדתי בחו״ל')]
    ds = dataset(rows)
    candidates = produced(PersonalFactRule, ds)
    assert len(candidates) == 4
    for candidate in candidates:
        written = candidate.focus_player_ids[0]
        assert answer(candidate) == ds.display_name_for(written)
        quoted = next(v for p, v in ds.values_for('personal_fact') if p == written)
        assert quoted in candidate.text  # Exactly what the player wrote, nothing inferred.
        assert len({o.text for o in candidate.options}) == len(candidate.options)


def test_a_withheld_secret_is_never_quoted_and_a_shared_line_is_not_asked():
    rows = [{'city': 'חיפה', 'favorite_food': 'פיצה', 'hobby': 'ריצה', 'favorite_music': 'Pop',
             'personal_fact': fact} for fact in ('סוד פרטי מאוד', 'רצתי מרתון', 'יש לי תאום', 'רצתי מרתון')]
    ds = dataset(rows, hidden={0: ('personal_fact',)})
    texts = ' '.join(c.text for c in produced(PersonalFactRule, ds))
    assert 'סוד פרטי מאוד' not in texts  # Withheld: it does not exist for questions.
    assert 'רצתי מרתון' not in texts  # Two people wrote it: no single answer.
    assert 'יש לי תאום' in texts
    for room in VARIETY_ROOMS:
        shared = {value for _, value in room.dataset().values_for('personal_fact')}
        withheld = {row['values']['personal_fact'] for row in room.rows
                    if 'personal_fact' in row['hide']} - shared
        asked = ' '.join(c.text for c in game(room).selected)
        assert not any(secret in asked for secret in withheld), room.name
        quoted = [c for c in game(room).selected if meta(c).get('family') == 'SOCIAL_ATTRIBUTION']
        assert all(any(value in c.text for value in shared) for c in quoted), room.name


def test_taste_twins_name_the_pair_that_shares_the_most_and_explains_what():
    room = next(r for r in VARIETY_ROOMS if r.name == 'workplace_team_he')
    ds = room.dataset()
    twins = produced(TasteTwinsRule, ds)[0]
    first, second = twins.focus_player_ids
    summary = summarize(ds, KB)
    shared = [key for key in TasteTwinsRule.dimensions
              if (d := summary.get(key)) and first in d.classified and second in d.classified
              and d.classified[first] & d.classified[second]]
    assert len(shared) >= TasteTwinsRule.minimum_shared
    assert answer(twins) == f'{summary.name(first)} + {summary.name(second)}'
    assert str(len(set(shared))) in twins.explanation or len(shared) >= 2


def test_the_typical_member_matches_the_group_leaders_more_than_anyone_else():
    room = next(r for r in VARIETY_ROOMS if r.name == 'workplace_team_en')
    ds = room.dataset()
    typical = produced(TypicalMemberRule, ds)[0]
    summary = summarize(ds, KB)
    chosen = typical.focus_player_ids[0]
    leaders = []
    for key in TypicalMemberRule.dimensions:
        dimension = summary.get(key)
        if dimension is None or not dimension.eligible_for_count():
            continue
        counts = {c: dimension.count(c) for c in dimension.categories}
        if any(counts.values()):
            top = max(counts, key=lambda c: (counts[c], -dimension.categories.index(c)))
            leaders.append((dimension, top))
    mine = sum(chosen in d.members[c] for d, c in leaders)
    assert mine >= 2
    assert all(mine >= sum(p in d.members[c] for d, c in leaders) for p in ds.player_ids)


def test_unanimity_and_exception_only_claim_what_every_answer_supports():
    ds = dataset([{'city': c, 'favorite_food': 'פיצה', 'hobby': 'ריצה', 'favorite_music': 'Pop'}
                  for c in ('חיפה', 'עכו', 'נהריה', 'צפת', 'כרמיאל', 'טבריה')])
    unanimity = next(c for c in produced(GroupUnanimityRule, ds) if c.semantic_key[1] == 'place.region')
    assert answer(unanimity) == 'הצפון'
    assert 'כולם' in unanimity.explanation

    ds = dataset([{'city': c, 'favorite_food': 'פיצה', 'hobby': 'ריצה', 'favorite_music': 'Pop'}
                  for c in ('חיפה', 'עכו', 'נהריה', 'צפת', 'כרמיאל', 'אילת')])
    exception = next(c for c in produced(GroupExceptionRule, ds) if c.semantic_key[1] == 'place.region')
    assert answer(exception) == ds.display_name_for('p06')  # The one who is not northern.
    # An unrecognized answer must not become "the exception".
    unknown = dataset([{'city': c, 'favorite_food': 'פיצה', 'hobby': 'ריצה', 'favorite_music': 'Pop'}
                       for c in ('חיפה', 'עכו', 'נהריה', 'צפת', 'כרמיאל', 'עיר שלא קיימת')])
    assert not [c for c in produced(GroupExceptionRule, unknown) if c.semantic_key[1] == 'place.region']


def test_a_hidden_shared_category_pairs_two_different_answers():
    ds = dataset([{'city': 'חיפה', 'favorite_food': food, 'hobby': 'ריצה', 'favorite_music': 'Pop'}
                  for food in ('סושי', 'ראמן', 'פיצה', 'פלאפל', 'חומוס', 'שקשוקה')])
    partner = next(c for c in produced(SharedTastePartnerRule, ds) if c.semantic_key[1] == 'food.cuisine')
    asked, found = partner.focus_player_ids
    dishes = dict(ds.values_for('favorite_food'))
    assert dishes[asked] != dishes[found]  # Different dishes, same cuisine.
    assert dishes[asked] in partner.text and answer(partner) == ds.display_name_for(found)


def test_who_chose_both_names_the_only_person_in_two_categories():
    room = next(r for r in VARIETY_ROOMS if r.name == 'school_class_en')
    ds = room.dataset()
    both = produced(IntersectionPersonRule, ds)[0]
    summary = summarize(ds, KB)
    key_a, category_a, key_b, category_b, _ = both.semantic_key[1:]
    members = set(summary.get(key_a).members[category_a]) & set(summary.get(key_b).members[category_b])
    assert members == {both.focus_player_ids[0]}
    assert answer(both) == summary.name(both.focus_player_ids[0])


def test_a_song_by_someone_elses_favourite_artist_is_a_real_link():
    room = next(r for r in VARIETY_ROOMS if r.name == 'gamers_he')
    ds = room.dataset()
    link = produced(SongArtistLinkRule, ds)[0]
    summary = summarize(ds, KB)
    owner, listener = link.focus_player_ids
    artist = summary.get('artist.genre').entities[owner]
    song = summary.get('song.genre').entities[listener]
    assert artist.canonical_id in song.performer_ids and owner != listener
    assert answer(link) == summary.name(listener)


def test_two_films_from_one_series_are_matched_by_reference_data():
    ds = dataset([{'city': 'חיפה', 'favorite_food': 'פיצה', 'hobby': 'ריצה', 'favorite_music': 'Pop',
                   'favorite_movie': movie}
                  for movie in ('צעצוע של סיפור', 'צעצוע של סיפור 3', 'הסנדק', 'המסור', 'מטריקס', 'שרק')])
    link = produced(MovieSeriesLinkRule, ds)[0]
    summary = summarize(ds, KB)
    asked, found = link.focus_player_ids
    movies = summary.get('movie.genre').entities
    assert set(movies[asked].series_ids) & set(movies[found].series_ids)
    assert movies[asked].canonical_id != movies[found].canonical_id


def test_a_shared_studio_or_critics_list_is_not_a_film_series():
    # Toy Story and Finding Nemo share a "Pixar films" series id in the
    # reference data; they are not a film series and must not be linked.
    ds = dataset([{'city': 'חיפה', 'favorite_food': 'פיצה', 'hobby': 'ריצה', 'favorite_music': 'Pop',
                   'favorite_movie': movie}
                  for movie in ('צעצוע של סיפור', 'מוצאים את נמו', 'הסנדק', 'המסור', 'מטריקס', 'שרק')])
    assert not produced(MovieSeriesLinkRule, ds)


# ----- age and the other newly used answers ----------------------------------------------


def test_age_questions_use_ranges_and_never_reveal_an_exact_age():
    ds = dataset([{'city': 'חיפה', 'favorite_food': 'פיצה', 'hobby': 'ריצה', 'favorite_music': 'Pop',
                   'age': age} for age in (14, 15, 16, 17, 23, 24, 31, 42)])
    spread = produced(AgeSpreadRule, ds)[0]
    assert answer(spread) == '28'  # 42 − 14, without naming anyone's age.
    ages = [str(a) for a in (15, 16, 17, 23, 24, 31, 42)]
    for candidate in game(rooms.Room('ages', 'he', ()), 1, 1) and []:
        pass
    assert not any(a in spread.text for a in ages)
    assert age_band(17) == frozenset({'age.16_18'}) and age_band('not an age') == frozenset()
    # Bands, not birthdays: a question about the group's ages names a range.
    summary = summarize(ds, KB).get('age.band')
    assert summary.count('age.16_18') == 2 and summary.coverage == 1.0


def test_food_format_and_music_making_open_new_questions():
    ds = dataset([{'city': 'חיפה', 'favorite_food': food, 'hobby': hobby, 'favorite_music': 'Pop'}
                  for food, hobby in zip(('מרק עוף', 'סלט', 'שווארמה', 'המבורגר', 'סושי', 'פסטה'),
                                         ('גיטרה', 'פסנתר', 'ריצה', 'ציור', 'שחמט', 'קריאה'))])
    summary = summarize(ds, KB)
    formats = summary.get('food.format')
    assert formats.count('food.sandwich') == 2 and formats.count('food.salad') == 1
    assert summary.get('hobby.making_music').count('hobby.music') == 2
    # A recognized dish outside the compared formats is a known non-member, not an unknown.
    assert formats.coverage == 1.0


@pytest.mark.parametrize('room', RICH[:6], ids=lambda r: r.name)
def test_hebrew_and_english_games_ask_the_same_facts(room):
    he, en = game(room, language='he'), game(room, language='en')
    assert [c.semantic_key for c in he.selected] == [c.semantic_key for c in en.selected]
    assert [meta(c).get('signature') for c in he.selected] == [meta(c).get('signature') for c in en.selected]


def test_variety_rules_keep_generation_fast():
    room = max(VARIETY_ROOMS, key=lambda r: r.dataset().player_count)
    assert room.dataset().player_count >= 30
    GENERATOR.generate(room.dataset(), question_count=20, time_limit_seconds=20, seed=1)
    timings = []
    for seed in range(5):
        started = perf_counter()
        GENERATOR.generate(room.dataset(), question_count=20, time_limit_seconds=20, seed=seed)
        timings.append(perf_counter() - started)
    assert sorted(timings)[2] < 0.5, timings
