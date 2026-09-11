"""Truth fixtures per family, privacy invariance, progression and classroom bounds."""

from dataclasses import replace
from random import Random
from time import perf_counter
import re

import pytest

from app.domain.game import Player, PlayerProfile, ProfileField
from app.domain.questions import ProfileDataset, QuestionGenerator, QuestionValidator, default_rules
from app.domain.questions.question import Difficulty
from app.domain.questions.language import normalize


FIELDS = ('city', 'favorite_food', 'hobby', 'favorite_music', 'favorite_movie', 'age')
STANDARD = [
    ('X', 'pizza', 'chess', 'Rock', 'Up', 10),
    ('X', 'sushi', 'chess', 'Pop', 'Cars', 13),
    ('Y', 'pizza', 'running', 'Rock', 'Up', 18),
    ('Z', 'pizza', 'drawing', 'Jazz', 'Dune', 25),
]


def dataset(rows, *, language='en', hidden=False, omit=False):
    players = []
    for i, row in enumerate(rows):
        pid = f'p{i}'
        fields = dict(row) if isinstance(row, dict) else dict(zip(FIELDS, row))
        facts = [ProfileField(k, v, True) for k, v in fields.items()]
        if hidden and not omit:
            facts += [ProfileField('personal_fact', 'PRIVATE_NOT_FOR_QUESTIONS', False)]
        players.append(Player(pid, chr(65 + i) if i < 26 else f'Person{i}',
                              profile=PlayerProfile(pid, tuple(facts))))
    return ProfileDataset(players, language=language)


def food_counts(*counts):
    return [{'favorite_food': name} for name, count in zip(('pizza', 'sushi', 'tacos'), counts) for _ in range(count)]


# Each first candidate has a manually calculated answer. Compact fixtures make
# every comparison auditable, including those that require four or more people.
CASES = [
    ('unique_value', STANDARD, 'C', 'EASY'),
    ('most_common_value', STANDARD, 'X', 'EASY'),
    ('value_count', STANDARD, '2', 'EASY'),
    ('multi_attribute', STANDARD, 'A', 'MEDIUM'),
    ('profile_fingerprint', [('X','pizza','chess'), ('X','pizza','run'), ('X','sushi','chess'), ('Y','pizza','chess')], 'A', 'HARD'),
    ('most_similar_pair', STANDARD, 'A + C', 'MEDIUM'),
    ('similar_to_player', STANDARD, 'C', 'MEDIUM'),
    ('odd_one_out', food_counts(3,1), 'D', 'MEDIUM'),
    ('filtered_mode', [('X','pizza'), ('X','pizza'), ('X','sushi'), ('Y','tacos')], 'pizza', 'HARD'),
    ('shared_reference', STANDARD, 'B', 'MEDIUM'),
    ('group_comparison', STANDARD, 'X', 'EASY'),
    ('least_common_value', food_counts(3,2,1), 'tacos', 'MEDIUM'),
    ('minority_fraction', food_counts(4,1), 'sushi', 'MEDIUM'),
    ('attribute_chain', [('X','pizza','chess'), ('Y','sushi','chess'), ('X','sushi','running'), ('X','tacos','chess'), ('Z','pizza','chess')], 'C', 'HARD'),
    ('cross_person_similarity', [('X','pizza','run'), ('Y','sushi','chess'), ('X','pizza','chess'), ('Z','tacos','draw')], 'C', 'HARD'),
    ('commonality_count', STANDARD, '2', 'MEDIUM'),
    ('group_exception', food_counts(3,1), 'D', 'MEDIUM'),
    ('conditional_youngest', [{'city':'X','age':13}, {'city':'X','age':15}, {'city':'X','age':18}, {'city':'Y','age':10}], 'A', 'HARD'),
    ('age_ranking', STANDARD, 'D', 'EASY'),
    ('second_largest_group', food_counts(4,2,1), 'sushi', 'MEDIUM'),
    ('pair_match', [('X','pizza'), ('X','pizza'), ('Y','sushi'), ('Z','tacos')], 'A + B', 'HARD'),
    ('shared_but_different', [('X','pizza'), ('X','sushi'), ('Y','pizza')], 'B', 'MEDIUM'),
    ('category_coverage', [('X','pizza'), ('X','sushi'), ('X','tacos'), ('Y','pizza'), ('Y','pizza')], 'X', 'HARD'),
    ('unique_connection', [('X','pizza'), ('X','sushi'), ('Y','pizza'), ('X','tacos')], 'A', 'HARD'),
    ('two_step_elimination', [('X','pizza'), ('X','sushi'), ('Y','pizza')], 'B', 'MEDIUM'),
    ('closest_age_pair', STANDARD, 'A + B', 'MEDIUM'),
    ('balanced_split', [('X','pizza'), ('X','pizza'), ('Y','pizza'), ('Y','sushi')], 'city', 'MEDIUM'),
    ('rarest_profile', [('X','pizza'), ('X','sushi'), ('Y','pizza'), ('X','tacos')], 'C', 'HARD'),
    ('exact_overlap_pair', STANDARD, 'A + B', 'HARD'),
]
RULES = {rule.rule_id: rule for rule in default_rules()}


def correct(candidate):
    return next(o.text for o in candidate.options if o.option_id == candidate.correct_option_id)


@pytest.mark.parametrize('rule_id,rows,answer,difficulty', CASES, ids=[c[0] for c in CASES])
@pytest.mark.parametrize('language', ['en', 'he'])
def test_each_family_has_proven_answer_bilingual_rendering_and_determinism(rule_id, rows, answer, difficulty, language):
    source = dataset(rows, language=language)
    rule = RULES[rule_id]
    candidates = rule.generate(source, Random(81))
    assert candidates
    assert candidates == rule.generate(source, Random(81))
    expected = 'עיר' if answer == 'city' and language == 'he' else answer
    assert correct(candidates[0]) == expected
    assert all(c.difficulty.value == difficulty for c in candidates)
    assert all(QuestionValidator().is_valid(c, source) for c in candidates)
    for candidate in candidates:
        assert bool(re.search('[א-ת]', candidate.text)) == (language == 'he')
        assert '{' not in candidate.text and '}' not in candidate.text
        assert len({normalize(o.text) for o in candidate.options}) == len(candidate.options)


@pytest.mark.parametrize('rule_id,rows,answer,difficulty', CASES, ids=[c[0] for c in CASES])
def test_every_family_ignores_hidden_data_and_rejects_no_consent(rule_id, rows, answer, difficulty):
    rule = RULES[rule_id]
    assert rule.generate(dataset(rows, hidden=True), Random(7)) == rule.generate(dataset(rows, omit=True), Random(7))
    denied = []
    for i, row in enumerate(rows):
        pid = f'p{i}'
        fields = dict(row) if isinstance(row, dict) else dict(zip(FIELDS, row))
        private = tuple(ProfileField(k, 'WITHHELD' if isinstance(v, str) else 99, False) for k, v in fields.items())
        denied.append(Player(pid, chr(65+i), profile=PlayerProfile(pid, private)))
    assert rule.generate(ProfileDataset(denied), Random(7)) == ()
    assert rule.generate(ProfileDataset([]), Random(7)) == ()


@pytest.mark.parametrize('rule_id,rows,answer,difficulty', CASES, ids=[c[0] for c in CASES])
def test_withdrawing_each_used_field_is_identical_to_omitting_it(rule_id, rows, answer, difficulty):
    """Even suppression and distractors must be independent of private values."""
    rule = RULES[rule_id]
    records = [dict(row) if isinstance(row, dict) else dict(zip(FIELDS, row)) for row in rows]
    for field in {key for row in records for key in row}:
        omitted = [dict(row) for row in records]
        omitted[0].pop(field, None)
        players = []
        for i, row in enumerate(records):
            pid = f'p{i}'
            facts = tuple(ProfileField(k, ('PRIVATE_CHANGED' if isinstance(v, str) else 99)
                                       if i == 0 and k == field else v, not (i == 0 and k == field))
                          for k, v in row.items())
            players.append(Player(pid, chr(65+i), profile=PlayerProfile(pid, facts)))
        assert rule.generate(ProfileDataset(players), Random(31)) == rule.generate(dataset(omitted), Random(31))


@pytest.mark.parametrize('rule_id', [c[0] for c in CASES[3:]])
def test_new_families_require_at_least_three_participants(rule_id):
    assert RULES[rule_id].generate(dataset(STANDARD[:2]), Random(13)) == ()


@pytest.mark.parametrize('rule_id', list(RULES))
def test_symmetric_ties_cannot_invent_unique_winners(rule_id):
    source = dataset([('X','pizza','chess','Rock','Up',20)] * 6)
    candidates = RULES[rule_id].generate(source, Random(5))
    # A count has a single correct numeric answer even when everyone ties.
    if rule_id in ('value_count', 'commonality_count'):
        assert candidates
        assert all(correct(c) in ('5','6') for c in candidates)
    else:
        assert candidates == ()


def test_registry_is_unique_and_every_production_family_has_a_truth_fixture():
    assert len(RULES) == len(default_rules()) == len(CASES) == 29
    assert set(RULES) == {c[0] for c in CASES}


def classroom_rows(n=30):
    rng = Random(223)
    return [(f'City {rng.randrange(4)}', f'Food {rng.randrange(4)}', f'Hobby {rng.randrange(4)}',
             ('Pop','Rock','Jazz')[rng.randrange(3)], f'Movie {rng.randrange(5)}', 12+rng.randrange(12)) for _ in range(n)]


def test_full_twenty_question_curve_is_diverse_deterministic_and_fast():
    source = dataset(classroom_rows())
    before = perf_counter()
    result = QuestionGenerator().generate(source, question_count=20, time_limit_seconds=20, seed=42)
    elapsed = perf_counter() - before
    assert elapsed < 2.0, f'30-player generation took {elapsed:.3f}s'
    assert len(result) == 20
    assert result == QuestionGenerator().generate(source, question_count=20, time_limit_seconds=20, seed=42)
    assert [q.difficulty for q in result] == [Difficulty.EASY]*5 + [Difficulty.MEDIUM]*9 + [Difficulty.HARD]*6
    assert len({q.source_rule_id for q in result}) >= 12
    assert len({normalize(q.text) for q in result}) == 20
    print(f'30 players / 20 questions: {elapsed:.4f}s, {len({q.source_rule_id for q in result})} rules')


@pytest.mark.parametrize('count', [1,5,20,50])
def test_custom_count_is_respected(count):
    result = QuestionGenerator().generate(dataset(classroom_rows()), question_count=count, time_limit_seconds=20, seed=3)
    assert len(result) == count
    assert all(q.total_questions == count for q in result)


def test_sparse_data_uses_valid_available_difficulty_without_duplicates():
    result = QuestionGenerator().generate(dataset([{'city':'X'}]*3), question_count=20, time_limit_seconds=20, seed=1)
    assert len(result) == 1
    assert result[0].difficulty == Difficulty.EASY
    assert result[0].total_questions == 1


def test_nfc_whitespace_case_are_comparison_only_and_hebrew_is_preserved():
    source = dataset([{'city':' Tel   Aviv '}, {'city':'tel aviv'}, {'city':'חיפה'}])
    questions = RULES['most_common_value'].generate(source, Random(8))
    assert correct(questions[0]) == ' Tel   Aviv '
    assert normalize('e\u0301') == normalize('é')
    assert normalize('תל אביב') == 'תל אביב'


def test_missing_consent_is_not_inequality_and_age_is_not_a_preference():
    source = dataset([{'city':'X'}, {'city':'X','favorite_food':'pizza'}, {'city':'Y','favorite_food':'sushi'}])
    assert RULES['shared_but_different'].generate(source, Random(1)) == ()
    assert RULES['two_step_elimination'].generate(source, Random(1)) == ()
    age_only = dataset([{'age':20}, {'age':20}, {'age':21}])
    assert RULES['most_similar_pair'].generate(age_only, Random(1)) == ()
    assert RULES['commonality_count'].generate(age_only, Random(1)) == ()


def test_fingerprint_rejects_redundant_third_clue():
    source = dataset(STANDARD)
    assert RULES['profile_fingerprint'].generate(source, Random(3)) == ()


@pytest.mark.parametrize('value', ['<script>alert(1)</script>', '<img src=x onerror=alert(1)>', "O'Reilly \"Hi\"", 'עברית?! {name}'])
def test_player_values_are_interpolated_once_as_literal_data(value):
    source = dataset([{'city':value}, {'city':'X'}, {'city':'Y'}], language='he')
    candidates = RULES['unique_value'].generate(source, Random(1))
    assert value in candidates[0].text
    assert correct(candidates[0]) == 'A'


def test_quality_gate_rejects_equivalent_distractors_and_overlong_rendered_text():
    source = dataset(STANDARD)
    candidate = RULES['unique_value'].generate(source, Random(1))[0]
    assert not QuestionValidator().is_valid(replace(candidate, text='x'*601), source)
    assert not QuestionValidator().is_valid(replace(candidate, options=(candidate.options[0], replace(candidate.options[1], text=candidate.options[0].text.upper()))), source)


def test_insufficient_hard_questions_fill_with_valid_lower_difficulties():
    from app.domain.questions import QuestionSelector
    source = dataset(classroom_rows())
    candidates = [c for rule in default_rules() for c in rule.generate(source, Random(9))
                  if QuestionValidator().is_valid(c, source)]
    hard = [c for c in candidates if c.difficulty == Difficulty.HARD][:1]
    others = [c for c in candidates if c.difficulty != Difficulty.HARD]
    result = QuestionSelector().select([(c, .5) for c in others + hard], question_count=20)
    assert len(result) == 20
    assert sum(c.difficulty == Difficulty.HARD for c in result) == 1
    assert len({normalize(c.text) for c in result}) == 20


def test_selector_avoids_recent_same_person_field_when_an_equal_alternative_exists():
    from app.domain.questions import QuestionSelector
    source = dataset(STANDARD)
    first = RULES['unique_value'].generate(source, Random(2))[0]
    a = replace(first, text='First?', source_rule_id='first', focus_player_ids=('p2',), difficulty=Difficulty.MEDIUM)
    repeated = replace(first, text='Repeated?', source_rule_id='second', focus_player_ids=('p2',), difficulty=Difficulty.MEDIUM)
    fresh = replace(first, text='Fresh?', source_rule_id='third', focus_player_ids=('p1',), difficulty=Difficulty.MEDIUM)
    selected = QuestionSelector().select([(a,1),(repeated,.5),(fresh,.5)], question_count=2)
    assert [c.text for c in selected] == ['First?','Fresh?']


def test_quality_gate_rejects_a_clue_that_accidentally_names_its_answer():
    source = dataset(STANDARD)
    candidate = RULES['most_common_value'].generate(source, Random(1))[1]
    assert not QuestionValidator().is_valid(replace(candidate, text='The answer is pizza; which food?'), source)
