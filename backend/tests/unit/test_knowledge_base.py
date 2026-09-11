"""Offline data contract, provenance, conservative aliases and corruption tests."""
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from pathlib import Path
import shutil
import socket

import pytest

from app.application.profile_rules import MUSIC_STYLES
from app.domain.questions.knowledge import Category, KnownEntity, KnowledgeBase, Match, distance_km, normalize_name
from app.infrastructure.knowledge import BUNDLE_DIR, KnowledgeDataError, get_knowledge, load_knowledge


@pytest.fixture(scope='module')
def kb():
    return get_knowledge()


@pytest.mark.parametrize('kind,text,qid,fact',[
    ('movies','המסור','Q486239','movie.horror'),('movies','Saw','Q486239','movie.horror'),
    ('movies','לזמן את הרוע','Q5540479','movie.horror'),('movies','The Conjuring','Q5540479','movie.horror'),
    ('artists','עומר אדם','Q2918713','music.mizrahi'),('artists','Omer Adam','Q2918713','music.pop'),
    ('foods','פיצה','Q177','food.italian'),('foods','Pizza','Q177','food.italian'),
    ('foods','Pizza','Q177','food.pastry'),
    ('foods','סושי','Q46383','food.japanese'),('foods','Sushi','Q46383','food.rice'),
    ('foods','פלאפל','Q188788','food.legume'),('foods','חומוס','Q241987','food.middle_eastern'),
    ('foods','ג׳חנון','Q1960279','food.pastry'),('foods','פסטה','Q178','food.pasta'),
    ('hobbies','ריצה','Q105674','hobby.sport'),('hobbies','כדורגל','Q2736','hobby.sport'),
    ('hobbies','גלישה','Q159992','hobby.water'),('hobbies','פילאטיס','Q272460','hobby.fitness'),
    ('hobbies','Gaming','Q7889','hobby.digital'),('hobbies','גיימינג','Q7889','hobby.digital'),
    ('hobbies','Photography','Q11633','hobby.creative'),('hobbies','גיטרה','Q6607','hobby.music'),
    ('hobbies','שחמט','Q718','hobby.table_games'),
    ('music','היפהופ','Q11401','music.hiphop'),('music','היפ־הופ','Q11401','music.hiphop'),
    ('music','hip hop','Q11401','music.hiphop'),('music','Hip-Hop / Rap','Q11401','music.hiphop'),
    ('music','מזרחית','Q2738544','music.mizrahi'),('music','ים תיכוני','Q108250543','music.mediterranean'),
    ('music','פופ ישראלי','local_israeli_pop','music.pop'),
    ('music','House','Q20502','music.electronic'),('music','Techno','Q170611','music.electronic'),
    ('music','טראנס','Q170435','music.trance'),('music','R&B','Q45981','music.rnb'),
    ('localities','תל אביב','G293397','place.tel_aviv'),('localities','תל אביב יפו','G293397','place.tel_aviv'),
    ('localities','ת״א','G293397','place.tel_aviv'),('localities','Tel-Aviv','G293397','place.tel_aviv'),
    ('localities','חיפה','G294801','place.haifa'),('localities','באר שבע','G295530','place.south'),
    ('localities','ראשון לציון','G293703','place.central'),('localities','רחובות','G293725','place.central'),
])
def test_researched_facts_and_bilingual_aliases(kb,kind,text,qid,fact):
    result=kb.resolve(kind,text)
    assert result.match in (Match.EXACT,Match.ALIAS)
    assert result.entity.canonical_id==qid
    assert fact in result.entity.category_ids


@pytest.mark.parametrize('style',[s for s in MUSIC_STYLES if s!='Other'])
def test_every_selectable_music_style_resolves(kb,style):
    assert kb.resolve_music_genre(style).entity is not None


@pytest.mark.parametrize('kind,text',[
    ('movies','some obscure unreleased movie'),('movies','Swa'),('movies','Covid-19'),
    ('movies','Saw IIiII'),('foods','בננה בלי מלח'),('localities','ציון'),
    ('localities','UNKNOWN PLACE'),('hobbies','definitely an athlete'),
    ('artists','Everyone who likes Mizrahi'),('music','Other'),('music','Polka not in this catalog'),
    ('foods','<script>alert(1)</script>'),('movies','x'*201),('badkind','Pizza'),
])
def test_unknown_is_not_guessed(kb,kind,text):
    assert kb.resolve(kind,text).match==Match.UNKNOWN
    assert kb.resolve(kind,text).entity is None


def test_confidence_and_name_collision_fail_closed(kb):
    assert kb.resolve_food('  PIZZA  ').match==Match.EXACT
    assert kb.resolve_israeli_locality('ת״א').match==Match.ALIAS
    assert kb.resolve_movie('Aladdin').match==Match.UNKNOWN
    original=kb.resolve_movie('Saw').entity
    another=replace(original,canonical_id='Q999',english='Other title',hebrew='',aliases=('Saw',))
    collision=KnowledgeBase([original,another],kb.categories.values(),'test')
    assert collision.resolve_movie('Saw').match==Match.UNKNOWN
    assert collision.resolve_movie('המסור').entity==original
    assert 'saw' in collision.ambiguous_names['movies']


def test_safe_normalization_preserves_distinctions():
    assert normalize_name('  תֵּל־אָבִיב  ')==normalize_name('תל אביב')
    assert normalize_name('ת״א')==normalize_name('ת"א')
    assert normalize_name('Hip–Hop')==normalize_name('HIP HOP')
    assert normalize_name('Saw II')!=normalize_name('Saw III')
    assert normalize_name('קריית אונו')!=normalize_name('קריית אתא')


def test_reference_facts_are_immutable(kb):
    entity=kb.resolve_movie('Saw').entity
    with pytest.raises(FrozenInstanceError): entity.canonical_id='oops'
    with pytest.raises(TypeError): kb.entities['movies','Q1']=entity
    with pytest.raises(TypeError): kb.categories['movie.horror']=None
    assert isinstance(entity.category_ids,frozenset)


def test_geography_math_and_no_pairwise_table(kb):
    a=kb.resolve_israeli_locality('Rehovot').entity
    b=kb.resolve_israeli_locality('Rishon LeZion').entity
    assert 8<distance_km(a,b)<10
    assert distance_km(a,b)==pytest.approx(distance_km(b,a))
    assert distance_km(a,a)==0
    assert a.coordinates==pytest.approx((31.89421,34.81199))
    with pytest.raises(ValueError): distance_km(kb.resolve_movie('Saw').entity,a)


def test_no_stereotypes_or_unsupported_diet_claims(kb):
    assert 'movie.thriller' not in kb.resolve_movie('Saw').entity.category_ids
    assert 'hobby.sport' not in kb.resolve_hobby('Chess').entity.category_ids
    assert 'hobby.social' not in kb.resolve_hobby('Travel').entity.category_ids
    assert not any(term in c for c in kb.categories for term in ('vegan','vegetarian','personality','religion','gender'))
    assert not hasattr(kb.resolve_artist('Omer Adam').entity,'listeners')


def test_bundle_coverage_provenance_and_schema(kb):
    minimum={'movies':450,'artists':270,'music':60,'foods':175,'hobbies':200,'localities':1200}
    for kind,n in minimum.items(): assert len(kb.in_kind(kind))>=n
    manifest=json.loads((BUNDLE_DIR/'manifest.json').read_text())
    assert {s['license'] for s in manifest['sources']}=={'CC0-1.0','CC-BY-4.0'}
    for name,meta in manifest['files'].items():
        raw=(BUNDLE_DIR/name).read_bytes()
        assert meta['bytes']==len(raw)
        assert meta['sha256']==hashlib.sha256(raw).hexdigest()
        assert meta['rows']==len(json.loads(raw))
    for entity in kb.entities.values():
        if entity.canonical_id.startswith('Q'): assert entity.source_revision>0
        assert len(entity.category_ids)<20
        assert all(c in kb.categories for c in entity.category_ids)
    assert sum(p.stat().st_size for p in BUNDLE_DIR.iterdir() if p.suffix=='.json')<750_000


def test_load_once_with_no_network(monkeypatch):
    def forbidden(*args,**kwargs): raise AssertionError('network forbidden')
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    assert get_knowledge() is get_knowledge()
    assert load_knowledge().resolve_movie('Saw').entity==get_knowledge().resolve_movie('Saw').entity


@pytest.fixture
def bundle(tmp_path):
    target=tmp_path/'knowledge'
    shutil.copytree(BUNDLE_DIR,target)
    return target


def write_checked(bundle,name,data):
    raw=json.dumps(data,ensure_ascii=False).encode()
    (bundle/name).write_bytes(raw)
    manifest=json.loads((bundle/'manifest.json').read_text())
    manifest['files'][name].update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    (bundle/'manifest.json').write_text(json.dumps(manifest))


@pytest.mark.parametrize('mutation',[
    'missing','hash','duplicate_json_key','invalid_json','oversized','symlink','nonfinite',
    'bad_category','wrong_dimension','duplicate_entity','nonstring_alias','too_many_aliases',
    'bad_coords','outside_coords','invalid_id','bool_revision','empty_domain','unknown_file',
])
def test_corrupt_build_inputs_fail_closed(bundle,mutation,tmp_path):
    name='movies.json';rows=json.loads((bundle/name).read_text())
    if mutation=='missing': (bundle/name).unlink()
    elif mutation=='hash': (bundle/name).write_text('[]')
    elif mutation=='duplicate_json_key': (bundle/'manifest.json').write_text('{"schema":1,"schema":1}')
    elif mutation=='invalid_json': (bundle/name).write_text('{bad')
    elif mutation=='oversized': (bundle/name).write_text(' '*4_000_001)
    elif mutation=='symlink':
        (bundle/name).unlink(); (bundle/name).symlink_to(BUNDLE_DIR/name)
    elif mutation=='unknown_file':
        m=json.loads((bundle/'manifest.json').read_text());m['files']['../escape.json']={};(bundle/'manifest.json').write_text(json.dumps(m))
    else:
        if mutation in ('bad_coords','outside_coords','nonfinite'):
            name='localities.json';rows=json.loads((bundle/name).read_text())
            rows[0][5]={'bad_coords':[1], 'outside_coords':[0,0], 'nonfinite':[float('nan'),35]}[mutation]
        elif mutation=='bad_category': rows[0][4]=['made.up']
        elif mutation=='wrong_dimension': rows[0][4]=['hobby.sport']
        elif mutation=='duplicate_entity': rows.append(rows[0])
        elif mutation=='nonstring_alias': rows[0][3]=[{}]
        elif mutation=='too_many_aliases': rows[0][3]=['x']*31
        elif mutation=='invalid_id': rows[0][0]='../../oops'
        elif mutation=='bool_revision': rows[0][6]=True
        elif mutation=='empty_domain': rows=[]
        write_checked(bundle,name,rows)
    with pytest.raises(KnowledgeDataError): load_knowledge(bundle)


@pytest.mark.parametrize('change',['boolean_schema','invalid_date','unapproved_license','unsafe_url'])
def test_invalid_provenance_is_rejected(bundle,change):
    path=bundle/'manifest.json';manifest=json.loads(path.read_text())
    if change=='boolean_schema': manifest['schema']=True
    if change=='invalid_date': manifest['sources'][0]['retrieved']='not-a-date'
    if change=='unapproved_license': manifest['sources'][0]['license']='unknown'
    if change=='unsafe_url': manifest['sources'][0]['url']='javascript:alert(1)'
    path.write_text(json.dumps(manifest))
    with pytest.raises(KnowledgeDataError): load_knowledge(bundle)
