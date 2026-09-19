"""Recognition must improve without inventing identities or bypassing consent."""
from dataclasses import replace
from itertools import product
import gc
import json
from pathlib import Path
from statistics import median
import socket
import tracemalloc
from time import perf_counter

import pytest

from app.domain.game import Player, PlayerProfile, ProfileField
from app.domain.questions import ProfileDataset, QuestionGenerator
from app.domain.questions.knowledge import Category, KnownEntity, KnowledgeBase, Match, normalize_name
from app.domain.questions.name_matching import bounded_distance, MAX_CANDIDATES
from app.infrastructure.knowledge import get_knowledge, load_knowledge

ROOT = Path(__file__).resolve().parents[3]
CORPUS = json.loads((ROOT / 'scripts/knowledge/resolution-evaluation.json').read_text())
KB = get_knowledge()
FIELDS = dict(favorite_movie='movies', favorite_song='songs', favorite_artist='artists',
              favorite_music='music', favorite_food='foods', hobby='hobbies', city='localities')


def dataset(room, language='he'):
    return ProfileDataset([
        Player(str(i), row['name'], profile=PlayerProfile(str(i), tuple(
            ProfileField(k, v, k not in row['hide']) for k, v in row['values'].items())))
        for i, row in enumerate(room['rows'])], language)


def generate(room, language='he', seed=11):
    return QuestionGenerator(knowledge=KB).trace(dataset(room, language), question_count=20,
                                                time_limit_seconds=20, seed=seed)


@pytest.mark.parametrize('case', CORPUS['cases'], ids=lambda c: c['kind']+':'+c['text'])
def test_frozen_corpus_has_no_false_positive_identities(case):
    result = KB.resolve(case['kind'], case['text'])
    actual = result.entity.canonical_id if result.entity else None
    assert actual is None or actual == case['expected_id']
    assert result.high_confidence == (actual is not None)


def test_imperfect_recognition_improves_on_frozen_baseline_without_losing_controls():
    imperfect = [c for c in CORPUS['cases'] if c['group']=='imperfect']
    correct = sum((r := KB.resolve(c['kind'], c['text'])).entity is not None
                  and r.entity.canonical_id == c['expected_id'] for c in imperfect)
    assert correct >= 100  # Baseline: 39/106, before changing resolver code.
    for c in CORPUS['cases']:
        if c['group'] in ('canonical', 'short_exact_control'):
            assert KB.resolve(c['kind'], c['text']).entity.canonical_id == c['expected_id']


@pytest.mark.parametrize('kind,text,confidence', [
    ('movies', 'The Conjuring', Match.EXACT), ('localities', 'ת״א', Match.ALIAS),
    ('foods', '  ＰＩＺＺＡ  ', Match.NORMALIZED), ('localities', 'קריית-שמונה', Match.NORMALIZED),
    ('localities', 'קרית שמונה', Match.NORMALIZED), ('localities', 'רמת גנ', Match.NORMALIZED),
    ('movies', 'Conjuring', Match.PARTIAL_HIGH_CONFIDENCE),
    ('movies', 'The Conjruing', Match.FUZZY_HIGH_CONFIDENCE),
    ('artists', 'Omer Adma', Match.FUZZY_HIGH_CONFIDENCE),
    ('songs', 'Blank Spce', Match.FUZZY_HIGH_CONFIDENCE),
    ('foods', 'Falafell', Match.FUZZY_HIGH_CONFIDENCE),
    ('hobbies', 'Photograpy', Match.FUZZY_HIGH_CONFIDENCE),
    ('music', 'Electornic', Match.FUZZY_HIGH_CONFIDENCE),
    ('localities', 'Jeruslaem', Match.FUZZY_HIGH_CONFIDENCE),
])
def test_explainable_stages_across_all_domains(kind, text, confidence):
    result = KB.resolve(kind, text)
    assert result.entity and result.high_confidence and result.reason
    assert result.match == confidence
    if confidence == Match.FUZZY_HIGH_CONFIDENCE:
        assert result.similarity >= .82
        assert result.similarity-result.runner_up_similarity >= .08


@pytest.mark.parametrize('a,b', [('תֵּל־אָבִיב', 'תל אביב'), ('ת״א', 'ת"א'),
                               ('Hip—Hop', 'hip hop'), ('AC/DC', 'ac-dc'),
                               ('  Blank\t Space! ', 'blank space'), ('ג’חנון', 'ג׳חנון')])
def test_normalization(a, b):
    assert normalize_name(a) == normalize_name(b)


def tiny(names, *, kind='artists'):
    categories = (Category('music.pop', 'music.genre', 'Pop', 'פופ'),)
    entities = [KnownEntity(f'Q{i+1}', kind, name, '', (), frozenset({'music.pop'})) for i,name in enumerate(names)]
    return KnowledgeBase(entities, categories, 'test')


def test_equal_fuzzy_candidates_and_small_margin_fail_closed_without_shared_facts():
    kb = tiny(['Miriam Cohen', 'Miriam Cohan'])
    result = kb.resolve_artist('Miriam Cohin')
    assert result.match == Match.AMBIGUOUS and result.reason == 'fuzzy_margin'
    assert result.candidate_count == 2 and result.entity is None
    assert not kb.classify('artists','Miriam Cohin').category_ids
    kb = tiny(['Alexandra Winter', 'Alexandra Wintor'])
    result = kb.resolve_artist('Alexandra Winteq')
    assert result.match == Match.AMBIGUOUS
    assert 0 < result.similarity-result.runner_up_similarity < .08


def test_aliases_of_one_entity_are_not_competing_entities():
    kb = tiny(['Miriam Cohen'])
    entity = next(iter(kb.entities.values()))
    kb = KnowledgeBase([replace(entity, aliases=('Miriam Cohenn',))], kb.categories.values(), 'test')
    assert kb.resolve_artist('Miriam Cohne').match == Match.FUZZY_HIGH_CONFIDENCE
    assert kb.resolve_artist('Miriam Cohne').candidate_count == 1


def test_partial_collision_cannot_be_resolved_by_tiebreak_or_shared_categories():
    for text in ('Harry Potter','הארי פוטר','Back to Future'):
        result = KB.resolve_movie(text)
        assert result.match == Match.AMBIGUOUS and result.entity is None
        assert not KB.classify('movies', text).category_ids
    kb = tiny(['Amber River North', 'Amber River South'])
    assert kb.resolve_artist('Amber River').match == Match.AMBIGUOUS


def test_unique_partial_needs_full_tokens_and_enough_title_coverage():
    kb = tiny(['Miriam Cohen Quartet'])
    assert kb.resolve_artist('Miriam Cohen').entity is None  # Too much name omitted.
    assert kb.resolve_artist('Miriam Cohe').entity is None  # Not full tokens.
    kb = tiny(['Amber River of Gold'])
    assert kb.resolve_artist('Amber River Gold').match == Match.PARTIAL_HIGH_CONFIDENCE


def test_long_partial_contenders_are_not_lost_at_the_fuzzy_search_boundary():
    kb = tiny(['Amber River of Gold', 'Amber River Gold ' + 'Extended Performance '*5])
    assert kb.resolve_artist('Amber River Gold').match == Match.AMBIGUOUS
    kb = tiny(['The Conjuring', 'A Conjuring'], kind='movies')
    assert kb.resolve_movie('Conjuring').match == Match.AMBIGUOUS


def test_long_title_similarity_cannot_hide_a_close_second_entity():
    stem = 'The Exceptional Adventures of Amber River '
    kb = tiny([stem+'North',stem+'Nortx'], kind='movies')
    result = kb.resolve_movie(stem+'Nortz')
    assert result.match == Match.AMBIGUOUS and result.entity is None


def test_length_capped_score_keeps_unsearched_three_edit_rivals_outside_margin():
    # A correctable one-edit query and any three-edit name differ in length by
    # at most three. The conservative score cap makes that rival safely weaker.
    for length in range(5,65):
        weakest_best = 1-1/min(length,20)
        strongest_outside = 1-3/min(length+3,20)
        assert weakest_best-strongest_outside > .08


def test_spelling_and_punctuation_collisions_never_choose_one_identity():
    base = KB.resolve_israeli_locality('רמת גן').entity
    collision = replace(base, canonical_id='G1', english='Other city', hebrew='רמת גנ')
    kb = KnowledgeBase([base, collision], KB.categories.values(), 'test')
    assert kb.resolve_israeli_locality('רמת גןן').entity is None
    one = replace(base, english='Alpha/Beta', hebrew='', aliases=())
    two = replace(collision, english='Alpha-Beta', hebrew='', aliases=())
    kb = KnowledgeBase([one,two], KB.categories.values(), 'test')
    assert kb.resolve_israeli_locality('Alpha Beta').match == Match.AMBIGUOUS


@pytest.mark.parametrize('kind', tuple(FIELDS.values()))
@pytest.mark.parametrize('value', ['a', 'it', 'rock', 'ro', 'Swa'])
def test_short_inputs_only_use_existing_full_names(kind, value):
    r = KB.resolve(kind,value)
    if r.entity:
        assert r.match in (Match.EXACT, Match.ALIAS, Match.NORMALIZED)
    else:
        assert not r.high_confidence


@pytest.mark.parametrize('query', ['Amber River III', 'Amber River 3', 'Amber River 1999'])
def test_numbers_and_roman_sequels_are_protected(query):
    kb = tiny(['Amber River II', 'Amber River 2', 'Amber River 1998'], kind='movies')
    assert kb.resolve_movie(query).entity is None


def test_same_domain_only_and_no_uncontrolled_transliteration():
    assert KB.resolve_artist('The Conjruing').entity is None
    assert KB.resolve_song('Omer Adma').entity is None
    assert KB.resolve_israeli_locality('tayler swipt').entity is None


def test_candidate_limit_rejects_instead_of_truncating(monkeypatch):
    from app.domain.questions import name_matching
    kb = tiny(['Miriam Cohen','Miriam Cohan'])
    monkeypatch.setattr(name_matching, 'MAX_CANDIDATES', 1)
    r = kb.resolve_artist('Miriam Cohin')
    assert r.entity is None and r.reason == 'fuzzy_search_too_broad'


def test_search_does_not_compare_the_whole_catalog(monkeypatch):
    from app.domain.questions import name_matching
    actual = name_matching.bounded_distance
    calls = []
    def counted(a,b,limit=2):
        calls.append(b)
        return actual(a,b,limit)
    monkeypatch.setattr(name_matching,'bounded_distance',counted)
    assert KB.resolve_artist('Taylor Swfit').entity
    assert 0 < len(calls) <= MAX_CANDIDATES
    assert len(calls) < len(KB.in_kind('artists')) / 10


def reference_distance(a,b):
    # Independent full-matrix OSA oracle; production uses a bounded band.
    d = [[i+j for j in range(len(b)+1)] for i in range(len(a)+1)]
    for i in range(1,len(a)+1):
        for j in range(1,len(b)+1):
            d[i][j] = min(d[i-1][j]+1,d[i][j-1]+1,d[i-1][j-1]+(a[i-1]!=b[j-1]))
            if i>1 and j>1 and a[i-1]==b[j-2] and a[i-2]==b[j-1]:
                d[i][j] = min(d[i][j],d[i-2][j-2]+1)
    return min(d[-1][-1],3)


def test_bounded_edit_distance_matches_full_reference_including_swaps():
    words = [''.join(chars) for n in range(5) for chars in product('ab',repeat=n)]
    for a,b in product(words, repeat=2):
        assert bounded_distance(a,b) == reference_distance(a,b)
    for a,b in [('אבגדהו','אבגדוה'),('abcdef','acbdef'),('abcdef','bacdfe')]:
        assert bounded_distance(a,b) == reference_distance(a,b)


@pytest.mark.parametrize('field,kind', FIELDS.items())
def test_consent_stops_raw_values_before_any_resolution_and_preserves_final_quiz(field, kind, monkeypatch):
    original = CORPUS['rooms'][0]
    hidden = {**original, 'rows': [{**r, 'hide':[field] if i<3 else []} for i,r in enumerate(original['rows'])]}
    changed = {**hidden, 'rows': [{**r, 'values':{**r['values'],field:'PRIVATE_RESOLUTION_SENTINEL'} if i<3 else r['values']}
                                for i,r in enumerate(hidden['rows'])]}
    seen = []
    resolve = KB.resolve
    def watched(kind, value):
        seen.append((kind,value))
        return resolve(kind,value)
    monkeypatch.setattr(KB,'resolve',watched)
    before, after = generate(hidden), generate(changed)
    assert before.questions == after.questions
    assert before.selected == after.selected
    assert not any(value=='PRIVATE_RESOLUTION_SENTINEL' for _,value in seen)
    assert 'PRIVATE_RESOLUTION_SENTINEL' not in repr(after)


@pytest.mark.parametrize('room', CORPUS['rooms'][:3], ids=lambda r:r['name'])
@pytest.mark.parametrize('language', ['en','he'])
@pytest.mark.parametrize('seed', [1,11,37])
def test_imperfect_rooms_improve_final_quiz_not_just_candidates(room,language,seed):
    trace = generate(room,language,seed)
    assert len(trace.questions) == 20
    assert sum(bool(c.knowledge_version and dict(c.metadata).get('kind')!='direct') for c in trace.selected) >= 15
    assert not any(q.source_rule_id=='unique_value' for q in trace.questions)
    assert {f for c in trace.selected if c.knowledge_version for f in c.source_field_keys} >= {
        'favorite_movie','favorite_artist','favorite_song','hobby','favorite_food','city'}
    for q in trace.questions:
        assert q.explanation or not q.knowledge_version
        assert sum(o.option_id==q.correct_option_id for o in q.options) == 1
        assert not any(word in q.text+q.explanation for word in ('FUZZY','CONFIDENCE','NORMALIZED'))
    assert trace.questions == generate(room,language,seed).questions


def test_unknown_room_stays_short_without_repetitive_lookup_padding():
    trace = generate(CORPUS['rooms'][-1])
    assert len(trace.questions)==1 and trace.questions[0].total_questions==1
    assert trace.questions[0].source_rule_id=='unique_value'


def test_recovered_spellings_do_not_become_false_separate_raw_favorites():
    originals=CORPUS['rooms'][0]['rows'][:6]
    values=('Conjuring','The Conjruing','The Conjuring','Saw','המסור','Saw')
    room={'rows':[{**row,'values':{'favorite_movie':value},'hide':[]} for row,value in zip(originals,values)]}
    trace=generate(room)
    assert trace.questions
    assert not any(c.source_rule_id in ('unique_value','value_count','most_common_value','group_comparison')
                   for c in trace.valid)


def test_no_runtime_network_and_generation_performance(monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError('network is forbidden during question generation')
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    times=[]
    for seed in range(5):
        start=perf_counter(); t=generate(CORPUS['rooms'][2], seed=seed)
        times.append(perf_counter()-start)
        assert len(t.questions)==20
    assert median(times)<.2


def test_partial_and_fuzzy_are_deterministic_under_entity_order():
    entities=tuple(KB.in_kind('artists')[:100])+(KB.resolve_artist('Omer Adam').entity,)
    forward=KnowledgeBase(entities, KB.categories.values(),'test')
    backward=KnowledgeBase(reversed(entities), KB.categories.values(),'test')
    for value in ('Omer Adma','Omer Adam','unknown artist'):
        assert forward.resolve_artist(value)==backward.resolve_artist(value)


def test_loaded_knowledge_memory_stays_within_free_hosting_budget():
    gc.collect(); tracemalloc.start()
    try:
        knowledge = load_knowledge()
        gc.collect()
        retained, _ = tracemalloc.get_traced_memory()
        assert knowledge.resolve_artist('Omer Adma').entity is not None
        assert retained < 80_000_000  # Hard review limit; actual target/report is <60 MB.
    finally:
        tracemalloc.stop()
