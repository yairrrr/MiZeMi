"""Category-first group discoveries, proven through the complete production pipeline.

ProfileDataset → knowledge classification → group summaries → discovery
families → validation → scoring → QuestionSelector → final questions. The
tests assert question families and facts, never exact wording, because
wording variants exist on purpose.
"""

import re
from collections import Counter, defaultdict
from random import Random
from time import perf_counter

import pytest

from app.domain.game import Player, PlayerProfile, ProfileField
from app.domain.questions import QuestionGenerator, QuestionValidator
from app.domain.questions.dataset import ProfileDataset
from app.domain.questions.discovery_rules import (
    ClosestPairRule,
    GeographicOutlierRule,
    GroupComparisonRule,
    GroupCountRule,
    GroupDistributionRule,
    GroupMajorityRule,
    GroupMinorityRule,
    GroupUniqueRule,
    RegionComparisonRule,
    RegionMajorityRule,
    discovery_rules,
)
from app.domain.questions.group_summary import summarize
from app.domain.questions.knowledge import Category, KnownEntity, KnowledgeBase
from app.domain.questions.language import normalize
from app.infrastructure.knowledge import get_knowledge
from tests.fixtures import rooms

KB = get_knowledge()
GENERATOR = QuestionGenerator(knowledge=KB)
FIELDS = ('city', 'favorite_food', 'hobby', 'favorite_music', 'favorite_movie', 'favorite_artist',
          'favorite_song', 'age', 'personal_fact')


def dataset(rows, language='he', hidden=None, kb_names=None):
    """``rows`` are dicts; ``hidden`` maps a row index to fields withheld from questions."""
    hidden = hidden or {}
    names = kb_names or (rooms.HE_NAMES if language == 'he' else rooms.EN_NAMES)
    players = []
    for index, row in enumerate(rows):
        pid = f'p{index + 1:02d}'
        fields = tuple(ProfileField(key, row[key], key not in hidden.get(index, ()))
                       for key in FIELDS if key in row)
        players.append(Player(pid, names[index], profile=PlayerProfile(pid, fields)))
    return ProfileDataset(players, language=language)


def meta(candidate):
    return dict(candidate.metadata)


def answer(candidate):
    return next(o.text for o in candidate.options if o.option_id == candidate.correct_option_id)


def trace(ds, count=20, seed=11):
    return GENERATOR.trace(ds, question_count=count, time_limit_seconds=20, seed=seed)


def produced(rule, ds, knowledge=KB):
    candidates = rule(knowledge).generate(ds, Random(3))
    return [c for c in candidates if QuestionValidator().is_valid(c, ds)]


def kinds(selected):
    return Counter(meta(c)['kind'] if 'kind' in meta(c) else 'direct' for c in selected)


def base_row(i, **values):
    cities = ('תל אביב', 'חיפה', 'ירושלים', 'באר שבע', 'נתניה', 'רמת גן', 'עכו', 'אילת', 'רחובות', 'חולון')
    foods = ('פיצה', 'סושי', 'חומוס', 'המבורגר', 'פסטה', 'פלאפל', 'ראמן', 'לזניה', 'טאקו', 'שווארמה')
    hobbies = ('ריצה', 'ציור', 'כדורגל', 'גיימינג', 'שחייה', 'צילום', 'קריאה', 'גיטרה', 'פילאטיס', 'בישול')
    music = ('Pop', 'Rock', 'Mizrahi', 'Pop', 'Electronic', 'Rock', 'Pop', 'Mizrahi', 'Jazz', 'Pop')
    row = {'city': cities[i % 10], 'favorite_food': foods[i % 10], 'hobby': hobbies[i % 10],
           'favorite_music': music[i % 10]}
    row.update(values)
    return row


# ----- Scenario 1: movie genres ---------------------------------------------------------

HORROR = ('המסור', 'לזמן את הרוע')
SCIFI = ('מטריקס', 'בחזרה לעתיד', 'טרון: ארס')
OTHER_MOVIES = ('פורסט גאמפ', 'היומן', 'צעצוע של סיפור', 'שכחו אותי בבית', 'הסנדק', 'לה לה לנד',
                'בדרך לחתונה עוצרים בווגאס')


@pytest.mark.parametrize('language', ['he', 'en'])
def test_scenario_1_horror_and_science_fiction_picks_become_a_group_question(language):
    movies = HORROR + SCIFI + OTHER_MOVIES
    ds = dataset([base_row(i, favorite_movie=m) for i, m in enumerate(movies)], language)
    genre = summarize(ds, KB).get('movie.genre')
    assert genre.count('movie.horror') == 2 and genre.count('movie.scifi') == 3 and not genre.unknown

    comparison = next(c for c in produced(GroupComparisonRule, ds)
                      if c.semantic_key == ('SEMANTIC_COMPARISON', 'movie.genre', 'movie.horror', 'movie.scifi'))
    horror, scifi = ('אימה', 'מדע בדיוני') if language == 'he' else ('Horror', 'Science fiction')
    assert answer(comparison) == scifi
    assert [o.text for o in comparison.options] == [horror, scifi]
    assert '3' in comparison.explanation and '2' in comparison.explanation
    assert not any(title in comparison.text for title in movies)  # Nobody typed the genre.

    selected = trace(ds).selected
    movie_discoveries = [c for c in selected if meta(c).get('kind') == 'semantic' and meta(c).get('domain') == 'movie']
    assert movie_discoveries, [c.text for c in selected]


# ----- Scenario 2: geography ---------------------------------------------------------------


def test_scenario_2_a_northern_majority_is_discovered_from_town_names():
    ds = rooms.GEO_HEAVY.dataset()
    selected = trace(ds).selected
    region = next(c for c in selected if c.source_rule_id == 'region_majority')
    assert answer(region) == 'הצפון'
    assert 'רוב' in region.text
    assert '9 אנשים גרים בצפון' in region.explanation and 'יותר ממחצית הקבוצה' in region.explanation
    assert not any(row['values']['city'] == 'צפון' for row in rooms.GEO_HEAVY.rows)


# ----- Scenario 3: hobbies -----------------------------------------------------------------


@pytest.mark.parametrize('language,sport', [('he', 'ספורט'), ('en', 'sport')])
def test_scenario_3_different_sports_are_counted_as_sport(language, sport):
    hobbies = ('ריצה', 'כדורגל', 'פילאטיס', 'גלישה', 'ציור', 'שחמט')
    ds = dataset([base_row(i, hobby=h) for i, h in enumerate(hobbies)], language)
    count = next(c for c in produced(GroupCountRule, ds)
                 if c.semantic_key == ('SEMANTIC_COUNT', 'hobby.family', 'hobby.sport'))
    assert answer(count) == '4'
    assert sport in count.text.lower()
    assert all(sport not in h for h in hobbies)
    assert any(meta(c).get('kind') == 'semantic' and meta(c).get('domain') == 'hobby'
               for c in trace(ds, count=12).selected)


# ----- Scenario 4: food --------------------------------------------------------------------


def test_scenario_4_italian_dishes_aggregate_into_a_cuisine_question():
    foods = ('פיצה', 'פסטה', 'לזניה', 'סושי', 'חומוס', 'המבורגר')
    ds = dataset([base_row(i, favorite_food=f) for i, f in enumerate(foods)])
    counts = {c.semantic_key: answer(c) for c in produced(GroupCountRule, ds)}
    assert counts[('SEMANTIC_COUNT', 'food.cuisine', 'food.italian')] == '3'
    majority = next(c for c in produced(GroupMajorityRule, ds) if c.semantic_key == ('SEMANTIC_MAJORITY', 'food.cuisine'))
    assert answer(majority) == 'איטלקי'
    assert any(meta(c).get('kind') == 'semantic' and meta(c).get('domain') == 'food' for c in trace(ds, count=12).selected)


def test_hummus_is_middle_eastern_not_asian_and_japanese_dishes_are_asian():
    ds = dataset([base_row(i, favorite_food=f) for i, f in enumerate(('חומוס', 'שווארמה', 'סושי', 'ראמן'))])
    cuisine = summarize(ds, KB).get('food.cuisine')
    assert cuisine.members['food.middle_eastern'] == ('p01', 'p02')
    assert cuisine.members['food.asian'] == ('p03', 'p04')


# ----- Scenario 5 and 6: the rich room, through the real selector -------------------------------


def diagnostic_table(ds, seed=11):
    t = trace(ds, seed=seed)
    return t, [(i + 1, q.difficulty.value, q.source_rule_id, meta(c).get('family'), meta(c).get('domain'),
                meta(c).get('kind'), q.text) for i, (q, c) in enumerate(zip(t.questions, t.selected))]


@pytest.mark.parametrize('room,domains', [(rooms.HE_RICH, 3), (rooms.EN_RICH, 3), (rooms.MOVIE_HEAVY, 3),
                                          (rooms.FOOD_HEAVY, 2)], ids=lambda r: getattr(r, 'name', r))
def test_scenario_5_rich_rooms_are_mostly_group_discoveries(room, domains):
    # The food room has no movies and music is a listed choice, so food and hobbies
    # are its only taste domains; the other rooms also carry movie discoveries.
    t, table = diagnostic_table(room.dataset())
    print('\n'.join(' | '.join(map(str, row)) for row in table))  # Visible with pytest -s.
    mix = kinds(t.selected)
    assert len(t.questions) == 20
    assert mix['semantic'] >= 7, table
    assert mix['direct'] <= 7, table
    assert mix['geographic'] + mix['cross_domain'] >= 4, table
    semantic_domains = {meta(c)['domain'] for c in t.selected if meta(c).get('kind') == 'semantic'}
    assert len(semantic_domains) >= domains, table


def test_scenario_6_semantic_candidates_reach_the_final_questions():
    ds = rooms.HE_RICH.dataset()
    t = trace(ds)
    raw = kinds(t.raw)
    final = kinds(t.selected)
    # Direct rules still produce the most raw candidates, and every one of them is valid…
    assert raw['direct'] > raw['semantic']
    assert not t.rejected
    # …yet the final quiz is led by discoveries, and each one is a real question object.
    assert final['semantic'] >= final['direct']
    finals = {q.question_id: q for q in t.questions}
    assert len(finals) == 20
    assert all(q.knowledge_version for q, c in zip(t.questions, t.selected) if meta(c).get('kind') != 'direct')


def test_scenario_7_a_flood_of_literal_questions_cannot_starve_discoveries():
    # Thirty players with mostly distinct raw answers: hundreds of valid "who is the only one…" lookups.
    towns = ('תל אביב', 'רמת גן', 'חולון', 'בת ים', 'הרצליה', 'פתח תקווה', 'ראשון לציון', 'רחובות', 'נתניה', 'כפר סבא',
             'רעננה', 'הוד השרון', 'גבעתיים', 'מודיעין', 'חיפה', 'עכו', 'נהריה', 'טבריה', 'צפת', 'כרמיאל',
             'עפולה', 'באר שבע', 'אשדוד', 'אשקלון', 'אילת', 'דימונה', 'שדרות', 'קריית גת', 'ירושלים', 'בית שמש')
    foods = ('פיצה', 'פסטה', 'לזניה', 'ספגטי', 'ריזוטו', 'ניוקי', 'סושי', 'ראמן', 'פאד תאי', 'חומוס',
             'פלאפל', 'שווארמה', 'שקשוקה', 'המבורגר', 'טאקו', 'פאייה', 'קוסקוס', 'מג׳דרה', 'נאצ׳וס', 'חביתה')
    hobbies = ('ריצה', 'כדורגל', 'כדורסל', 'טניס', 'שחייה', 'גלישה', 'פילאטיס', 'ציור', 'צילום', 'סריגה',
               'גיטרה', 'פסנתר', 'גיימינג', 'קריאה', 'שחמט', 'מדיטציה', 'טיולים', 'בישול', 'אפייה', 'תכנות')
    movies = HORROR + SCIFI + OTHER_MOVIES + ('הניצוץ', 'תברח', 'פארק היורה', 'שרק', 'מוצאים את נמו', 'למעלה')
    music = ('Pop', 'Rock', 'Mizrahi', 'Electronic', 'Hip-Hop / Rap', 'Jazz')
    rows = [{'city': towns[i], 'favorite_food': foods[i % 20], 'hobby': hobbies[(i * 7) % 20],
             'favorite_music': music[i % 6], 'favorite_movie': movies[i % len(movies)], 'age': 20 + i,
             'personal_fact': f'יש לי {i + 2} חתולים'}
            for i in range(30)]
    t = trace(dataset(rows, kb_names=[f'שחקן {i}' for i in range(30)]))
    raw, final = kinds(t.raw), kinds(t.selected)
    assert raw['direct'] >= 2.5 * raw['semantic']
    assert final['semantic'] >= 7
    assert final['direct'] <= 7
    assert max(Counter(meta(c).get('family') for c in t.selected).values()) <= 4


# ----- Scenario 8: recognition coverage ------------------------------------------------------

UNLISTED = ('סרט של אבא שלי', 'הסרט מהקיץ', 'משהו עם זומבים', 'לא זוכרת את השם', 'הסרט הישראלי ההוא',
            'סדרה ולא סרט', 'אנימה כלשהי', 'שובר קופות', 'הראשון שראיתי', 'קומדיה צרפתית', 'סרט טורקי',
            'הסרט עם הכלב', 'דוקו על טבע', 'סרט אימה מקוריאה', 'קלאסיקה ישנה', 'מה שהיה בנטפליקס')
HORROR_ONLY = ('Evil Dead Burn', 'The Monkey (film)', 'Until Dawn (film)', 'Insidious: Out of the Further',
               'Return to Silent Hill', 'The Conjuring: Last Rites', 'Wolf Man (2025 film)', 'Saw',
               'Together (2025 film)', 'Send Help')
OTHER_CLEAN = ('Challengers (film)', 'Greyhound (film)', 'Fjord (film)', 'David (2025 film)',
               'The Mandalorian and Grogu', 'Tron: Ares', 'The Invite', 'Train Dreams (film)')
GENRE_CLAIMS = (GroupMajorityRule, GroupComparisonRule, GroupCountRule, GroupUniqueRule, GroupMinorityRule,
                GroupDistributionRule)


def test_scenario_8_four_recognized_movies_out_of_twenty_support_no_group_claim():
    movies = ('Saw', 'The Conjuring', 'Evil Dead Burn', 'The Monkey (film)') + UNLISTED
    ds = dataset([base_row(i, favorite_movie=m) for i, m in enumerate(movies)], 'en')
    genre = summarize(ds, KB).get('movie.genre')
    assert (len(genre.recognized), len(genre.consented)) == (4, 20)
    claims = [c for rule in GENRE_CLAIMS for c in produced(rule, ds) if 'favorite_movie' in c.source_field_keys]
    assert claims == []
    assert not any('favorite_movie' in c.source_field_keys and meta(c).get('kind') != 'direct'
                   for c in trace(ds).selected)


def test_scenario_8_eighteen_recognized_movies_with_a_clear_horror_majority_may_claim_it():
    movies = HORROR_ONLY + OTHER_CLEAN + UNLISTED[:2]
    ds = dataset([base_row(i, favorite_movie=m) for i, m in enumerate(movies)], 'en')
    genre = summarize(ds, KB).get('movie.genre')
    assert (len(genre.recognized), len(genre.consented), genre.count('movie.horror')) == (18, 20, 10)
    majority = next(c for c in produced(GroupMajorityRule, ds) if c.semantic_key == ('SEMANTIC_MAJORITY', 'movie.genre'))
    assert answer(majority) == 'Horror'
    assert '18 of the 20' in majority.explanation


def test_unknown_answers_cannot_flip_a_comparison():
    # Three horror against two science fiction is decided only if no unknown answer could tie it.
    decided = HORROR_ONLY[:3] + ('Tron: Ares', 'Spaceman (2024 film)', 'Challengers (film)')
    undecided = decided + UNLISTED[:1]
    key = ('SEMANTIC_COMPARISON', 'movie.genre', 'movie.horror', 'movie.scifi')
    assert key in {c.semantic_key for c in produced(GroupComparisonRule, dataset([base_row(i, favorite_movie=m) for i, m in enumerate(decided)], 'en'))}
    assert key not in {c.semantic_key for c in produced(GroupComparisonRule, dataset([base_row(i, favorite_movie=m) for i, m in enumerate(undecided)], 'en'))}


# ----- Scenario 9: ties ----------------------------------------------------------------------


def keys(rule, ds, knowledge=KB):
    return {c.semantic_key for c in produced(rule, ds, knowledge)}


def test_scenario_9_tied_categories_are_never_compared_or_crowned():
    movies = HORROR_ONLY[:3] + ('Tron: Ares', 'Spaceman (2024 film)', 'Megalopolis (film)')
    ds = dataset([base_row(i, favorite_movie=m, favorite_music=('Pop', 'Rock')[i % 2],
                           favorite_food=('פיצה', 'סושי')[i % 2], hobby=('ריצה', 'ציור')[i % 2],
                           city=('חיפה', 'תל אביב')[i % 2]) for i, m in enumerate(movies)])
    assert ('SEMANTIC_COMPARISON', 'movie.genre', 'movie.horror', 'movie.scifi') not in keys(GroupComparisonRule, ds)
    assert ('SEMANTIC_MAJORITY', 'movie.genre') not in keys(GroupMajorityRule, ds)
    for dimension, a, b in (('music.genre', 'music.pop', 'music.rock'), ('food.cuisine', 'food.italian', 'food.asian'),
                            ('hobby.family', 'hobby.sport', 'hobby.creative')):
        assert ('SEMANTIC_COMPARISON', dimension, a, b) not in keys(GroupComparisonRule, ds)
        assert ('SEMANTIC_MAJORITY', dimension) not in keys(GroupMajorityRule, ds)
    assert not keys(RegionMajorityRule, ds)
    assert not {k for k in keys(RegionComparisonRule, ds) if {'region.north', 'region.central'} <= set(k)}


def test_a_race_one_side_wins_more_than_three_to_one_is_not_asked():
    sports = ('ריצה', 'כדורגל', 'שחייה', 'פילאטיס')
    pair = ('SEMANTIC_COMPARISON', 'hobby.family', 'hobby.sport', 'hobby.creative')
    lopsided = dataset([base_row(i, hobby=sports[i % 4] if i < 9 else 'ציור') for i in range(11)])  # 9 vs 2
    close = dataset([base_row(i, hobby=sports[i % 4] if i < 6 else 'ציור') for i in range(8)])  # 6 vs 2
    assert pair not in keys(GroupComparisonRule, lopsided)
    assert pair in keys(GroupComparisonRule, close)


def test_scenario_9_a_runner_up_is_named_only_when_it_is_really_second():
    ds = rooms.HE_RICH.dataset()
    region = summarize(ds, KB).get('place.region')
    assert sorted((region.count(c) for c in region.represented()), reverse=True) == [9, 4, 4, 2]
    center = next(c for c in produced(RegionMajorityRule, ds))
    assert '9 אנשים גרים במרכז' in center.explanation and 'במקום השני' not in center.explanation  # North and south tie.
    assert ('rank', 'place.region', 'region.north') not in meta(center)['reveals']
    hobby = next(c for c in produced(GroupMajorityRule, ds) if c.semantic_key == ('SEMANTIC_MAJORITY', 'hobby.family'))
    assert 'במקום השני: אמנות ויצירה (3)' in hobby.explanation  # 11, 3, 2, …


def test_scenario_9_minority_and_distribution_reject_boundary_ties():
    rows = [base_row(i, hobby=h) for i, h in enumerate(
        ('ריצה', 'כדורגל', 'כדורסל', 'ציור', 'צילום', 'גיימינג', 'שחמט', 'ריצה'))]
    family = summarize(dataset(rows), KB).get('hobby.family')
    counts = {c: family.count(c) for c in family.represented()}
    assert sorted(counts.values()) == [1, 1, 2, 4]  # digital and table games tie for least.
    assert not {k for k in keys(GroupMinorityRule, dataset(rows)) if k[1] == 'hobby.family'}


def geometry_kb():
    categories = [Category('region.north', 'place.region', 'The north', 'הצפון'),
                  Category('region.central', 'place.region', 'The center', 'המרכז')]
    towns = [('A', (32.0, 34.8)), ('B', (32.1, 34.8)), ('C', (32.5, 34.8)), ('D', (32.6, 34.8))]
    entities = [KnownEntity(f'local_{name.lower()}', 'localities', name, name, (),
                            frozenset({'region.north' if lat > 32.3 else 'region.central'}), coords)
                for name, coords in towns for lat in [coords[0]]]
    return KnowledgeBase(entities, categories, 'geometry-test')


def test_scenario_9_equal_nearest_pairs_and_furthest_people_are_not_asked():
    kb = geometry_kb()
    symmetric = dataset([{'city': c} for c in ('A', 'B', 'C', 'D')], 'en')
    assert not produced(ClosestPairRule, symmetric, kb)  # A–B equals C–D.
    assert not produced(GeographicOutlierRule, symmetric, kb)  # Mirror image: A and D tie, B and C tie.
    uneven = dataset([{'city': c} for c in ('A', 'B', 'C', 'C')], 'en')
    assert not produced(ClosestPairRule, uneven, kb)  # Two people in the same town are not "closest towns".


# ----- Scenario 10: consent ------------------------------------------------------------------

CONSENT_ROWS = [
    {'city': 'חיפה', 'favorite_food': 'פיצה', 'hobby': 'ריצה', 'favorite_music': 'Pop', 'favorite_movie': 'המסור',
     'favorite_artist': 'עומר אדם', 'favorite_song': 'Blank Space'},
    *[base_row(i, favorite_movie=m, favorite_artist=a, favorite_song=s) for i, (m, a, s) in enumerate((
        ('לזמן את הרוע', 'Taylor Swift', 'Yellow - Coldplay'), ('מטריקס', 'Coldplay', 'Enter Sandman'),
        ('שרק', 'Metallica', 'Blank Space'), ('בחזרה לעתיד', 'עדן בן זקן', 'Yellow - Coldplay'),
        ('צעצוע של סיפור', 'Eminem', 'Enter Sandman'), ('הסנדק', 'Taylor Swift', 'Blank Space'),
        ('פורסט גאמפ', 'Coldplay', 'Yellow - Coldplay'), ('היומן', 'עומר אדם', 'Enter Sandman')), start=1)],
]


@pytest.mark.parametrize('field', ['favorite_movie', 'favorite_food', 'hobby', 'city', 'favorite_music',
                                   'favorite_artist', 'favorite_song'])
def test_scenario_10_a_withheld_answer_has_no_influence_at_all(field):
    hidden = dataset(CONSENT_ROWS, hidden={0: (field,)})
    secret = dataset([{**CONSENT_ROWS[0], field: 'Other' if field == 'favorite_music' else 'לזמן את הרוע'},
                      *CONSENT_ROWS[1:]], hidden={0: (field,)})
    omitted = dataset([{k: v for k, v in CONSENT_ROWS[0].items() if k != field}, *CONSENT_ROWS[1:]])
    outputs = [trace(ds, seed=5) for ds in (hidden, secret, omitted)]
    assert outputs[0].questions == outputs[1].questions == outputs[2].questions
    assert outputs[0].raw == outputs[1].raw == outputs[2].raw
    for summary in summarize(hidden, KB).dimensions.values():
        if summary.dimension.field == field:
            assert 'p01' not in summary.consented
            assert all('p01' not in members for members in summary.members.values())
    for candidate in outputs[0].raw:
        if field not in candidate.source_field_keys:
            continue
        assert 'p01' not in candidate.focus_player_ids and meta(candidate).get('answer_key') != 'p01'
        if candidate.source_field_keys == (field,):
            # A cross-domain candidate may involve p01 through the other, shared dimension.
            assert 'p01' not in candidate.involved_player_ids
            assert 'דנה' not in ' '.join(o.text for o in candidate.options) + candidate.explanation


def test_scenario_10_a_withheld_horror_pick_is_not_counted():
    rows = [base_row(i, favorite_movie=m) for i, m in enumerate(('המסור', 'לזמן את הרוע', 'שרק', 'היומן', 'מטריקס'))]
    shared = summarize(dataset(rows), KB).get('movie.genre')
    withheld = summarize(dataset(rows, hidden={0: ('favorite_movie',)}), KB).get('movie.genre')
    assert (shared.count('movie.horror'), withheld.count('movie.horror')) == (2, 1)
    assert (len(shared.consented), len(withheld.consented)) == (5, 4)


# ----- Scenario 11 and 12: wording ------------------------------------------------------------

IMPLEMENTATION_WORDS = re.compile(r'שדה|ערך|ערכים|רשומה|נתון|מיפוי|קטגוריה|סמנטי|\bfield\b|\bvalue\b|\brecord\b|categor|semantic|mapp')
CHOICE_VALUES = ('Pop', 'Rock', 'Mizrahi', 'Electronic', 'Hip-Hop / Rap', 'Israeli Pop', 'Jazz', 'Trance', 'Other')
SINGULAR_WITH_PLURAL_VERB = re.compile(r'(אדם אחד|(?<![\d])1) ו?(בחרו|גרים|אוהבים)')


def test_scenario_11_hundreds_of_hebrew_questions_use_plain_spoken_hebrew():
    questions = [(q, room) for room in rooms.AUDIT_ROOMS for seed in (1, 2, 3)
                 for q in GENERATOR.generate(room.dataset('he'), question_count=20, time_limit_seconds=20, seed=seed)]
    assert len(questions) >= 500
    for q, room in questions:
        rendered = ' '.join((q.text, q.explanation, *(o.text for o in q.options)))
        assert not IMPLEMENTATION_WORDS.search(rendered), (room.name, rendered)
        assert '{' not in rendered and '}' not in rendered and 'None' not in rendered
        assert not SINGULAR_WITH_PLURAL_VERB.search(rendered), rendered
        assert re.search('[א-ת]', q.text), q.text
        assert not any(value in q.text or value in (o.text for o in q.options) for value in CHOICE_VALUES), q.text
    assert Counter(q.source_rule_id for q, _ in questions)['group_comparison_semantic'] > 0


@pytest.mark.parametrize('language', ['he', 'en'])
def test_scenario_11_a_count_of_one_takes_a_singular_verb(language):
    from app.domain.questions.discovery_language import Wording
    from app.domain.questions.discovery_rules import IntersectionCountRule
    ds = dataset([base_row(i) for i in range(10)], language)
    summary, words, rule = summarize(ds, KB), Wording(language, KB), IntersectionCountRule(KB)
    expected = {('place.region', 'food.cuisine'): ('אדם אחד גר ', 'One person lives in '),
                ('music.genre', 'hobby.family'): ('אדם אחד בחר גם ', 'One person chose both ')}
    for (key_a, key_b), (hebrew, english) in expected.items():
        first, second = summary.get(key_a), summary.get(key_b)
        category_a, category_b = next((a, b) for a in first.represented() for b in second.represented()
                                      if len(set(first.members[a]) & set(second.members[b])) == 1)
        both = tuple(p for p in first.members[category_a] if p in second.members[category_b])
        explanation = rule.intersect(summary, words, Random(1), first, second, category_a, category_b, both).explanation
        assert explanation.startswith(hebrew if language == 'he' else english), explanation
        assert not SINGULAR_WITH_PLURAL_VERB.search(explanation), explanation


@pytest.mark.parametrize('room', rooms.AUDIT_ROOMS, ids=lambda r: r.name)
def test_scenario_12_hebrew_and_english_games_ask_the_same_facts(room):
    hebrew = trace(room.dataset('he'), seed=23)
    english = trace(room.dataset('en'), seed=23)

    def facts(t):
        return [(c.source_rule_id, meta(c).get('family'), c.semantic_key, meta(c).get('answer_key'),
                 c.correct_option_id) for c in t.selected]

    assert facts(hebrew) == facts(english)
    for he, en in zip(hebrew.questions, english.questions):
        assert he.language == 'he' and en.language == 'en'
        if he.knowledge_version:
            assert re.search('[א-ת]', he.text) and he.text != en.text


# ----- mechanics ------------------------------------------------------------------------------


def test_overlapping_genres_are_compared_as_appearances_and_explained():
    movies = ('Toy Story', 'Finding Nemo', 'Home Alone', 'Up', 'The Conjuring', 'The Godfather', 'Joker', 'Saw')
    ds = dataset([base_row(i, favorite_movie=m) for i, m in enumerate(movies)], 'en')
    genre = summarize(ds, KB).get('movie.genre')
    both = set(genre.members['movie.comedy']) & set(genre.members['movie.adventure'])
    assert both  # Animated comedies are also adventures.
    for c in produced(GroupComparisonRule, ds):
        if c.semantic_key[1] != 'movie.genre':
            continue
        _, _, a, b = c.semantic_key
        overlap = set(genre.members[a]) & set(genre.members[b])
        if overlap:
            assert 'appears more' in c.text or 'shows up more' in c.text
            assert 'count for both' in c.explanation or 'counts for both' in c.explanation
        assert 2 * len(overlap) < min(genre.count(a), genre.count(b))


def test_parent_labels_never_compete_with_their_own_children():
    ds = dataset([base_row(i, hobby=h, favorite_music=m) for i, (h, m) in enumerate(
        (('ריצה', 'Trance'), ('פילאטיס', 'House'), ('כדורגל', 'Techno'), ('ציור', 'Pop'), ('שחייה', 'Pop')))])
    summary = summarize(ds, KB)
    assert 'hobby.fitness' not in summary.get('hobby.family').categories
    assert summary.get('hobby.family').count('hobby.sport') == 4
    assert summary.get('music.genre').members['music.electronic'] == ('p01', 'p02', 'p03')
    for c in produced(GroupMajorityRule, ds):
        assert not {'כושר גופני', 'פעילות במים', 'טראנס', 'האוס'} & {o.text for o in c.options}


def test_music_choices_are_direct_unless_grouping_merges_different_choices():
    merged = dataset([base_row(i, favorite_music=m) for i, m in enumerate(('Trance', 'House', 'Pop', 'Rock', 'Pop'))])
    literal = dataset([base_row(i, favorite_music=m) for i, m in enumerate(('Pop', 'Pop', 'Rock', 'Rock', 'Jazz'))])
    electronic = next(c for c in produced(GroupCountRule, merged)
                      if c.semantic_key == ('SEMANTIC_COUNT', 'music.genre', 'music.electronic'))
    pop = next(c for c in produced(GroupCountRule, literal) if c.semantic_key == ('SEMANTIC_COUNT', 'music.genre', 'music.pop'))
    assert meta(electronic)['kind'] == 'semantic'
    assert (meta(pop)['kind'], meta(pop)['family']) == ('direct', 'DIRECT_CHOICE')


def test_consensus_classification_recognizes_remakes_and_spelling_variants():
    assert KB.resolve_movie('Titanic').entity is None  # Identity stays ambiguous…
    assert 'movie.drama' in KB.classify('movies', 'Titanic').category_ids  # …but every Titanic is a drama.
    assert not KB.classify('movies', 'It').category_ids  # No shared classification: unknown.
    assert 'hobby.sport' in KB.classify('hobbies', 'יוגה').category_ids
    assert KB.resolve_israeli_locality('קרית שמונה').entity == KB.resolve_israeli_locality('קריית שמונה').entity
    ds = dataset([base_row(i, city=c) for i, c in enumerate(('קרית שמונה', 'חיפה', 'תל אביב', 'באר שבע'))])
    assert not summarize(ds, KB).get('place.region').unknown


def test_selection_is_deterministic_and_discoveries_carry_explanations():
    ds = rooms.MIXED_EN.dataset()
    first, second = trace(ds, seed=99), trace(ds, seed=99)
    assert first.questions == second.questions
    for q, c in zip(first.questions, first.selected):
        if meta(c).get('kind') != 'direct':
            assert q.explanation and q.knowledge_version == KB.version


_SETTLING_FAMILIES = {
    'group_mode': 'leader', 'region_majority': 'leader', 'group_comparison_semantic': 'pair',
    'region_comparison': 'pair', 'group_distribution': 'distribution', 'group_minority': 'minority',
    'group_count': 'count', 'region_count': 'count', 'group_unique': 'unique', 'region_unique': 'unique',
    'group_filtered_mode': 'subgroup_leader', 'group_subgroup_comparison': 'subgroup_pair',
    'group_intersection_count': 'intersection', 'most_common_value': 'raw_leader', 'group_comparison': 'raw_pair',
    'value_count': 'raw_count',
}


def answered_by_earlier_questions(t, ds):
    """Later questions that an earlier question or its explanation already settles, in presentation order.

    Derived from each family's fact, the players' answers and the room's counts, independently of the
    selector's bookkeeping. A key is a dimension, a raw answer field, or a dimension within a subgroup.
    """
    summary = summarize(ds, KB)
    counted, leading, single, pairs, found = defaultdict(set), defaultdict(set), defaultdict(set), set(), []
    for c in t.selected:
        operation = _SETTLING_FAMILIES.get(c.source_rule_id)
        if operation is None:
            continue
        fact, winner = c.semantic_key[1:], meta(c).get('answer_key')
        if operation.startswith('raw_'):
            key = c.source_field_keys[0]
            value_of = {p: str(normalize(v)) for p, v in ds.values_for(key)}
            categories = sorted({value_of[p] for p in c.involved_player_ids})
            winner = categories[0]
        elif operation.startswith('subgroup'):
            key, categories = tuple(fact[:3]), list(fact[3:])
        elif operation == 'intersection':
            key_a, category_a, key_b, category_b = fact
            sides = (((key_a, category_a, key_b), category_b), ((key_b, category_b, key_a), category_a))
        else:
            key, *categories = fact
        settled = {
            'leader': lambda: winner in leading[key],
            'raw_leader': lambda: winner in leading[key],
            'subgroup_leader': lambda: winner in leading[key],
            'pair': lambda: bool(set(categories) & leading[key]) or set(categories) <= counted[key],
            'raw_pair': lambda: bool(set(categories) & leading[key]) or set(categories) <= counted[key],
            'subgroup_pair': lambda: bool(set(categories) & leading[key]) or set(categories) <= counted[key],
            'distribution': lambda: winner in leading[key] or set(categories) <= counted[key],
            'minority': lambda: winner in single[key] or set(categories) <= counted[key],
            'count': lambda: categories[0] in counted[key],
            'raw_count': lambda: categories[0] in counted[key],
            'intersection': lambda: any(category in counted[within] for within, category in sides),
            'unique': lambda: False,  # Asks who, which no count discloses.
        }[operation]()
        if operation in ('subgroup_leader', 'intersection'):
            # The same two categories' shared members, asked again from the other side.
            pair = (frozenset({(key[0], key[1]), (key[2], winner)}) if operation == 'subgroup_leader'
                    else frozenset({(key_a, category_a), (key_b, category_b)}))
            settled = settled or pair in pairs
            pairs.add(pair)
        if settled:
            found.append(c.text)
        if operation == 'leader':
            named = {winner}
            if 'Second:' in c.explanation or 'במקום השני' in c.explanation:
                s = summary.get(key)
                counts = {x: s.count(x) for x in s.categories if x != winner and s.count(x)}
                named.add(max(counts, key=counts.get))
            leading[key] |= named
            counted[key] |= named
        elif operation == 'raw_leader':
            leading[key].add(winner)  # No explanation: only the answer is shown.
        elif operation in ('subgroup_leader', 'subgroup_pair'):
            if operation == 'subgroup_leader':
                leading[key].add(winner)
            counted[key] |= {winner} if operation == 'subgroup_leader' else set(categories)
            counted[key[0]].add(key[1])  # "Nine people live in the center."
        elif operation == 'intersection':
            for within, category in sides:
                counted[within].add(category)
        elif operation == 'distribution':
            leading[key].add(winner)
            counted[key] |= set(categories)
        elif operation in ('count', 'unique'):
            counted[key] |= set(categories)
            if operation == 'unique' or winner == '1':
                single[key] |= set(categories)
            if operation == 'count' and 2 * int(winner) >= len(summary.get(key).consented):
                leading[key] |= set(categories)  # Half the shared answers wins any race that is asked.
        elif operation == 'raw_count':
            counted[key] |= set(categories)
            if 2 * len(c.involved_player_ids) >= len(ds.values_for(key)):
                leading[key] |= set(categories)
        elif operation in ('pair', 'minority'):
            counted[key] |= set(categories)
    return found


@pytest.mark.parametrize('room', list({r.name: r for r in (*rooms.AUDIT_ROOMS, *rooms.DIAGNOSTIC_ROOMS)}.values()),
                         ids=lambda r: r.name)
def test_no_question_is_answered_by_one_shown_before_it(room):
    """Before this rule most games had one, e.g. "most of you live in the center", later "center or south?"."""
    ds = room.dataset()
    for seed in (11, 12):
        t = trace(ds, seed=seed)
        assert len(t.questions) == 20
        assert answered_by_earlier_questions(t, ds) == []


def test_selector_prefers_the_fact_that_settles_others_and_respects_presentation_order():
    from app.domain.questions.candidate import QuestionCandidate
    from app.domain.questions.question import Difficulty, QuestionOption
    from app.domain.questions.selector import QuestionSelector

    def rank(c):
        return ('rank', 'hobby.family', c)

    def count(c):
        return ('count', 'hobby.family', c)

    def fact(text, difficulty, family, score, reveals, needs):
        candidate = QuestionCandidate(
            text, (QuestionOption('a', 'x'), QuestionOption('b', 'y')), 'a', family.lower(), ('hobby',), ('p01',),
            difficulty, semantic_key=(family, text),
            metadata=(('kind', 'semantic'), ('family', family), ('domain', 'hobby'), ('reveals', reveals),
                      ('needs', needs)))
        return candidate, score

    leader = fact('Which type leads?', Difficulty.EASY, 'SEMANTIC_MAJORITY', 0.5,
                  (rank('sport'), count('sport')), ((rank('sport'),),))
    sport_or_art = fact('Sport or art?', Difficulty.MEDIUM, 'SEMANTIC_COMPARISON', 0.9, (count('sport'), count('art')),
                        ((rank('sport'),), (rank('art'),), (count('sport'), count('art'))))
    sport_count = fact('How many chose sport?', Difficulty.EASY, 'SEMANTIC_COUNT', 0.45, (count('sport'),),
                       ((count('sport'),),))
    art_count = fact('How many chose art?', Difficulty.EASY, 'SEMANTIC_COUNT', 0.4, (count('art'),), ((count('art'),),))
    reading_or_games = fact('Reading or games?', Difficulty.MEDIUM, 'SEMANTIC_COMPARISON', 0.3,
                            (count('reading'), count('games')),
                            ((rank('reading'),), (rank('games'),), (count('reading'), count('games'))))
    selector = QuestionSelector(group_first=True)

    # The leader settles "sport or art?" and discloses the sport count, so both give way to it.
    chosen = selector.select([sport_or_art, sport_count, leader, art_count, reading_or_games], question_count=3)
    assert {c.text for c in chosen} == {'Which type leads?', 'How many chose art?', 'Reading or games?'}
    # An easy count shown before a comparison it does not settle is fine, even though the comparison
    # explanation later repeats that count.
    chosen = selector.select([sport_or_art, art_count], question_count=2)
    assert [c.text for c in chosen] == ['How many chose art?', 'Sport or art?']


def test_production_registry_asks_about_players_never_general_knowledge():
    rules = {r.rule_id for r in GENERATOR._rules}
    assert not rules & {'music_artist_bridge', 'profile_fingerprint', 'similar_to_player', 'attribute_chain',
                        'category_coverage', 'filtered_mode', 'second_largest_group', 'group_scoped_count'}
    for rule in discovery_rules(KB):
        assert rule.rule_id in rules
    t = trace(rooms.MIXED_EN.dataset(), seed=3)
    years = re.compile(r'\b(19|20)\d\d\b')
    assert not any(years.search(q.text) for q in t.questions)


def test_thirty_player_twenty_question_generation_stays_fast():
    rows = [row for room in (rooms.HE_RICH, rooms.MOVIE_HEAVY) for row in room.rows][:30]
    ds = rooms.Room('thirty', 'he', tuple(rows)).dataset()
    GENERATOR.generate(ds, question_count=20, time_limit_seconds=20, seed=1)
    timings = []
    for seed in range(3):
        started = perf_counter()
        assert len(GENERATOR.generate(ds, question_count=20, time_limit_seconds=20, seed=seed)) == 20
        timings.append(perf_counter() - started)
    assert sorted(timings)[1] < 0.5, timings


def test_validator_allows_either_or_questions_but_not_a_named_answer():
    from dataclasses import replace
    from app.domain.questions.candidate import QuestionCandidate
    from app.domain.questions.question import QuestionOption
    ds = dataset([base_row(i) for i in range(3)])
    either = QuestionCandidate('מה יש יותר בקבוצה — חובבי אימה או מדע בדיוני?',
                               (QuestionOption('a', 'אימה'), QuestionOption('b', 'מדע בדיוני')), 'b', 'rule',
                               ('city',), ('p01',))
    assert QuestionValidator().rejection_reason(either, ds) is None
    leak = replace(either, text='רוב הקבוצה בחרה מדע בדיוני. מה בחרו?')
    assert QuestionValidator().rejection_reason(leak, ds) == 'answer_named_in_question'


def test_quotas_follow_supply_and_never_pad_a_missing_kind():
    from app.domain.questions.selector import plan_quotas
    assert plan_quotas(20, {'semantic': 40, 'direct': 40, 'geographic': 40, 'cross_domain': 40}) == {
        'semantic': 9, 'direct': 5, 'geographic': 3, 'cross_domain': 3}
    limited = plan_quotas(20, {'semantic': 4, 'direct': 40, 'geographic': 2, 'cross_domain': 0})
    assert limited['semantic'] == 4 and limited['geographic'] == 2 and limited['cross_domain'] == 0
    assert sum(limited.values()) == 20
    assert plan_quotas(20, {'semantic': 3, 'direct': 2}) == {'semantic': 3, 'direct': 2}


def test_information_value_prefers_discoveries_over_lookups():
    t = trace(rooms.HE_RICH.dataset())
    scores = {}
    for candidate, score in t.scored:
        scores.setdefault(meta(candidate).get('family'), []).append(score)
    best = {family: max(values) for family, values in scores.items()}
    assert best['SEMANTIC_MAJORITY'] > best['DIRECT_UNIQUE']
    assert best['CROSS_SUBGROUP_MAJORITY'] > best['DIRECT_COUNT']
    assert all(0.0 <= s <= 1.0 for _, s in t.scored)


def test_most_of_the_group_means_most_of_the_room_even_when_towns_are_withheld():
    ds = rooms.CONSENT_RESTRICTED.dataset()
    region = summarize(ds, KB).get('place.region')
    assert (len(region.consented), region.count('region.central'), ds.player_count) == (11, 7, 14)
    majority = next(c for c in produced(RegionMajorityRule, ds))
    assert 'רוב' not in majority.text  # 7 of the 14 visible players is not most of the group.
    few_shared = dataset([base_row(i, favorite_movie=m) if i < 6 else base_row(i)
                          for i, m in enumerate(HORROR_ONLY[:4] + ('Challengers (film)', 'Greyhound (film)') + ('',) * 8)], 'en')
    assert not [c for c in produced(GroupMajorityRule, few_shared) if 'favorite_movie' in c.source_field_keys]
