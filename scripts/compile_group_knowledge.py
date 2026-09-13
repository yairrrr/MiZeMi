#!/usr/bin/env python3
"""Offline compiler for the expanded, reviewed group-intelligence bundle.

Uses compact public-fact caches from expand_knowledge.py plus explicit curation.
No network code. Existing reviewed seed records retain their IDs and revisions.
"""
from __future__ import annotations
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.infrastructure.knowledge import BUNDLE_DIR, load_knowledge
from app.domain.questions.knowledge import KINDS, normalize_name
from build_knowledge_base import clean, dump, unpoint

CURATION=ROOT/'scripts/knowledge/curation.json'
GROUP=ROOT/'scripts/knowledge/group-curation.json'


def closure(q, records, depth=3, blocked_edges=()):
    seen,frontier={q},{q}
    for _ in range(depth):
        frontier={p for item in frontier for p in records.get(item,{}).get('P279',[]) if (item,p) not in blocked_edges}-seen
        seen.update(frontier)
    return seen


def reference_ids(values):
    # Wikidata can return "some value" blank nodes. These are unknown facts,
    # not entity identifiers, and must never enter runtime metadata.
    return sorted({q for q in values if isinstance(q,str) and re.fullmatch(r'Q[1-9]\d{0,11}',q)})[:12]


def activity_facts(q,record,records,config):
    terms=closure(q,records)
    for parent in record.get('P31',[]): terms.update(closure(parent,records,2))
    facts={cat for cat,roots in config['activity_roots'].items() if terms.intersection(roots)}
    # Preserve physical exercise as part of the game's broad sport family.
    if 'hobby.fitness' in facts: facts.add('hobby.sport')
    if 'hobby.music' in facts: facts.add('hobby.creative')
    if facts.intersection(('hobby.sport','hobby.fitness','hobby.water')) or terms.intersection(('Q11639','Q41425','Q201022','Q1085001','Q169737','Q189825')):
        facts.add('activity.physical')
    elif facts.intersection(('hobby.digital','hobby.table_games','hobby.music','hobby.learning','hobby.collecting','hobby.wellbeing','hobby.creative')):
        facts.add('activity.nonphysical')
    settings={setting for setting,roots in config['settings'].items() if q in roots}
    if not settings: settings={setting for setting,roots in config['settings'].items() if terms.intersection(roots)}
    if len(settings)==1: facts.add('setting.'+next(iter(settings)))
    elif settings: facts.add('setting.flexible')
    return facts


def compile_bundle(cache, output=BUNDLE_DIR, *, base=BUNDLE_DIR, retrieved=None, version=None):
    retrieved=retrieved or date.today().isoformat()
    version=version or retrieved+'.1'
    old=json.loads(CURATION.read_text()); config=json.loads(GROUP.read_text())
    date.fromisoformat(retrieved)
    records={}; selected={kind:[] for kind in KINDS}; selection_dates=[]
    paths=sorted(cache.glob('*.json'))
    for path in paths:
        if path.name.endswith('-selection.json'):
            kind=path.name.split('-')[0]
            selection=json.loads(path.read_text())
            selection_date=selection.get('retrieved',retrieved)
            if date.fromisoformat(selection_date)>date.fromisoformat(retrieved):
                raise ValueError('--retrieved must not predate source retrieval')
            selection_dates.append(selection_date)
            if kind in selected:selected[kind].extend(selection['ids'])
        elif path.name=='ancestors.json' or re.fullmatch(r'(movies|songs|artists|foods|hobbies)-(?:he-)?\d{5}\.json',path.name):
            records.update(json.loads(path.read_text()))
    if not records: raise ValueError('No factual research cache; fetch and review first')
    categories={r[0]:r for r in json.loads((base/'categories.json').read_text())}
    categories.update({r[0]:r for r in config['categories']})
    roots={key:set(ids) for key,ids in old['roots'].items()}
    roots['movie.animation']={'Q202866'}
    for key,row in categories.items():
        if row[1]=='music.genre': roots.setdefault(key,set())
    files={}; excluded={}; metadata_counts={}
    for kind in KINDS:
        base_path=base/(kind+'.json')
        seed_rows=json.loads(base_path.read_text()) if base_path.exists() else []
        seed_ids=set(old['selection'].get(kind,[]))
        # Only curated seed records are carried forward; an updated fetch may
        # remove prior bulk records rather than silently retaining stale facts.
        keep={r[0]:r for r in seed_rows if r[0] in seed_ids or r[0].startswith('local_') or kind=='localities'}
        excluded[kind]=0
        for q in dict.fromkeys(selected[kind]):
            r=records.get(q,{})
            types=set(r.get('P31',[]))
            if types.intersection(('Q4167410','Q13406463')) or (kind=='hobbies' and 'Q5' in types):
                excluded[kind]+=1; continue
            # Exclude explicit adult-film types, never identities or cultures.
            if (set(r.get('P136',[]))|types).intersection(('Q185529','Q138020407')):
                excluded[kind]+=1; continue
            facts=set()
            if kind in ('movies','artists','songs'):
                blocked_edges={tuple(edge) for edge in config.get('excluded_genre_parent_edges',[])}
                terms=set().union(*(closure(g,records,2,blocked_edges) for g in r.get('P136',[]))) if r.get('P136') else set()
                dim='movie.genre' if kind=='movies' else 'music.genre'
                if kind=='movies' and 'Q202866' in types: terms.add('Q202866')
                facts={key for key,ids in roots.items() if categories[key][1]==dim and terms&ids}
            elif kind=='foods':
                terms=closure(q,records)
                for parent in r.get('P31',[]): terms.update(closure(parent,records,2))
                for term in tuple(terms):
                    for cuisine in records.get(term,{}).get('P2012',[]): terms.update(closure(cuisine,records,2))
                facts={key for key,ids in roots.items() if categories[key][1].startswith('food.') and terms&ids}
                facts.update(old['extra_food_facts'].get(q,[]))
            elif kind=='hobbies': facts=activity_facts(q,r,records,config)
            if not facts:
                excluded[kind]+=1;continue
            # Keep a real native title when an English title is unavailable;
            # never fabricate a translation or expose an internal ID as a name.
            en=clean(r.get('titleEn') or r.get('en') or r.get('titleHe') or r.get('he',''))
            he=clean(config['hebrew_labels'].get(q) or old['hebrew_labels'].get(q) or r.get('titleHe') or r.get('he',''))
            if not en or len(en)>200 or len(he)>200:
                excluded[kind]+=1;continue
            aliases=set(old['aliases'].get(q,[]))|set(config['extra_aliases'].get(q,[]))
            for text in (en,he):
                if text:
                    aliases.add(text)
                    # A qualified activity can describe a narrower discipline.
                    # Do not turn "running (sport)" into an alias that masks
                    # the separately represented general running activity.
                    if kind!='hobbies': aliases.add(re.sub(r' \([^()]+\)$','',text))
            years=sorted({int(m[1]) for t in r.get('P577',[]) if (m:=re.match(r'^\+?(\d{4})-',t)) and 1800<=int(m[1])<=int(retrieved[:4])})
            year=years[0] if years and kind in ('movies','songs') else None
            if year and kind in ('movies','songs'):
                for text in (en,he):
                    if text:aliases.add(re.sub(r' \([^()]+\)$','',text)+' '+str(year))
            performers=reference_ids(r.get('P175',[])) if kind=='songs' else []
            if kind=='songs':
                for artist in performers:
                    a=records.get(artist,{})
                    for title,artist_name in ((en,a.get('en','')),(he,a.get('he',''))):
                        if title and artist_name:
                            short=re.sub(r' \([^()]+\)$','',title)
                            aliases.update((short+' - '+artist_name,artist_name+' - '+short))
            aliases=sorted({clean(a) for a in aliases if clean(a) not in ('',en,he) and len(clean(a))<=200})[:30]
            details=[year,reference_ids(r.get('P495',[])),reference_ids(r.get('P179',[])),performers,'']
            row=[q,en,he,aliases,sorted(facts),None,0,details]
            if q in keep:
                seed=keep[q]
                # Retain the manually reviewed seed spellings/facts and source
                # revision. Add only positive fetched facts and bounded aliases.
                row[1:3]=seed[1:3]
                row[3]=sorted((set(aliases)|set(seed[3]))-{row[1],row[2]})[:30]
                if kind in ('foods','hobbies'):
                    row[4]=sorted(set(row[4])|set(seed[4]))
                row[6]=seed[6]
            keep[q]=row
        if kind=='hobbies':
            for q,row in keep.items():
                row[4]=sorted(set(row[4])|activity_facts(q,records.get(q,{}),records,config))
                previous_hebrew=row[2]
                row[2]=config['hebrew_labels'].get(q,row[2])
                if previous_hebrew and previous_hebrew!=row[2]: row[3].append(previous_hebrew)
                row[3]=sorted((set(row[3])|set(config['extra_aliases'].get(q,[])))-{row[1],row[2]})[:30]
        if kind=='localities':
            geo_path=cache/'geonames/localities.json'
            if geo_path.exists():
                refreshed={}
                district_codes=dict(zip(('01','02','03','04','05','06'),('place.south','place.central','place.north','place.haifa','place.tel_aviv','place.jerusalem')))
                for gid,en,ascii_name,aliases,place_type,lat,lon,district in json.loads(geo_path.read_text()):
                    if not (28.5<=lat<=34.5 and 33.5<=lon<=36.5): continue
                    q='G'+gid; seed=keep.get(q)
                    he_names=[clean(a) for a in aliases if any('א'<=ch<='ת' for ch in a)]
                    pointed=[a for a in he_names if unpoint(a)!=a]
                    he=old['place_hebrew'].get(gid,unpoint((pointed or he_names or [''])[0]))
                    if seed: en,he=seed[1:3]
                    names={clean(ascii_name),*old['place_aliases'].get(gid,[])}
                    if seed:names.update(seed[3])
                    names=sorted(names-{'',en,he})
                    facts=[district_codes[district]] if district in district_codes else []
                    refreshed[q]=[q,en,he,names,facts,[round(lat,5),round(lon,5)],0,[None,[],[],[],place_type]]
                keep=refreshed
            for row in keep.values():
                districts=[f for f in row[4] if f.startswith('place.')]
                row[4]=sorted(set(districts)|{config['region_from_district'][d] for d in districts if d in config['region_from_district']})
        for q,allowed in config.get('fact_overrides',{}).items():
            if q in keep: keep[q][4]=sorted(set(allowed))
        files[kind+'.json']=sorted(keep.values(),key=lambda r:r[0])
        metadata_counts[kind]=sum(len(r)>7 and r[7][0] is not None for r in keep.values())
    files['categories.json']=list(categories.values())
    output.mkdir(parents=True,exist_ok=True)
    for name,rows in files.items(): dump(output/name,rows)
    previous=json.loads((base/'manifest.json').read_text())
    sources=previous['sources'][:2]
    # Keep the seed/GeoNames retrieval dates truthful; new query projections
    # have their own independently dated source entry and transformation record.
    if (cache/'geonames/localities.json').exists():
        geo_source=cache/'geonames/source.json'
        geo_date=json.loads(geo_source.read_text())['retrieved'] if geo_source.exists() else retrieved
        sources[1]={**sources[1],'retrieved':geo_date,
                    'fields':'GeoNames ID; populated-place feature code; names and reviewed aliases; latitude/longitude; administrative district code.',
                    'cache_sha256':hashlib.sha256((cache/'geonames/localities.json').read_bytes()).hexdigest()}
    sources.append({'name':'Wikidata bounded group-reference expansion','url':'https://query.wikidata.org/sparql','retrieved':retrieved,
        'retrieval_started':min(selection_dates,default=retrieved),
        'license':'CC0-1.0','license_url':'https://www.wikidata.org/wiki/Wikidata:Licensing',
        'fields':'Q IDs; English/Hebrew labels and sitelink names; P136, P31, P279, P2012, P495, P577, P179, P175.',
        'transformation':'Popularity-ranked finite selections, licensed factual projections only. At most two genre-parent edges, three activity/food-parent edges. No artist-to-song genre inheritance. Earliest supplied release year, explicit country/series/performer IDs. Reviewed seed records retain their original revisions; new query records use revision 0 with this dated query provenance. Ambiguous names fail closed.',
        'query_recipe':'scripts/expand_knowledge.py','curation_recipe':'scripts/knowledge/group-curation.json',
        'cache_sha256':hashlib.sha256(json.dumps(records,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()})
    manifest={**previous,'schema':2,'version':version,'sources':sources,
        'entity_columns':['id','en','he','aliases','categories','lat_lon','source_revision','optional_details'],
        'details_columns':['earliest_release_year','country_ids','series_ids','performer_ids','locality_type'],
        'group_curation_sha256':hashlib.sha256(GROUP.read_bytes()).hexdigest(),
        'files':{name:{'bytes':(output/name).stat().st_size,'sha256':hashlib.sha256((output/name).read_bytes()).hexdigest(),'rows':len(rows)} for name,rows in sorted(files.items())}}
    dump(output/'manifest.json',manifest)
    kb=load_knowledge(output)
    summary={'entities':{k:len(kb.in_kind(k)) for k in KINDS},'omitted':excluded,'release_year_records':metadata_counts}
    print(json.dumps(summary,indent=2))
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('cache',type=Path);p.add_argument('--output',type=Path,default=BUNDLE_DIR)
    p.add_argument('--base',type=Path,default=BUNDLE_DIR);p.add_argument('--retrieved');p.add_argument('--version')
    a=p.parse_args();compile_bundle(a.cache,a.output,base=a.base,retrieved=a.retrieved,version=a.version)

if __name__=='__main__':main()
