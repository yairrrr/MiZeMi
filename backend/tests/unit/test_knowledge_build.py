"""Compilation is reproducible offline; source fetch is an explicit dev action."""
import importlib.util
import json
from pathlib import Path
import socket

from app.infrastructure.knowledge import load_knowledge

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('knowledge_builder',ROOT/'scripts/build_knowledge_base.py')
builder=importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_compact_source_compilation_is_offline_and_reproducible(tmp_path,monkeypatch):
    def entity(q,en,he,claims):
        return {'id':q,'revision':123,'names':{},'titles':{'enwiki':en,'hewiki':he},'claims':claims}
    records={q:entity(q,en,he,claims) for q,en,he,claims in (
        ('Q486239','Saw (film)','המסור',{'P136':['Q200092']}),
        ('Q2918713','Omer Adam','עומר אדם',{'P136':['Q2738544']}),
        ('Q2738544','Mizrahi music','מוזיקה מזרחית',{}),
        ('Q177','Pizza','פיצה',{'P2012':['Q192786']}),
        ('Q105674','Running','ריצה',{}),
    )}
    cache=tmp_path/'cache';cache.mkdir()
    (cache/'concepts.json').write_text(json.dumps(records))
    (cache/'localities.json').write_text(json.dumps([{'id':'293397','name':'Tel Aviv','ascii':'Tel Aviv','aliases':['תל אביב'],
                                                    'lat':32.08088,'lon':34.78057,'district':'05'}]))
    def forbidden(*a,**k): raise AssertionError('compilation must not fetch')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    for name in ('one','two'):
        builder.compile_bundle(cache,tmp_path/name,version='test.1',retrieved='2026-09-11')
    for file in (tmp_path/'one').iterdir(): assert file.read_bytes()==(tmp_path/'two'/file.name).read_bytes()
    kb=load_knowledge(tmp_path/'one')
    assert 'movie.horror' in kb.resolve_movie('המסור').entity.category_ids
    assert kb.resolve_israeli_locality('ת״א').entity.coordinates==(32.08088,34.78057)
    assert 'music.pop' in kb.resolve_music_genre('Israeli pop').entity.category_ids


def test_research_code_is_not_imported_by_runtime():
    for file in (ROOT/'backend/app').rglob('*.py'):
        assert 'import build_knowledge_base' not in file.read_text()
        assert 'scripts.knowledge' not in file.read_text()
