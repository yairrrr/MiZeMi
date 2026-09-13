"""Group discoveries, independently checked answers, wording and strict consent."""
from collections import Counter
from dataclasses import replace
from pathlib import Path
from random import Random
import socket
from time import perf_counter

import pytest
from app.domain.game import Player, PlayerProfile, ProfileField
from app.domain.questions import QuestionGenerator, QuestionValidator
from app.domain.questions.group_rules import group_rules, HOBBY_FAMILIES
from app.domain.questions.knowledge import KnownEntity, KnowledgeBase, Category, Match
from app.domain.questions.semantic import enrich
from app.infrastructure.knowledge import get_knowledge
from tests.fixtures.knowledge import dataset, correct


def questions(rule, rows, language='he', kb=None):
    kb=kb or get_knowledge(); ds=dataset(rows, language=language)
    return tuple(q for r in group_rules(kb) if r.rule_id==rule for q in r.generate(ds,Random(13))
                 if QuestionValidator().is_valid(q,ds))


def fixture_knowledge():
    """Controlled classifications and coordinates test algorithms, not sources."""
    cats=[Category(*r) for r in (
        ('movie.horror','movie.genre','Horror','אימה'),('movie.comedy','movie.genre','Comedy','קומדיה'),
        ('movie.drama','movie.genre','Drama','דרמה'),('hobby.sport','hobby.family','Sport','ספורט'),
        ('hobby.creative','hobby.family','Creative','יצירה'),('hobby.digital','hobby.family','Digital','דיגיטל'),
        ('food.italian','food.cuisine','Italian cuisine','המטבח האיטלקי'),('food.asian','food.cuisine','Asian cuisines','מטבחי אסיה'),
        ('region.central','place.region','Central Israel','המרכז'),('region.north','place.region','Northern Israel','הצפון'),
        ('region.south','place.region','Southern Israel','הדרום'),('setting.outdoor','hobby.setting','Outdoors','בחוץ'),
        ('setting.indoor','hobby.setting','Indoors','במקום סגור'),('activity.physical','hobby.physical','Physical activity','פעילות גופנית'),
        ('music.pop','music.genre','Pop','פופ'),('music.rock','music.genre','Rock','רוק'),
    )]
    definitions=[
        ('movies','M1','movie.horror',None),('movies','M2','movie.horror',None),('movies','M3','movie.comedy',None),
        ('movies','M4','movie.comedy',None),('movies','M5','movie.drama',None),
        ('hobbies','H1','hobby.sport,setting.outdoor,activity.physical',None),
        ('hobbies','H2','hobby.sport,setting.outdoor,activity.physical',None),
        ('hobbies','H3','hobby.creative,setting.indoor',None),('hobbies','H4','hobby.digital,setting.indoor',None),
        ('foods','F1','food.italian',None),('foods','F2','food.italian',None),('foods','F3','food.asian',None),
        ('music','Pop','music.pop',None),('music','Rock','music.rock',None),
        ('artists','A1','music.pop',None),('artists','A2','music.rock',None),
        ('songs','S1','music.pop',None),('songs','S2','music.rock',None),
        ('localities','C1','region.central',(32.0,34.8)),('localities','C2','region.central',(32.04,34.8)),
        ('localities','C3','region.north',(32.8,35.0)),('localities','C4','region.south',(29.6,34.9)),
    ]
    return KnowledgeBase([KnownEntity(str(i),kind,name,name,(),frozenset(facts.split(',')),coords)
                          for i,(kind,name,facts,coords) in enumerate(definitions)],cats,'test-exact-facts')


@pytest.mark.parametrize('language',['en','he'])
def test_actual_raw_choices_reveal_group_families_without_typing_them(language):
    rows=[
        {'favorite_movie':'המסור','favorite_food':'פיצה','hobby':'ריצה','city':'תל אביב','favorite_music':'Mizrahi'},
        {'favorite_movie':'לזמן את הרוע','favorite_food':'פסטה','hobby':'כדורגל','city':'רמת גן','favorite_music':'Pop'},
        {'favorite_movie':'שרק','favorite_food':'לזניה','hobby':'גלישה','city':'ראשון לציון','favorite_music':'Rock'},
        {'favorite_movie':'טיטניק (סרט, 1997)','favorite_food':'סושי','hobby':'גיימינג','city':'חיפה','favorite_music':'Mizrahi'},
        {'favorite_movie':'שרק 2','favorite_food':'פלאפל','hobby':'גינון','city':'באר שבע','favorite_music':'Trance'},
    ]
    qs=questions('group_count',rows,language)
    horror=next(q for q in qs if q.semantic_key[-1]=='movie.horror')
    assert correct(horror)=='2'
    assert 'המסור' in horror.explanation if language=='he' else 'Saw' in horror.explanation
    movie_mode=next(q for q in questions('group_mode',rows[:4],language) if q.source_field_keys==('favorite_movie',))
    assert correct(movie_mode)==('אימה' if language=='he' else 'Horror')
    sport=next(q for q in qs if q.semantic_key[-1]=='hobby.sport')
    assert correct(sport)=='3'
    cuisine=next(q for q in questions('group_mode',rows,language) if q.source_field_keys==('favorite_food',))
    assert correct(cuisine)==('המטבח האיטלקי' if language=='he' else 'Italian cuisine')
    region=questions('region_majority',rows,language)[0]
    assert correct(region)==('המרכז' if language=='he' else 'Central Israel')
    assert ('רוב' in region.text) if language=='he' else ('majority' in region.text)
    settings=next(q for q in questions('group_comparison_semantic',rows,language) if q.semantic_key[1]=='hobby.setting')
    assert correct(settings) in ('Outdoors','Indoors','בחוץ','בבית או בחלל סגור')
    unique_rows=[{**r,'favorite_movie':('המסור' if i==0 else 'שרק')} for i,r in enumerate(rows)]
    unique=next(q for q in questions('group_unique',unique_rows,language) if q.semantic_key[-1]=='movie.horror')
    assert correct(unique)==('דנה' if language=='he' else 'Dana')
    assert 'רק אחד' in unique.text if language=='he' else 'Only one' in unique.text


@pytest.mark.parametrize('language',['he','en'])
def test_actual_artist_and_song_choices_reveal_shared_genres(language):
    rows=[{'favorite_artist':artist,'favorite_song':song} for artist,song in (
        ('עומר אדם','Shake It Off - Taylor Swift'),('Taylor Swift','Blank Space'),('Metallica','Enter Sandman'))]
    qs=questions('group_count',rows,language)
    for dim in ('artist.genre','song.genre'):
        q=next(q for q in qs if q.semantic_key==('membership',dim,'music.pop'))
        assert correct(q)=='2'
        assert q.source_field_keys==(('favorite_artist' if dim=='artist.genre' else 'favorite_song'),)
    kb=get_knowledge()
    song=kb.resolve_song('Shake It Off - Taylor Swift').entity
    assert song.canonical_id=='Q17544624' and song.year==2014
    assert song.performer_ids==('Q26876',)
    assert 'music.classical' not in kb.resolve_artist('עדן בן זקן').entity.category_ids


def test_parent_and_child_memberships_do_not_repeat_the_same_discovery():
    from app.domain.questions.selector import QuestionSelector
    rows=[{'favorite_music':s} for s in ('Mizrahi','Trance','Trance')]
    pool=questions('group_count',rows)
    assert {'music.trance','music.electronic'} <= {q.semantic_key[-1] for q in pool}
    selected=QuestionSelector(group_first=True).select([(q,1.0) for q in pool],question_count=20)
    signatures=[dict(q.metadata)['membership_signature'] for q in selected]
    assert len(signatures)==len(set(signatures))
    assert sum(q.semantic_key[-1] in ('music.trance','music.electronic') for q in selected)==1


def test_broad_hobby_choices_do_not_compete_with_their_own_children():
    qs=questions('group_mode',[{'hobby':h} for h in ('פילאטיס','ריצה','כדורגל','ציור')])
    q=next(q for q in qs if q.source_field_keys==('hobby',))
    assert correct(q)=='ספורט'
    assert not {'כושר','פעילות במים','מוזיקה'} & {o.text for o in q.options}


def test_legacy_fallback_cannot_split_known_hebrew_english_aliases():
    from app.domain.questions.group_rules import SocialLegacyRule
    kb=get_knowledge()
    rows=[{'city':c,'favorite_movie':m} for c,m in
          (('Tel Aviv','Saw'),('תל אביב','המסור'),('Haifa','Toy Story'))]
    ds=dataset(rows)
    assert enrich(ds,kb).raw_alias_collisions==frozenset({'city','favorite_movie'})
    generator=QuestionGenerator(knowledge=kb)
    assert not [q for r in generator._rules if isinstance(r,SocialLegacyRule) for q in r.generate(ds,Random(1))]
    count=next(q for q in questions('group_count',rows) if q.semantic_key[-1]=='movie.horror')
    assert correct(count)=='2'


def test_plurality_never_claims_a_majority_and_ties_are_rejected():
    kb=fixture_knowledge()
    rows=[{'city':c} for c in ('C1','C2','C3','C4')]
    q=questions('region_majority',rows,kb=kb)[0]
    assert correct(q)=='המרכז' and 'רוב' not in q.text
    assert not questions('region_majority',[{'city':c} for c in ('C1','C2','C3','C3')],kb=kb)
    unique=questions('region_unique',[{'city':c} for c in ('C1','C2','C1','C3')],kb=kb)
    assert len(unique)==1 and correct(unique[0])=='עמית'
    assert not questions('region_unique',rows,kb=kb)  # Two singleton regions.


def test_counts_comparisons_diversity_and_different_choices_independently():
    kb=fixture_knowledge();rows=[{'hobby':h,'favorite_food':f} for h,f in zip(('H1','H2','H3','H3','H4'),('F1','F2','F1','F3','F3'))]
    q=next(q for q in questions('group_count',rows,kb=kb) if q.semantic_key[-1]=='hobby.sport')
    assert correct(q)=='2'
    assert not questions('group_mode',rows,kb=kb)[0].source_field_keys==('hobby',)  # sport and creative tie.
    cuisine=next(q for q in questions('group_mode',rows,kb=kb) if q.source_field_keys==('favorite_food',))
    assert correct(cuisine)=='המטבח האיטלקי'
    d=next(q for q in questions('group_diversity',rows,kb=kb) if q.source_field_keys==('hobby',))
    assert correct(d)=='3'
    pair=questions('group_different_pair',rows,kb=kb)[0]
    assert correct(pair)=='דנה + עומר'
    duplicate=[{'hobby':h} for h in ('H1','H1','H4')]
    assert not questions('group_different_pair',duplicate,kb=kb)
    for q in questions('group_comparison_semantic',rows,kb=kb):
        _,dim,a,b=q.semantic_key;v=enrich(dataset(rows),kb)
        groups=v.groups(dim)
        assert len(groups[a])!=len(groups[b])
        winner=a if len(groups[a])>len(groups[b]) else b
        assert correct(q)==kb.categories[winner].hebrew


def test_geographic_average_outlier_and_unique_pair_use_math():
    kb=fixture_knowledge(); rows=[{'city':c} for c in ('C1','C2','C3','C4')]
    ds=dataset(rows);view=enrich(ds,kb)
    means={p:sum(distance for pair,distance in view.distances.items() if p in pair)/3 for p in ds.player_ids}
    winner=max(means,key=means.get)
    q=questions('geographic_outlier',rows,kb=kb)[0]
    assert correct(q)==dataset(rows,'he').display_name_for(winner)=='עמית'
    assert 'בממוצע' in q.text
    closest=questions('locality_distance_pair',rows,kb=kb)[0]
    assert correct(closest)=='דנה + עומר'
    # Symmetric endpoints have equal average distances, never broken by ID.
    equal=[{'city':c} for c in ('C1','C2','C1','C2')]
    assert not questions('geographic_outlier',equal,kb=kb)
    assert not questions('locality_distance_pair',equal,kb=kb)


def test_meaningful_subgroup_analysis_and_positive_cross_domain_counts():
    kb=fixture_knowledge()
    rows=[{'favorite_movie':m,'hobby':h} for m,h in zip(('M1','M2','M1','M3','M4'),('H1','H2','H3','H1','H4'))]
    q=next(q for q in questions('group_filtered_mode',rows,kb=kb) if q.semantic_key[1]=='movie.genre')
    assert correct(q)=='ספורט'
    q=next(q for q in questions('group_intersection_count',rows,kb=kb) if q.semantic_key[2]=='movie.horror')
    assert correct(q)=='2'
    small=rows[:2]+[{'favorite_movie':'M3','hobby':'H3'}]
    assert not questions('group_filtered_mode',small,kb=kb)


def test_region_hobby_diversity_counts_families_and_rejects_ties():
    kb=fixture_knowledge()
    rows=[{'city':city,'hobby':hobby} for city,hobby in
          (('C1','H1'),('C2','H3'),('C3','H1'),('C3','H2'),('C4','H4'))]
    q=questions('region_hobby_diversity',rows,kb=kb)[0]
    assert correct(q)=='המרכז'  # Two families, versus one in each other region.
    assert 'ספורט' in q.explanation and 'יצירה' in q.explanation
    tied=[*rows[:3],{'city':'C3','hobby':'H3'},rows[4]]
    assert not questions('region_hobby_diversity',tied,kb=kb)
    incomplete=[*rows[:4],{'city':'C4'}]
    assert not questions('region_hobby_diversity',incomplete,kb=kb)


@pytest.mark.parametrize('field',['favorite_movie','favorite_food','hobby','city','favorite_music','favorite_artist','favorite_song'])
def test_withheld_values_cannot_affect_any_question_or_derived_fact(field):
    kb=fixture_knowledge()
    original=[{'favorite_movie':'M1','favorite_food':'F1','hobby':'H1','city':'C1','favorite_music':'Pop','favorite_artist':'A1','favorite_song':'S1'},
              {'favorite_movie':'M2','favorite_food':'F2','hobby':'H2','city':'C2','favorite_music':'Rock','favorite_artist':'A2','favorite_song':'S2'},
              {'favorite_movie':'M3','favorite_food':'F3','hobby':'H3','city':'C3','favorite_music':'Pop','favorite_artist':'A1','favorite_song':'S1'}]
    changed=[{**row,field:'SECRET_DIFFERENT_VALUE'} for row in original]
    hidden_a=dataset(original,hidden=(field,));hidden_b=dataset(changed,hidden=(field,))
    omitted=dataset([{k:v for k,v in r.items() if k!=field} for r in original])
    gen=QuestionGenerator(knowledge=kb)
    def generated(ds): return gen.generate(ds,question_count=20,time_limit_seconds=20,seed=41)
    assert generated(hidden_a)==generated(hidden_b)==generated(omitted)
    assert field not in {f for r in gen._rules for q in r.generate(hidden_a,Random(41)) for f in q.source_field_keys}
    # Every single participant's opt-out is also respected, not only whole-field hiding.
    def one_hidden(value):
        players=[]
        for i,row in enumerate(original):
            fields=tuple(ProfileField(k,value if i==0 and k==field else v,not(i==0 and k==field)) for k,v in row.items())
            players.append(Player(str(i),str(i),profile=PlayerProfile(str(i),fields)))
        from app.domain.questions.dataset import ProfileDataset
        return ProfileDataset(players)
    assert generated(one_hidden('M1'))==generated(one_hidden('SECRET_CHANGE'))


def test_song_genre_does_not_come_from_performers_or_private_artist():
    kb=fixture_knowledge()
    # Artist and song intentionally have different known genres.
    rows=[{'favorite_artist':'A1','favorite_song':'S2'}]*3+[{'favorite_artist':'A2','favorite_song':'S1'}]
    song=next(q for q in questions('group_mode',rows,kb=kb) if q.source_field_keys==('favorite_song',))
    artist=next(q for q in questions('group_mode',rows,kb=kb) if q.source_field_keys==('favorite_artist',))
    assert correct(song)=='רוק' and correct(artist)=='פופ'
    unknown=[{'favorite_artist':'A1','favorite_song':'unlisted song'}]*4
    assert not any('favorite_song' in q.source_field_keys for q in questions('group_mode',unknown,kb=kb))


def test_production_disables_trivia_and_prior_social_knowledge_puzzles():
    gen=QuestionGenerator(knowledge=get_knowledge())
    ids={r.rule_id for r in gen._rules}
    assert not ids & {'music_artist_bridge','similar_to_player','shared_reference','profile_fingerprint','attribute_chain',
                      'cross_person_similarity','shared_but_different','unique_connection','rarest_profile','commonality_count'}
    assert {'group_count','group_mode','geographic_outlier','region_majority','group_filtered_mode'} <= ids


def test_partial_resolution_is_named_and_never_treated_as_no():
    kb=fixture_knowledge(); rows=[{'favorite_movie':m} for m in ('M1','M2','M3','not known')]
    assert not questions('group_mode',rows,kb=kb)
    qs=questions('group_scoped_count',rows,kb=kb)
    assert qs and all('דנה, עומר, נועה' in q.text for q in qs)
    assert all('עמית' not in q.text and 'p3' not in q.involved_player_ids for q in qs)


def test_equivalent_count_and_unique_discovery_is_not_asked_twice():
    kb=fixture_knowledge(); rows=[{'favorite_movie':m,'hobby':h} for m,h in zip(('M1','M3','M4','M5'),('H1','H2','H3','H4'))]
    gen=QuestionGenerator(knowledge=kb)
    candidates=[q for rule in gen._rules for q in rule.generate(dataset(rows),Random(3))]
    scored=[(q,1.0) for q in candidates if QuestionValidator().is_valid(q,dataset(rows))]
    chosen=gen._selector.select(scored,question_count=20)
    signatures=[q.semantic_key for q in chosen if q.semantic_key and q.semantic_key[0]=='membership']
    assert len(signatures)==len(set(signatures))
    assert sum(q.source_rule_id=='unique_value' for q in chosen)<=2
    assert sum(dict(q.metadata).get('person_answer',False) for q in chosen)<=5
