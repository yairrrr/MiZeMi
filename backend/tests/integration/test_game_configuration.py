"""Public config bounds, shared language, reconnect and additive persistence."""

import contextlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, func

from app.domain.game.config import GameConfig
from app.infrastructure.database import Base, create_database_engine, create_session_factory
from app.infrastructure.database.models import GameRow
from app.infrastructure.repositories import SqlAlchemyGameRepository
from tests.fixtures.live import CreatedRoom, host_ws, join, player_ws, submit_profile_and_ready, receive_until, envelope, distinct_profiles, wait_for_snapshot
from tests.integration.test_game_flow_hardening import _app


@pytest.mark.parametrize('body', [None, {}, {'language':'en'}])
def test_old_create_clients_get_twenty_questions(body):
    with TestClient(_app()) as client:
        response = client.post('/api/v1/rooms', **({} if body is None else {'json':body}))
        assert response.status_code == 201
        assert response.json()['config'] == {'question_count':20,'language':'en'}


@pytest.mark.parametrize('value', [0,-1,51,10**12,True,False,3.0,2.5,'20',None,[],{}])
def test_count_is_strictly_validated_by_server(value):
    with TestClient(_app()) as client:
        response = client.post('/api/v1/rooms', json={'question_count':value})
        assert response.status_code == 422
        assert response.json()['error']['code'] == 'VALIDATION_ERROR'
        assert 'traceback' not in response.text.lower()


@pytest.mark.parametrize('language', ['fr','../he','he.html','HE',None,True,[],{}])
def test_language_is_an_allowlisted_value_not_a_path(language):
    with TestClient(_app()) as client:
        assert client.post('/api/v1/rooms', json={'language':language}).status_code == 422


@pytest.mark.parametrize('count', [1,5,20,50])
def test_config_is_in_create_response_domain_and_reconnect(count):
    app = _app()
    with TestClient(app) as client:
        body = client.post('/api/v1/rooms', json={'question_count':count,'language':'he'}).json()
        room = CreatedRoom(body['room_code'], body['game_id'], body['host_token'])
        assert app.state.room_registry.get(room.room_code).game.config == GameConfig(count, 'he')
        for _ in range(2):
            with host_ws(client, room) as host:
                snapshot = receive_until(host, 'room.updated')['payload']
                assert snapshot['config'] == body['config']
                assert snapshot['total_questions'] == count
                assert 'host_token' not in str(snapshot)


@pytest.mark.parametrize('language,count', [('en',20),('he',5)])
def test_public_config_controls_full_game_and_survives_results_and_persistence(language,count):
    app = _app()
    with TestClient(app) as client, contextlib.ExitStack() as stack:
        body = client.post('/api/v1/rooms', json={'question_count':count,'language':language}).json()
        room = CreatedRoom(body['room_code'], body['game_id'], body['host_token'])
        host = stack.enter_context(host_ws(client, room))
        names = ['Dana','Omer','Noa']
        profiles = distinct_profiles(names)
        peers=[]
        for name in names:
            player = join(client, room.room_code, name)
            socket = stack.enter_context(player_ws(client, room.room_code, player))
            submit_profile_and_ready(socket, room.game_id, player, **profiles[name])
            peers.append((player,socket))
        wait_for_snapshot(host, lambda snapshot: snapshot['state'] == 'READY')
        host.send_json(envelope('game.start', {}, room.game_id))
        game = app.state.room_registry.get(room.room_code).game
        for index in range(count):
            question = receive_until(host, 'question.started')['payload']
            assert question['index'] == index
            assert question['total_questions'] == count
            assert question['language'] == language
            assert 'correct_option_id' not in question
            for player, socket in peers:
                socket.send_json(envelope('answer.submit', {'question_id':question['question_id'],'option_id':question['options'][0]['option_id']}, room.game_id))
            ended = receive_until(host, 'question.ended')['payload']
            assert ended['text'] == question['text']
            with host_ws(client, room) as restored:
                snapshot=receive_until(restored,'room.updated')['payload']
                assert snapshot['config'] == body['config']
                assert receive_until(restored,'question.ended')['payload'] == ended
            host.send_json(envelope('game.next', {}, room.game_id))
            receive_until(host,'leaderboard.updated')
            host.send_json(envelope('game.next', {}, room.game_id))
        receive_until(host,'game.finished')
        app.state.game_hub.flush_persistence()
        with app.state.database.session_factory() as session:
            record=SqlAlchemyGameRepository(session).get(room.game_id)
            assert record.config == GameConfig(count,language)
            assert len(record.questions) == count
            assert {q.language for q in record.questions} == {language}
            assert [q.difficulty for q in record.questions] == [q.difficulty.value for q in game.questions]
            assert all(q.source_rule_id for q in record.questions)


def test_additive_schema_preserves_old_records_without_configuration():
    engine=create_database_engine('sqlite://')
    original=[t for t in Base.metadata.sorted_tables if t.name not in ('game_configurations','question_details','question_explanations')]
    Base.metadata.create_all(engine, tables=original)
    with create_session_factory(engine)() as session:
        session.add(GameRow(game_id='old',state='FINISHED',current_question_index=None))
        session.commit()
    Base.metadata.create_all(engine)
    assert len(inspect(engine).get_table_names()) == 10
    with create_session_factory(engine)() as session:
        record=SqlAlchemyGameRepository(session).get('old')
        assert record.game_id == 'old' and record.config.language == 'en'
        SqlAlchemyGameRepository(session).delete('old')
        session.commit()
        assert all(session.scalar(select(func.count()).select_from(t)) == 0 for t in Base.metadata.sorted_tables)
    engine.dispose()
