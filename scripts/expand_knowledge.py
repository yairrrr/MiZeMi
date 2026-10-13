#!/usr/bin/env python3
"""Development-only, paced Wikidata discovery. Never imported by the app.

Explicit --fetch downloads bounded, compact factual projections into CACHE.
No article text, descriptions, lyrics, images or raw API responses are kept.
"""
from __future__ import annotations
import argparse
from datetime import date
import io
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ENDPOINT='https://query.wikidata.org/sparql'
UA='MiZeMiReferenceBuild/2.0 (offline classroom game; https://github.com/yairrrr/MiZeMi)'
PREFIX='''PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <http://schema.org/>
'''
SELECTIONS={
 'movies':('''?item wdt:P31 wd:Q11424; wdt:P136 ?g; wikibase:sitelinks ?n. FILTER(?n>=8)''',10000),
 'songs':('''VALUES ?type {wd:Q7366 wd:Q134556} ?item wdt:P31 ?type; wdt:P136 ?g; wikibase:sitelinks ?n. FILTER(?n>=4)''',9000),
 'artists':('''{ VALUES ?job {wd:Q177220 wd:Q639669 wd:Q2252262 wd:Q36834 wd:Q488205 wd:Q753110 wd:Q1278335} ?item wdt:P106 ?job. } UNION { ?item wdt:P31/wdt:P279* wd:Q215380. } ?item wdt:P136 ?g; wikibase:sitelinks ?n. FILTER(?n>=8)''',6000),
 'foods':('''{?item wdt:P31/wdt:P279* wd:Q746549.} UNION {?item wdt:P279+ wd:Q746549.} ?item wikibase:sitelinks ?n. FILTER(?n>=1)''',4500),
 'hobbies':(' '.join(('{'+ ' UNION '.join('{?item wdt:P31/wdt:P279* wd:'+q+'.} UNION {?item wdt:P279+ wd:'+q+'.}' for q in ('Q31629','Q2755547','Q61065','Q219067','Q34379','Q131436','Q38695','Q720398'))+'}', '?item wikibase:sitelinks ?n. FILTER(?n>=2)')),2500),
}
# A focused Israeli supplement: songs from Israel, sung in Hebrew or performed
# by Israeli artists, plus Israeli musicians/bands and those songs' performers.
# Origin is selection only; genres still come from each item's own P136.
_SONG_TYPES='VALUES ?type {wd:Q7366 wd:Q134556 wd:Q105543609 wd:Q2188189} '
_ISRAELI_SONG=('{?item wdt:P495 wd:Q801} UNION {?item wdt:P407 wd:Q9288} UNION '
               '{?item wdt:P175 ?p. ?p wdt:P27 wd:Q801} UNION {?item wdt:P175 ?p. ?p wdt:P495 wd:Q801}')
ISRAELI_SELECTIONS={
 'songs':(_SONG_TYPES+'?item wdt:P31 ?type. '+_ISRAELI_SONG+' ?item wikibase:sitelinks ?n.',5000),
 'artists':('''{?item wdt:P27 wd:Q801; wdt:P31 wd:Q5; wdt:P106 ?job.
VALUES ?job {wd:Q177220 wd:Q639669 wd:Q2252262 wd:Q36834 wd:Q488205 wd:Q753110 wd:Q1278335 wd:Q855091 wd:Q386854}}
UNION {?item wdt:P495 wd:Q801; wdt:P31/wdt:P279* wd:Q215380.}
UNION {'''+_SONG_TYPES+'?song wdt:P31 ?type; wdt:P175 ?item. ?song wdt:P407 wd:Q9288.}'
 ' ?item wikibase:sitelinks ?n.',6000),
}

def query(text, attempt=0):
    url=ENDPOINT+'?'+urllib.parse.urlencode({'query':PREFIX+text,'format':'json'})
    request=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/sparql-results+json'})
    try:
        with urllib.request.urlopen(request,timeout=60) as r:
            raw=r.read(25_000_001)
        if len(raw)>25_000_000: raise ValueError('Research response exceeds budget')
        result=json.loads(raw)
        return [{k:v['value'] for k,v in row.items()} for row in result['results']['bindings']]
    except TimeoutError:
        if attempt < 2:
            time.sleep(5 * (attempt + 1))
            return query(text, attempt + 1)
        raise
    except urllib.error.HTTPError as e:
        if e.code in (502,503,504) and attempt < 2 and not e.headers.get('Retry-After'):
            time.sleep(5 * (attempt + 1))
            return query(text, attempt + 1)
        raise RuntimeError(f'Public source returned {e.code}; stop and resume later. Retry-After: {e.headers.get("Retry-After","unspecified")}') from None

def write(path,value):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n')
    temporary.replace(path)


def fetch_places(cache, retrieved):
    """CC BY 4.0 populated-place projection; no full dump enters the repository."""
    target=cache/'geonames/localities.json'
    if target.exists(): return
    request=urllib.request.Request('https://download.geonames.org/export/dump/IL.zip', headers={'User-Agent':UA})
    with urllib.request.urlopen(request,timeout=60) as response:
        raw=response.read(5_000_001)
    if len(raw)>5_000_000: raise ValueError('Geographic download exceeds budget')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if archive.getinfo('IL.txt').file_size>20_000_000: raise ValueError('Geographic text exceeds budget')
        lines=archive.read('IL.txt').decode('utf-8').splitlines()
    rows=[]
    for line in lines:
        r=line.split('\t')
        if r[7] not in ('PPL','PPLA','PPLA2','PPLA3','PPLC'): continue
        rows.append([r[0],r[1],r[2],r[3].split(','),r[7],float(r[4]),float(r[5]),r[10]])
    target.parent.mkdir(parents=True,exist_ok=True)
    write(target,rows)
    write(target.parent/'source.json',{'retrieved':retrieved,'archive_bytes':len(raw),'url':'https://download.geonames.org/export/dump/IL.zip'})

def qid(value): return value.rsplit('/',1)[-1]

def fetch(cache,kinds,hebrew=False,retrieved=None,israeli=False):
    retrieved=retrieved or date.today().isoformat()
    cache.mkdir(parents=True,exist_ok=True)
    for kind in kinds:
        tag=kind+'-il' if israeli else kind+'-he' if hebrew else kind
        selection_path=cache/(tag+'-selection.json')
        pattern,limit=(ISRAELI_SELECTIONS if israeli else SELECTIONS)[kind]
        if hebrew:
            import re
            pattern=re.sub(r'FILTER\(\?n>=\d+\)', '', pattern)
            # Genre joins multiply intermediate rows. The offline compiler
            # checks useful genres after this finite title/artist selection.
            pattern=pattern.replace('wdt:P136 ?g; ', '')
            if kind=='movies':
                pattern=pattern.replace('?item wdt:P31 wd:Q11424;', 'VALUES ?filmType {wd:Q11424 wd:Q202866} ?item wdt:P31 ?filmType;')
            if kind=='artists':
                # A focused Israeli supplement avoids a costly join across
                # every Hebrew-linked performer. Country is selection only;
                # it never classifies a player's identity or preferences.
                pattern='''{?item wdt:P27 wd:Q801; wdt:P31 wd:Q5.} UNION
{?item wdt:P495 wd:Q801; wdt:P31/wdt:P279* wd:Q215380.}
?item wdt:P136 ?g; wikibase:sitelinks ?n.'''
            else:
                pattern += ' ?heArticle schema:about ?item; schema:isPartOf <https://he.wikipedia.org/>.'
            limit=5000
        selection_query=f'SELECT DISTINCT ?item ?n WHERE {{ {pattern} }} ORDER BY DESC(?n) ?item LIMIT {limit}'
        if not selection_path.exists():
            rows=query(selection_query)
            time.sleep(4.0)
            if hebrew and kind in ('movies','hobbies'):
                extra_pattern=('?item wdt:P31 wd:Q202866;' if kind=='movies' else '?item wdt:P31/wdt:P279* wd:Q7889;')
                extra_limit=3000 if kind=='movies' else 500
                rows+=query('SELECT DISTINCT ?item ?n WHERE {'+extra_pattern+' wikibase:sitelinks ?n. FILTER(?n>=5)} ORDER BY DESC(?n) ?item LIMIT '+str(extra_limit))
                time.sleep(4.0)
            ids=list(dict.fromkeys(qid(r['item']) for r in rows))
            if hebrew:
                seed=Path(__file__).resolve().parent/'knowledge/curation.json'
                ids=list(dict.fromkeys((*ids,*json.loads(seed.read_text())['selection'].get(kind,[]))))
                already=set()
                for path in cache.glob(kind+'-[0-9]*.json'): already.update(json.loads(path.read_text()))
                ids=[q for q in ids if q not in already]
            write(selection_path,{'query':selection_query,'supplemental_animated_or_games':hebrew and kind in ('movies','hobbies'),'ids':ids,'retrieved':retrieved})
            print(f'{tag}: selected {len(ids)}',flush=True)
        ids=json.loads(selection_path.read_text())['ids']
        for offset in range(0,len(ids),150):
            path=cache/f'{tag}-{offset:05}.json'
            if path.exists(): continue
            values=' '.join('wd:'+q for q in ids[offset:offset+150])
            # Separate many-valued claims to avoid Cartesian multiplication.
            labels=f'''SELECT ?item ?en ?he ?titleEn ?titleHe WHERE {{ VALUES ?item {{{values}}}
OPTIONAL {{?item rdfs:label ?en FILTER(LANG(?en)="en")}}
OPTIONAL {{?item rdfs:label ?he FILTER(LANG(?he)="he")}}
OPTIONAL {{?ae schema:about ?item; schema:isPartOf <https://en.wikipedia.org/>; schema:name ?titleEn}}
OPTIONAL {{?ah schema:about ?item; schema:isPartOf <https://he.wikipedia.org/>; schema:name ?titleHe}} }}'''
            records={qid(r['item']):{k:v for k,v in r.items() if k!='item'} for r in query(labels)}
            time.sleep(4.0)
            branches=' UNION '.join('{?item wdt:'+p+' ?value. BIND(wdt:'+p+' AS ?prop)}'
                for p in ('P136','P31','P279','P2012','P495','P577','P179','P175'))
            claims='SELECT ?item ?prop ?value WHERE { VALUES ?item {'+values+'} '+branches+' }'
            for row in query(claims):
                record=records.setdefault(qid(row['item']),{})
                record.setdefault(qid(row['prop']),[]).append(qid(row['value']))
            write(path,records)
            print(f'{kind}: cached {min(offset+150,len(ids))}/{len(ids)}',flush=True)
            time.sleep(4.0)
    # A bounded taxonomy closure, not an unrestricted graph crawl.
    records={}
    for path in sorted(cache.glob('*.json')):
        if path.name.endswith('-selection.json') or path.name=='ancestors.json': continue
        records.update(json.loads(path.read_text()))
    ancestors_path=cache/'ancestors.json'
    ancestors=json.loads(ancestors_path.read_text()) if ancestors_path.exists() else {}
    for depth in range(4):
        roots={q for r in [*records.values(),*ancestors.values()] for p in ('P136','P31','P279','P2012') for q in r.get(p,[]) if q.startswith('Q')}
        todo=sorted(roots-set(records)-set(ancestors))
        if len(ancestors)+len(todo)>12000: raise ValueError('Taxonomy budget exceeded')
        for start in range(0,len(todo),150):
            batch=todo[start:start+150]; values=' '.join('wd:'+q for q in batch)
            rows=query(f'''SELECT ?item ?en ?he ?parent ?cuisine WHERE {{ VALUES ?item {{{values}}}
OPTIONAL {{?item rdfs:label ?en FILTER(LANG(?en)="en")}}
OPTIONAL {{?item rdfs:label ?he FILTER(LANG(?he)="he")}}
OPTIONAL {{?item wdt:P279 ?parent}} OPTIONAL {{?item wdt:P2012 ?cuisine}} }}''')
            for q in batch: ancestors[q]={}
            for r in rows:
                item=ancestors[qid(r['item'])]
                for k in ('en','he'):
                    if k in r:item[k]=r[k]
                for k,p in (('parent','P279'),('cuisine','P2012')):
                    if k in r and qid(r[k]) not in item.setdefault(p,[]): item[p].append(qid(r[k]))
            write(ancestors_path,ancestors)
            print(f'taxonomy: {len(ancestors)}',flush=True)
            time.sleep(4.0)
    print('Fetch complete. Review before compiling production assets.',flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fetch',type=Path,required=True)
    p.add_argument('--kinds',nargs='+',choices=tuple(SELECTIONS),default=list(SELECTIONS))
    p.add_argument('--hebrew',action='store_true',help='Supplement Hebrew-linked works/artists and animated films')
    p.add_argument('--israeli',action='store_true',help='Supplement Israeli/Hebrew songs and Israeli musicians')
    p.add_argument('--places-only',action='store_true',help='Fetch only the licensed GeoNames populated-place projection')
    p.add_argument('--retrieved',default=date.today().isoformat())
    a=p.parse_args()
    date.fromisoformat(a.retrieved)
    if a.places_only: fetch_places(a.fetch,a.retrieved)
    elif a.israeli:
        kinds=list(ISRAELI_SELECTIONS) if a.kinds==list(SELECTIONS) else a.kinds
        if a.hebrew or set(kinds)-set(ISRAELI_SELECTIONS): p.error('--israeli selects only songs and artists')
        fetch(a.fetch,kinds,retrieved=a.retrieved,israeli=True)
    else: fetch(a.fetch,a.kinds,a.hebrew,a.retrieved)

if __name__=='__main__':main()
