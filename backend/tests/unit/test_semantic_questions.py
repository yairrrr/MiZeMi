"""Independent truth fixtures, privacy boundaries, multi-hop proofs and replay."""
from random import Random
import ast
from pathlib import Path
import re
import socket
import subprocess
import sys
from time import perf_counter
import tracemalloc

import pytest

from app.domain.questions import QuestionGenerator, QuestionValidator
from app.domain.questions.semantic import enrich
from app.domain.questions.semantic_rules import semantic_rules, separated_extreme
from app.infrastructure.knowledge import get_knowledge, load_knowledge
from tests.fixtures.knowledge import ROWS, dataset, correct

RULES={r.rule_id:r for r in semantic_rules(get_knowledge())}


def candidates(rule_id,ds):
    return RULES[rule_id].generate(ds,Random(5))


CASES=[
    ('semantic_count',ROWS,'1','1'),
    ('semantic_subset_count',[{'favorite_movie':m} for m in ('Saw','The Conjuring','Toy Story','Unlisted classroom movie 9f4d')],'1','1'),
    ('semantic_scoped_pair',[{'favorite_movie':m} for m in ('Saw','The Conjuring','Toy Story','Unlisted classroom movie 9f4d')],'Dana + Omer','דנה + עומר'),
    ('semantic_mode',ROWS,'Mizrahi','מזרחית'),
    ('semantic_rare',[{'favorite_music':m} for m in ['Mizrahi']*3+['Jazz']*2+['Rock']],'Rock','רוק'),
    ('semantic_diversity',ROWS,'Italian cuisine','המטבח האיטלקי'),
    ('semantic_different_pair',ROWS,'Dana + Omer','דנה + עומר'),
    ('semantic_intersection',ROWS,'Noa','נועה'),
    ('semantic_filtered_mode',ROWS,'Horror','אימה'),
    ('semantic_outlier',ROWS,'Omer','עומר'),
    ('music_artist_bridge',ROWS,'Omer Adam','עומר אדם'),
    ('locality_extreme',ROWS,'Dana','דנה'),
    ('locality_distance_pair',ROWS,'Noa + Amit','נועה + עמית'),
    ('locality_nearest_to',ROWS,'Omer','עומר'),
    ('locality_middle',ROWS,'Amit','עמית'),
    ('locality_distinct',[{'city':'תל אביב'},{'city':'Tel-Aviv'},{'city':'Haifa'}],'2','2'),
    ('semantic_nearby_pair',ROWS,'Omer + Noa','עומר + נועה'),
    ('district_activity_diversity',ROWS,'Central District','מחוז המרכז'),
]


@pytest.mark.parametrize('rule_id,rows,en,he',CASES,ids=[c[0] for c in CASES])
@pytest.mark.parametrize('language',['en','he'])
def test_every_semantic_family_has_a_manually_proven_answer(rule_id,rows,en,he,language):
    ds=dataset(rows,language)
    generated=candidates(rule_id,ds)
    assert generated
    assert generated==candidates(rule_id,ds)
    sample=generated[0]
    if rule_id=='semantic_intersection':
        # Toy Story and Finding Nemo share adventure; only Noa among those
        # two chose a sport (surfing). Additional genres must not change this proof.
        sample=next(q for q in generated if q.semantic_key==('semantic_intersection','movie.genre','movie.adventure','hobby.family','hobby.sport'))
    if rule_id=='music_artist_bridge':
        # This historical (production-disabled) rule may choose any supported
        # artist as the reference catalog grows. Prove every option's truth.
        for option in sample.options:
            artist=get_knowledge().resolve_artist(option.text).entity
            assert artist is not None
            assert ('music.mizrahi' in artist.category_ids)==(option.option_id==sample.correct_option_id)
    else:
        assert correct(sample)==(he if language=='he' else en)
    for q in generated:
        assert QuestionValidator().is_valid(q,ds)
        assert q.explanation and q.knowledge_version==get_knowledge().version
        assert len({o.option_id for o in q.options})==len(q.options)
        assert sum(o.option_id==q.correct_option_id for o in q.options)==1
        assert len({o.text.casefold() for o in q.options})==len(q.options)
        assert bool(re.search('[א-ת]',q.text))==(language=='he')
        assert not re.search(r'שדה|שדות|ערכים|ערך סמנטי|קטגוריה|מיפוי|קנוני|רשומה',q.text)
        assert dict(q.metadata)['reasoning_hops']>=2


@pytest.mark.parametrize('language',['en','he'])
def test_real_discoveries_and_explanations_not_merely_direct_lookups(language):
    ds=dataset(language=language)
    pair=next(q for q in candidates('semantic_different_pair',ds) if q.semantic_key[-1]=='movie.horror')
    assert correct(pair)==('דנה + עומר' if language=='he' else 'Dana + Omer')
    assert ('המסור' if language=='he' else 'Saw') in pair.explanation
    assert ('לזמן את הרוע' if language=='he' else 'The Conjuring') in pair.explanation
    grouped=next(q for q in candidates('semantic_count',ds) if q.semantic_key[-1]=='hobby.sport')
    assert correct(grouped)=='3'
    for term in (('ריצה','כדורגל','גלישת גלים') if language=='he' else ('Running','Association football','Surfing')):
        assert term in grouped.explanation
    food=next(q for q in candidates('semantic_diversity',ds) if q.source_field_keys==('favorite_food',))
    assert correct(food)==('המטבח האיטלקי' if language=='he' else 'Italian cuisine')
    assert '3' in food.explanation
    geographic=candidates('locality_distance_pair',ds)[0]
    assert ('רחובות' if language=='he' else 'Reẖovot') in geographic.explanation
    assert '9' in geographic.explanation
    assert ('קו אווירי' if language=='he' else 'by air') in geographic.explanation


def test_aliases_are_not_different_films():
    ds=dataset([{'favorite_movie':'Saw'},{'favorite_movie':'המסור'},{'favorite_movie':'Toy Story'}])
    assert not candidates('semantic_different_pair',ds)


def test_different_music_subgenres_share_electronic_parent():
    ds=dataset([{'favorite_music':g} for g in ('House','Techno','Trance','Mizrahi')])
    q=next(q for q in candidates('semantic_count',ds) if q.semantic_key[-1]=='music.electronic')
    assert correct(q)=='3'
    assert all(word in q.explanation for word in ('House','Techno','Trance'))


def test_counts_people_once_with_multilabel_movies():
    ds=dataset([{'favorite_movie':m} for m in ('Saw','The Conjuring','The Conjuring','Toy Story')])
    q=next(q for q in candidates('semantic_count',ds) if q.semantic_key[-1]=='movie.horror')
    assert correct(q)=='3'


def test_mode_uses_people_but_diversity_uses_distinct_works():
    ds=dataset([{'hobby':h} for h in ('Football','Football','Football','Guitar','Photography')])
    mode=candidates('semantic_mode',ds)[0]
    diversity=candidates('semantic_diversity',ds)[0]
    assert correct(mode)=='Sport'
    assert correct(diversity)=='Arts and crafts'


@pytest.mark.parametrize('rule_id',RULES)
def test_private_inputs_and_unknowns_never_prove_group_membership(rule_id):
    original=dataset()
    hidden=dataset(hidden=('favorite_movie',))
    omitted=dataset([{k:v for k,v in zip(('city','favorite_food','hobby','favorite_music','favorite_movie','age'),row) if k!='favorite_movie'} for row in ROWS])
    assert candidates(rule_id,hidden)==candidates(rule_id,omitted)
    for q in candidates(rule_id,hidden):
        assert 'favorite_movie' not in q.source_field_keys
        assert 'Saw' not in q.explanation and 'The Conjuring' not in q.explanation
    assert not enrich(hidden,get_knowledge()).rows['favorite_movie']
    assert enrich(original,get_knowledge()) is enrich(original,get_knowledge())


@pytest.mark.parametrize('rule_id',RULES)
def test_no_semantic_questions_from_unknowns_or_private_profiles(rule_id):
    rows=[{'city':'secret town','favorite_movie':'obscure movie','hobby':'new hobby','favorite_food':'new dish','favorite_music':'Other'}]*3
    assert not candidates(rule_id,dataset(rows))
    assert not candidates(rule_id,dataset(hidden=('city','favorite_food','hobby','favorite_movie','favorite_music')))


def test_missing_one_answer_never_becomes_a_negative_classification():
    rows=[{'favorite_movie':'Saw'},{'favorite_movie':'The Conjuring'},{'favorite_movie':'Unlisted classroom movie 9f4d'}]
    for rule in RULES:
        assert not candidates(rule,dataset(rows))
    # Existing direct rules still work with the exact original answer.
    qs=QuestionGenerator().generate(dataset(rows),question_count=10,time_limit_seconds=20,seed=1)
    assert qs and any('Unlisted classroom movie 9f4d' in q.text for q in qs)


def test_extra_private_or_unrecognized_fields_cannot_enrich():
    rows=[dict(zip(('city','favorite_food','hobby','favorite_music','favorite_movie','age'),r)) for r in ROWS]
    for row in rows: row.update(personal_fact='PRIVATE_SAW',nationality='private')
    original=dataset()
    with_private=dataset(rows,hidden=('personal_fact','nationality'))
    for rule in RULES:
        assert candidates(rule,original)==candidates(rule,with_private)
    view=enrich(with_private,get_knowledge())
    assert 'personal_fact' not in view.rows and 'nationality' not in view.rows


def test_positive_cross_domain_clues_are_individually_ambiguous():
    ds=dataset();v=enrich(ds,get_knowledge())
    for q in candidates('semantic_intersection',ds):
        _,a,ca,b,cb=q.semantic_key
        ga,gb=set(v.groups(a)[ca]),set(v.groups(b)[cb])
        assert len(ga)>=2 and len(gb)>=2 and len(ga&gb)==1
        assert correct(q)==v.name(next(iter(ga&gb)))


def test_music_artist_question_proves_artist_classification_without_inventing_listening():
    kb=get_knowledge(); ds=dataset()
    for seed in range(15):
        q=RULES['music_artist_bridge'].generate(ds,Random(seed))[0]
        categories=[kb.resolve_artist(o.text).entity.category_ids for o in q.options]
        assert sum('music.mizrahi' in cats for cats in categories)==1
        assert 'music.mizrahi' in kb.resolve_artist(correct(q)).entity.category_ids
        assert not any(word in q.text.lower() for word in ('probably','playlist','definitely listens','personality'))
        assert not any(name in q.text for name in ('Dana','Omer','Noa','Amit','Lior'))


def test_ties_duplicate_places_and_geographic_precision():
    assert separated_extreme({'a':5.,'b':5.}) is None
    assert separated_extreme({'a':5.,'b':5.5},smallest=True) is None
    assert separated_extreme({'a':5.,'b':6.1},smallest=True)=='a'
    assert not candidates('locality_extreme',dataset([{'city':'Haifa'}]*3))
    assert not candidates('locality_middle',dataset([{'city':'Haifa'},{'city':'Tel Aviv'},{'city':'Haifa'}]))
    assert not candidates('locality_middle',dataset(ROWS[:4]))
    assert not candidates('semantic_mode',dataset([{'favorite_music':m} for m in ('Mizrahi','Jazz','Pop')]))
    assert not candidates('music_artist_bridge',dataset([{'favorite_music':m} for m in ('Mizrahi','Jazz','Pop')]))


@pytest.mark.parametrize('language',['en','he'])
def test_complete_generation_replay_and_semantic_selection(language):
    generator=QuestionGenerator(knowledge=get_knowledge())
    first=generator.generate(dataset(language=language),question_count=20,time_limit_seconds=20,seed=77)
    second=generator.generate(dataset(language=language),question_count=20,time_limit_seconds=20,seed=77)
    assert first==second and len(first)==20
    semantic=[q for q in first if q.knowledge_version]
    assert len(semantic)>=10
    assert {'group_filtered_mode','region_hobby_diversity'} & set(q.source_rule_id for q in first)
    assert not {'music_artist_bridge','similar_to_player','profile_fingerprint'} & set(q.source_rule_id for q in first)
    assert all(q.explanation for q in semantic)
    assert all(q.language==language for q in first)


def test_determinism_across_python_hash_seeds():
    code="""from tests.fixtures.knowledge import dataset
from app.infrastructure.knowledge import get_knowledge
from app.domain.questions import QuestionGenerator
from dataclasses import asdict
import json
qs=QuestionGenerator(knowledge=get_knowledge()).generate(dataset(),question_count=20,time_limit_seconds=20,seed=77)
print(json.dumps([asdict(q) for q in qs],default=lambda x:x.value,sort_keys=True))"""
    import os
    root=Path(__file__).resolve().parents[3]
    outputs=[]
    for seed in ('1','444','random'):
        result=subprocess.run([sys.executable,'-c',code],cwd=root,env={**os.environ,'PYTHONHASHSEED':seed,'PYTHONPATH':str(root/'backend')},capture_output=True,text=True,check=True)
        outputs.append(result.stdout)
    assert len(set(outputs))==1


def test_generation_never_reads_network_or_database_or_asset_files(monkeypatch):
    kb=get_knowledge(); ds=dataset()
    def forbidden(*a,**k): raise AssertionError('generation must be offline and in memory')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(Path,'read_text',forbidden)
    monkeypatch.setattr(Path,'read_bytes',forbidden)
    from sqlalchemy.orm import Session
    monkeypatch.setattr(Session,'execute',forbidden)
    assert len(QuestionGenerator(knowledge=kb).generate(ds,question_count=20,time_limit_seconds=20,seed=2))==20


def test_load_memory_and_classroom_generation_have_wide_sanity_bounds():
    tracemalloc.start(); start=perf_counter(); kb=load_knowledge()
    retained,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    assert perf_counter()-start<15  # Instrumented loading; uninstrumented SLA is measured separately.
    assert peak<80_000_000
    assert retained<60_000_000
    rows=[ROWS[i%5] for i in range(30)]
    start=perf_counter()
    for seed in range(3):
        qs=QuestionGenerator(knowledge=kb).generate(dataset(rows),question_count=20,time_limit_seconds=20,seed=seed)
        assert len(qs)==20
    assert perf_counter()-start<5


def test_all_hebrew_rule_templates_avoid_implementation_vocabulary():
    path=Path(__file__).resolve().parents[2]/'app/domain/questions'
    for file in path.glob('*rules.py'):
        for node in ast.walk(ast.parse(file.read_text())):
            if isinstance(node,ast.Constant) and isinstance(node.value,str) and '?' in node.value and re.search('[א-ת]',node.value):
                assert not re.search('שדות|שדה|ערכים|ערך סמנטי|מיפוי|קנוני|רשומה',node.value),node.value


def test_partial_knowledge_scopes_comparisons_without_treating_unknown_as_false():
    rows=[{'favorite_movie':m} for m in ('Saw','The Conjuring','Toy Story','Unlisted classroom movie 9f4d')]
    ds=dataset(rows)
    count=next(q for q in candidates('semantic_subset_count',ds) if q.semantic_key[2]=='movie.horror')
    assert correct(count)=='2'
    assert all(name in count.text for name in ('Dana','Omer','Noa'))
    assert 'Amit' not in count.text
    assert count.involved_player_ids==('p0','p1','p2')
    pair=candidates('semantic_scoped_pair',ds)[0]
    assert 'Among the pairs below' in pair.text
    assert correct(pair)=='Dana + Omer'
    assert all('Amit' not in option.text for option in pair.options)
    assert not candidates('semantic_mode',ds)


def test_partial_cross_domain_comparison_explicitly_names_its_scope():
    rows=[dict(zip(('city','favorite_food','hobby','favorite_music','favorite_movie','age'),r)) for r in ROWS]
    rows[4]['favorite_movie']='Unlisted classroom movie 9f4d'
    qs=[q for q in candidates('semantic_intersection',dataset(rows)) if 'favorite_movie' in q.source_field_keys]
    assert qs
    for q in qs:
        assert q.text.startswith('Among Dana, Omer, Noa, Amit:')
        assert 'p4' not in q.involved_player_ids
        assert 'Lior' not in ' '.join(o.text for o in q.options)
