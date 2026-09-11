#!/usr/bin/env python3
"""Development-only reference builder. No network unless --refresh is explicit.

Default: validate committed assets. --compile CACHE compiles reviewed compact
Wikidata/GeoNames inputs. --refresh CACHE fetches public inputs for review;
never invoked by application startup, CI or deployment. See knowledge/README.md.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.domain.questions.knowledge import normalize_name  # noqa: E402
from app.infrastructure.knowledge import BUNDLE_DIR, load_knowledge  # noqa: E402

CURATION = Path(__file__).with_name('knowledge') / 'curation.json'
UA = 'MiZeMiKnowledgeBuild/1.0 (offline classroom reference; development only)'
PROPERTIES = ('P31', 'P279', 'P136', 'P2012')


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value,list):
        content='[\n'+',\n'.join(json.dumps(row,ensure_ascii=False,separators=(',',':')) for row in value)+'\n]\n'
    else:
        content=json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n'
    path.write_text(content)


def clean(text):
    return ''.join(c for c in unicodedata.normalize('NFC', text) if c.isprintable()).strip()


def unpoint(text):
    return ''.join(c for c in text if not ('\u0591' <= c <= '\u05bd' or c in '\u05bf\u05c1\u05c2\u05c4\u05c5\u05c7'))


def ancestry(q, concepts, depth=3):
    # Only subclass-of edges, bounded and cycle-safe. Never infer from part-of,
    # country-of-origin, associated acts, influences, demographics or ingredients.
    seen, frontier = {q}, {q}
    for _ in range(depth):
        frontier = {v for item in frontier for v in concepts.get(item, {}).get('claims', {}).get('P279', [])
                    if isinstance(v, str)} - seen
        seen.update(frontier)
    return seen


def compile_bundle(cache, output=BUNDLE_DIR, *, version=None, retrieved=None):
    config = json.loads(CURATION.read_text())
    concepts = json.loads((cache / 'concepts.json').read_text())
    roots = {key: set(ids) for key, ids in config['roots'].items()}
    categories = config['categories']
    by_dimension = {row[0]: row[1] for row in categories}
    files = {'categories.json': categories}
    omitted = {}
    for kind, ids in config['selection'].items():
        rows = []
        omitted[kind] = []
        for q in ids:
            e = concepts.get(q)
            if not e or 'Q4167410' in e['claims'].get('P31', []):
                omitted[kind].append(q)
                continue
            facts = set()
            if kind in ('movies', 'artists', 'music'):
                terms = {q} if kind == 'music' else set(e['claims'].get('P136', []))
                terms = set().union(*(ancestry(term, concepts, 2) for term in terms)) if terms else set()
                dimension = 'movie.genre' if kind == 'movies' else 'music.genre'
                facts = {key for key, ids in roots.items() if by_dimension[key] == dimension and terms & ids}
            elif kind == 'foods':
                terms = ancestry(q, concepts)
                # P31 is considered only for the immediate dish, not arbitrary
                # instances of classes; P2012 identifies cuisine association.
                terms.update(e['claims'].get('P31', []))
                for term in tuple(terms):
                    terms.update(concepts.get(term, {}).get('claims', {}).get('P2012', []))
                facts = {key for key, ids in roots.items() if by_dimension[key].startswith('food.') and terms & ids}
                facts.update(config['extra_food_facts'].get(q, []))
            elif kind == 'hobbies':
                facts = set(config['hobby_categories'].get(q, []))
            if not facts:
                omitted[kind].append(q)
                continue
            titles = e.get('titles', {})
            english = clean(titles.get('enwiki') or e['names'].get('en', ''))
            hebrew = clean(config['hebrew_labels'].get(q) or titles.get('hewiki', ''))
            if not english:
                omitted[kind].append(q)
                continue
            names = set(config['aliases'].get(q, []))
            # Strip disambiguators into aliases, never resolve a collision by
            # popularity. Both "Aladdin" remakes therefore remain ambiguous.
            for title in (english, hebrew):
                if title:
                    names.add(re.sub(r' \([^()]+\)$', '', title))
                    # Preserve year-qualified alternatives for remakes.
                    match = re.search(r'\((\d{4})(?: film)?\)', title)
                    if match:
                        names.add(re.sub(r' \([^()]+\)$', '', title) + ' ' + match[1])
            names = sorted({clean(n) for n in names if n and clean(n) not in (english, hebrew)})
            rows.append([q, english, hebrew, names, sorted(facts), None, e['revision']])
        files[kind + '.json'] = sorted(rows, key=lambda row: row[0])
    files['music.json'].extend(config.get('local_music',[]))
    places = []
    districts = dict(zip(('01','02','03','04','05','06'),
                         ('place.south','place.central','place.north','place.haifa','place.tel_aviv','place.jerusalem')))
    for e in json.loads((cache / 'localities.json').read_text()):
        if not (28.5 <= e['lat'] <= 34.5 and 33.5 <= e['lon'] <= 36.5):
            continue
        he = [clean(a) for a in e['aliases'] if any('א' <= c <= 'ת' for c in a)]
        pointed = [a for a in he if unpoint(a) != a]
        hebrew = config['place_hebrew'].get(e['id'], unpoint((pointed or he or [''])[0]))
        english = {'294097': 'Nof HaGalil'}.get(e['id'], clean(e['name']))
        # Do not import the multilingual/historical alternate-name dump.
        names = {clean(e['ascii']), *config['place_aliases'].get(e['id'], [])}
        names.discard(english); names.discard(hebrew); names.discard('')
        places.append(['G'+e['id'], english, hebrew, sorted(names),
                       [districts[e['district']]] if e['district'] in districts else [],
                       [round(e['lat'], 5), round(e['lon'], 5)], 0])
    files['localities.json'] = sorted(places, key=lambda row: row[0])
    output.mkdir(parents=True, exist_ok=True)
    for name, value in files.items():
        dump(output / name, value)
    manifest = {
        'schema': 1, 'version': version or date.today().isoformat()+'.1',
        'entity_columns': ['id','en','he','aliases','categories','lat_lon','source_revision'],
        'category_columns': ['id','dimension','en','he'],
        'sources': [
            {'name': 'Wikidata', 'url': 'https://www.wikidata.org/', 'retrieved': retrieved or date.today().isoformat(),
             'license': 'CC0-1.0', 'license_url': 'https://www.wikidata.org/wiki/Wikidata:Licensing',
             'fields': 'Entity IDs, revisions, en/he sitelink titles; P136, P279, P31, P2012; reviewed factual descriptions for listed food overrides.',
             'transformation': 'Explicit selections and reviewed taxonomy in scripts/knowledge/curation.json. Genre P136 → approved genre roots using at most two P279 edges. Food P279 up to three edges, immediate P31 and P2012. Hobby memberships are individually reviewed activity-context adaptations. No bulk aliases, prose, images or raw responses.',
             'record_url': 'https://www.wikidata.org/w/index.php?title={id}&oldid={source_revision}',
             'local_adaptations': 'local_israeli_pop is an authored lexical subtype of pop (Q37073). It has no artist, nationality or listener inference. Hebrew labels and reviewed aliases are local editorial adaptations.'},
            {'name': 'GeoNames', 'url': 'https://download.geonames.org/export/dump/IL.zip', 'retrieved': retrieved or date.today().isoformat(),
             'license': 'CC-BY-4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
             'fields': 'geonameid, name, asciiname, reviewed Hebrew name, WGS84 latitude/longitude, admin1 district',
             'transformation': 'Retain populated places PPL/PPLA/PPLA2/PPLA3/PPLC only. Drop historic/abandoned features, population, dates and bulk alternate names. Curate modern names; five-decimal coordinate pairs, FIPS district labels. Coverage is provider geography, not a sovereignty assertion.',
             'attribution': 'Contains information from GeoNames, available under CC BY 4.0. MiZeMi filtered, normalized and adapted the data.'},
        ],
        'policy': 'Only consented player inputs, positive reference classifications and deterministic mathematics may determine scores. Unknown is not a negative classification. Distances compare locality reference points, never homes or travel routes.',
        'files': {name: {'bytes': (output/name).stat().st_size, 'sha256': hashlib.sha256((output/name).read_bytes()).hexdigest(), 'rows': len(value)} for name,value in sorted(files.items())},
        'curation_sha256': hashlib.sha256(CURATION.read_bytes()).hexdigest(),
    }
    dump(output/'manifest.json', manifest)
    kb = load_knowledge(output)
    print(json.dumps({'entities': {k: len(v) for k,v in ((k,kb.in_kind(k)) for k in ('movies','artists','music','foods','hobbies','localities'))}, 'omitted': {k:len(v) for k,v in omitted.items()}}, indent=2))


def request_json(params):
    url = 'https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode({'format':'json', **params})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':UA}), timeout=30) as response:
                result = json.load(response)
            if 'error' in result:
                raise RuntimeError('Public metadata API returned an error; review cache before retrying.')
            return result
        except urllib.error.HTTPError as error:
            if error.code not in (429,502,503,504) or attempt == 2:
                raise
            try:
                delay=int(error.headers.get('Retry-After','15'))
            except ValueError:
                raise RuntimeError('Source requests a dated retry; resume after its Retry-After time.') from None
            if delay>60:
                raise RuntimeError('Source requests a longer pause; resume after its Retry-After interval.') from None
            time.sleep(max(2,delay))
    raise RuntimeError('Source unavailable')


def refresh(cache):
    """One paced API request at a time; bounded selected entities and parents."""
    config = json.loads(CURATION.read_text())
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / 'concepts.json'
    concepts = json.loads(path.read_text()) if path.exists() else {}
    selected = set().union(*map(set, config['selection'].values()), *map(set, config['roots'].values()))
    for level in range(4):
        todo = sorted(selected - set(concepts))
        if len(concepts) + len(todo) > 8000:
            raise RuntimeError('Research budget exceeded; narrow selection before continuing.')
        for start in range(0,len(todo),40):
            result = request_json({'action':'wbgetentities','ids':'|'.join(todo[start:start+40]),
                                   'props':'info|labels|claims|sitelinks','languages':'en|he',
                                   'languagefallback':1,'sitefilter':'enwiki|hewiki'})
            for q,e in result.get('entities',{}).items():
                if 'missing' in e:
                    continue
                claims = {}
                for prop in PROPERTIES:
                    values = []
                    for claim in e.get('claims',{}).get(prop,[]):
                        snak = claim.get('mainsnak',{})
                        value = snak.get('datavalue',{}).get('value')
                        if claim.get('rank') != 'deprecated' and snak.get('snaktype') == 'value' and isinstance(value,dict) and 'id' in value:
                            values.append(value['id'])
                    if values: claims[prop] = values
                concepts[q] = {'id':q,'revision':e.get('lastrevid',0), 'claims':claims,
                               'names':{k:v['value'] for k,v in e.get('labels',{}).items()},
                               'titles':{k:v['title'] for k,v in e.get('sitelinks',{}).items()}}
            dump(path, concepts)
            print(f'Cached {len(concepts)} public entities', flush=True)
            time.sleep(1.1)
        selected = {q for e in concepts.values() for prop in PROPERTIES for q in e['claims'].get(prop,[])}
    geopath = cache / 'localities.json'
    if not geopath.exists():
        with urllib.request.urlopen(urllib.request.Request('https://download.geonames.org/export/dump/IL.zip', headers={'User-Agent':UA}),timeout=30) as response:
            data = response.read(5_000_001)
        if len(data)>5_000_000:
            raise RuntimeError('Unexpected source archive size')
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if archive.getinfo('IL.txt').file_size>20_000_000:
                raise RuntimeError('Unexpected source text size')
            lines = archive.read('IL.txt').decode().splitlines()
        rows=[]
        for line in lines:
            v=line.split('\t')
            if len(v)==19 and v[6]=='P' and v[7] in ('PPL','PPLA','PPLA2','PPLA3','PPLC'):
                rows.append({'id':v[0],'name':v[1],'ascii':v[2],'aliases':v[3].split(','),
                             'lat':float(v[4]),'lon':float(v[5]),'district':v[10]})
        dump(geopath,rows)
    print('Review cached facts and curation before --compile. Refresh never writes production assets.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--compile',type=Path,metavar='CACHE')
    group.add_argument('--refresh',type=Path,metavar='CACHE')
    parser.add_argument('--output',type=Path,default=BUNDLE_DIR)
    parser.add_argument('--version',help='Version to stamp when compiling; default DATE.1')
    parser.add_argument('--retrieved',help='Source retrieval date (YYYY-MM-DD), for reproducing a reviewed cache')
    args=parser.parse_args()
    if args.refresh: refresh(args.refresh)
    elif args.compile: compile_bundle(args.compile,args.output,version=args.version,retrieved=args.retrieved)
    else:
        kb=load_knowledge(args.output)
        print(f'Validated {len(kb.entities)} offline entities ({kb.version})')

if __name__=='__main__': main()
