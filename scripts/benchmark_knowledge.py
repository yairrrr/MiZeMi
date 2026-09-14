#!/usr/bin/env python3
"""Offline reproducible measurements and synthetic social-game discoveries.

Run from the repository root: .venv/bin/python scripts/benchmark_knowledge.py
No public services, credentials, app database or network access are required.
"""
import gc
import gzip
import json
import os
from pathlib import Path
import platform
from random import Random
import resource
import statistics
import subprocess
import sys
from time import perf_counter
import tracemalloc

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.domain.questions import QuestionGenerator, QuestionValidator
from app.domain.questions.knowledge import KINDS
from app.domain.questions.discovery_rules import discovery_rules
from app.domain.questions.group_summary import summarize
from app.infrastructure.knowledge import BUNDLE_DIR, load_knowledge
from tests.fixtures.knowledge import dataset, ROWS, correct
from tests.fixtures.rooms import AUDIT_ROOMS, HE_RICH

# The 30-player benchmark profile set, unchanged so timings stay comparable across revisions.
FIELDS = ('city', 'favorite_food', 'hobby', 'favorite_music', 'favorite_movie', 'age')
ARTISTS = ('עומר אדם', 'עדן בן זקן', 'Taylor Swift', 'Metallica', 'Coldplay')
SONGS = ('Shake It Off - Taylor Swift', 'Blank Space', 'Enter Sandman', 'Yellow - Coldplay', 'Paradise - Coldplay')


def timed(function, repeats):
    times=[]
    for _ in range(repeats):
        start=perf_counter();function();times.append((perf_counter()-start)*1000)
    return {'median_ms':round(statistics.median(times),3),'max_ms':round(max(times),3),'runs':repeats}


def main():
    raw={p.name:p.read_bytes() for p in sorted(BUNDLE_DIR.glob('*.json'))}
    gc.collect();tracemalloc.start();start=perf_counter();kb=load_knowledge()
    load_ms=(perf_counter()-start)*1000
    gc.collect();retained,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    lookups=[('movies','המסור'),('movies','The Conjuring'),('artists','עומר אדם'),('foods','פיצה'),
             ('hobbies','גיימינג'),('music','היפ הופ'),('localities','ת״א'),('movies','unlisted movie')]
    n=100_000;start=perf_counter()
    for i in range(n): kb.resolve(*lookups[i%len(lookups)])
    lookup_us=(perf_counter()-start)*1_000_000/n
    generation=QuestionGenerator(knowledge=kb)
    rows=[{**dict(zip(FIELDS,ROWS[i%5])),'age':15+i,'favorite_artist':ARTISTS[i%5],'favorite_song':SONGS[i%5]} for i in range(30)]
    def generate(seed=77):
        qs=generation.generate(dataset(rows),question_count=20,time_limit_seconds=20,seed=seed)
        assert len(qs)==20
        return qs
    generation_times=timed(generate,20)
    start=perf_counter()
    for room in range(25): generate(room)
    rooms_ms=(perf_counter()-start)*1000
    code='import json,resource,sys; from time import perf_counter; t=perf_counter(); import app.main; print(json.dumps({"ms":(perf_counter()-t)*1000,"rss":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=="darwin" else 1024)}))'
    env={**os.environ,'PYTHONPATH':str(ROOT/'backend'),'MIZEMI_DATABASE_URL':'sqlite://','MIZEMI_ENV':'test'}
    cold=[json.loads(subprocess.check_output([sys.executable,'-c',code],cwd=ROOT,env=env,text=True).strip()) for _ in range(5)]
    all_bytes=b''.join(raw.values())
    data={
        'python':platform.python_version(),'platform':platform.platform(),'dataset_version':kb.version,
        'entity_counts':{kind:len(kb.in_kind(kind)) for kind in KINDS},
        'aliases':{kind:sum(len(e.aliases) for e in kb.in_kind(kind)) for kind in KINDS},
        'normalized_lookup_keys':{kind:len(kb._indexes[kind]) for kind in KINDS},
        'ambiguous_keys_rejected':{kind:len(kb.ambiguous_names[kind]) for kind in KINDS},
        'categories':len(kb.categories),'raw_bundle_bytes':len(all_bytes),
        'gzip_bundle_bytes':len(gzip.compress(all_bytes,compresslevel=9,mtime=0)),
        'raw_files_bytes':{name:len(value) for name,value in raw.items()},
        'build_curation_bytes':sum((ROOT/'scripts/knowledge'/name).stat().st_size for name in ('curation.json','group-curation.json')),
        'hebrew_names':{kind:sum(bool(e.hebrew) for e in kb.in_kind(kind)) for kind in KINDS},
        'load_with_tracemalloc_ms':round(load_ms,3),'load_uninstrumented':timed(load_knowledge,10),
        'knowledge_retained_python_bytes':retained,'knowledge_peak_python_bytes':peak,
        'process_max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),
        'lookup_average_microseconds':round(lookup_us,3),'lookups':n,
        'cold_app_import_median_ms':round(statistics.median(r['ms'] for r in cold),3),
        'cold_app_import_median_rss_bytes':statistics.median(r['rss'] for r in cold),
        '30_players_20_questions':generation_times,
        '25_rooms_30_players_20_questions_total_ms':round(rooms_ms,3),
        'realistic_20_player_room_20_questions':timed(lambda: generation.generate(HE_RICH.dataset(),question_count=20,time_limit_seconds=20,seed=5),20),
    }
    target=ROOT/'scripts/knowledge/benchmark-results.json'
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    partial_rows=[dict(row) for row in rows]
    partial_rows[-1]['favorite_movie']='unknown movie'
    data['30_players_one_unknown_movie']=timed(lambda: generation.generate(dataset(partial_rows),question_count=20,time_limit_seconds=20,seed=77),10)
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    examples={}
    specialized={}
    for language in ('en','he'):
        examples[language]=[]
        for rule in discovery_rules(kb):
            ds=dataset(specialized.get(rule.rule_id,ROWS),language=language)
            candidates=[c for c in rule.generate(ds,Random(5)) if QuestionValidator().is_valid(c,ds)]
            if not candidates: continue
            c=candidates[0]
            examples[language].append({'rule':rule.rule_id,'question':c.text,'options':[o.text for o in c.options],
                                       'correct':correct(c),'explanation':c.explanation})
    (ROOT/'scripts/knowledge/demo-results.json').write_text(json.dumps({'synthetic_profiles':ROWS,'specialized_profiles':specialized,'examples':examples},ensure_ascii=False,indent=2)+'\n')
    summaries=[summarize(room.dataset(),kb) for room in AUDIT_ROOMS]
    dimensions=sorted({key for s in summaries for key in s.dimensions})
    data['audit_room_recognition']={key:{
        'shared_answers':sum(len(s.dimensions[key].consented) for s in summaries if key in s.dimensions),
        'recognized':sum(len(s.dimensions[key].recognized) for s in summaries if key in s.dimensions),
        'unknown':sum(len(s.dimensions[key].unknown) for s in summaries if key in s.dimensions)} for key in dimensions}
    data['note']='Recognition describes the published synthetic audit rooms, not a population estimate. RSS includes Python and benchmark instrumentation.'
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(data,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
