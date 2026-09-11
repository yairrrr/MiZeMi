"""Classroom limits, safe errors and production configuration regression tests."""
import asyncio
import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.main import create_app
from app.infrastructure.settings import Settings
from app.infrastructure.database import Base
from app.infrastructure.repositories import SqlAlchemyGameRepository
from app.realtime.connections import ConnectionHandle, MAX_QUEUED_MESSAGES
from app.realtime.transport import PLAYER_PROTOCOL
from tests.fixtures.live import create_room, join, player_ws, receive_until, envelope, profile_fields
from tests.integration.test_game_flow_hardening import Table, _app, NAMES


def test_http_body_limit_and_no_store_credentials():
    with TestClient(_app()) as client:
        response = client.post('/api/v1/rooms')
        assert response.status_code == 201
        assert response.headers['cache-control'] == 'no-store'
        assert response.headers['x-content-type-options'] == 'nosniff'
        assert response.headers['referrer-policy'] == 'no-referrer'
        code = response.json()['room_code']
        for data in ['x' * 17000, json.dumps({'display_name': 'x' * 17000})]:
            response = client.post(f'/api/v1/rooms/{code}/players', content=data)
            assert response.status_code == 413
            assert 'x' * 20 not in response.text


def test_chunked_body_limit():
    with TestClient(_app()) as client:
        response = client.post('/api/v1/rooms', content=iter([b'x' * 9000, b'y' * 9000]))
    assert response.status_code == 413


def test_post_rate_limit_keeps_health_available():
    with TestClient(_app()) as client:
        for _ in range(240):
            client.post('/api/v1/rooms/UNKNOWN/players', json={'display_name': 'Dana'})
        assert client.post('/api/v1/rooms').status_code == 429
        assert client.get('/api/v1/health').status_code == 200


def test_room_capacity_is_bounded(monkeypatch):
    monkeypatch.setattr('app.realtime.hub.MAX_ACTIVE_ROOMS', 2)
    with TestClient(_app()) as client:
        assert client.post('/api/v1/rooms').status_code == 201
        assert client.post('/api/v1/rooms').status_code == 201
        assert client.post('/api/v1/rooms').status_code == 503


@pytest.mark.parametrize('content', [b'binary', 'not json', 'x' * 17000, '[1, 2]', '{"a":NaN}'])
def test_bad_frames_do_not_crash_the_room(content):
    with TestClient(_app()) as client:
        room = create_room(client)
        player = join(client, room.room_code, 'Dana')
        with player_ws(client, room.room_code, player) as ws:
            if isinstance(content, bytes):
                ws.send_bytes(content)
            else:
                ws.send_text(content)
            assert receive_until(ws, 'error')['payload']['error']['code'] == 'VALIDATION_ERROR'


def test_production_requires_tls_database_and_exact_https_origin():
    common = {'env': 'production', '_env_file': None}
    with pytest.raises(ValueError, match='PostgreSQL'):
        create_app(Settings(**common, database_url='sqlite://'))
    with pytest.raises(ValueError, match='HTTPS'):
        create_app(Settings(**common, database_url='postgresql://user:placeholder@db.example.invalid/db?sslmode=require', cors_origins=['*']))
    app = create_app(Settings(**common, database_url='postgresql://user:placeholder@db.example.invalid/db?sslmode=require', cors_origins=['https://classroom.example']))
    assert app.state.database.engine.dialect.driver == 'psycopg'
    assert 'placeholder' not in repr(app.state.settings)
    app.state.game_hub.shutdown()
    app.state.database.engine.dispose()


def test_hosting_environment_aliases(monkeypatch):
    monkeypatch.delenv('MIZEMI_DATABASE_URL', raising=False)
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('PORT', '10000')
    monkeypatch.setenv('HOST', '0.0.0.0')
    monkeypatch.setenv('FRONTEND_ORIGIN', 'https://classroom.example')
    settings = Settings(_env_file=None)
    assert settings.env.value == 'production'
    assert settings.port == 10000
    assert settings.host == '0.0.0.0'
    assert settings.cors_origins == ('https://classroom.example',)


def test_slow_socket_queue_is_bounded_and_closed():
    class SlowSocket:
        def __init__(self):
            self.code = None
        async def send_json(self, data):
            await asyncio.Event().wait()
        async def close(self, code=1000):
            self.code = code

    async def check():
        socket = SlowSocket()
        handle = ConnectionHandle(socket, role='host')
        for i in range(MAX_QUEUED_MESSAGES + 10):
            handle.enqueue({'event': 'test', 'payload': i})
        await asyncio.sleep(0.01)
        assert handle.closed
        assert socket.code == 1013
        await handle.shutdown()
    asyncio.run(check())


def test_finished_answers_scores_upsert_and_retention_cascade():
    app = _app(questions_per_game=1)
    with TestClient(app) as client, Table(client, app) as table:
        table.start()
        for name in NAMES:
            table.answer(name, correct=(name == 'Dana'))
        receive_until(table.host, 'question.ended')
        table.host_send('game.next')
        receive_until(table.host, 'leaderboard.updated')
        table.host_send('game.next')
        receive_until(table.host, 'game.finished')
        app.state.game_hub.flush_persistence()
        with app.state.database.session_factory() as session:
            repository = SqlAlchemyGameRepository(session)
            repository.save(table.game)
            session.commit()
            record = repository.get(table.game.game_id)
            assert len(record.answers) == 3
            assert {s.player_id: s.total_score for s in record.scores} == table.game.scores
            assert repository.delete_older_than(datetime.now(UTC) + timedelta(days=1)) == 1
            session.commit()
            for model in Base.metadata.sorted_tables:
                assert session.scalar(select(func.count()).select_from(model)) == 0


def test_database_errors_never_log_query_parameters(caplog, monkeypatch):
    app = _app(questions_per_game=1)
    def fail(game):
        raise RuntimeError('private_profile_marker postgres://private:password@host/db')
    monkeypatch.setattr(app.state.game_hub, '_persist', fail)
    with TestClient(app) as client, Table(client, app) as table:
        table.start()
        for name in NAMES:
            table.answer(name, correct=True)
        receive_until(table.host, 'question.ended')
        table.host_send('game.next')
        receive_until(table.host, 'leaderboard.updated')
        table.host_send('game.next')
        receive_until(table.host, 'game.finished')
    assert 'failed to persist a finished game' in caplog.text
    assert 'private_profile_marker' not in caplog.text
    assert 'password' not in caplog.text


@pytest.mark.parametrize("mutation", ["boolean_value", "string_consent", "too_many_fields"])
def test_profile_types_cannot_coerce_consent_or_age(mutation):
    with TestClient(_app()) as client:
        room = create_room(client)
        player = join(client, room.room_code, "Dana")
        fields = profile_fields()
        if mutation == "boolean_value":
            fields.append({"field_key": "age", "value": True, "allow_question_usage": True})
        elif mutation == "string_consent":
            fields[0]["allow_question_usage"] = "yes"
        else:
            fields *= 2
        with player_ws(client, room.room_code, player) as ws:
            ws.send_json(envelope("player.profile_submit", {"player_id": player.player_id, "fields": fields}, room.game_id))
            assert receive_until(ws, "error")["payload"]["error"]["code"] == "VALIDATION_ERROR"


def test_socket_limit_retains_existing_connections():
    from contextlib import ExitStack
    from starlette.websockets import WebSocketDisconnect
    with TestClient(_app()) as client, ExitStack() as stack:
        room = create_room(client)
        player = join(client, room.room_code, "Dana")
        for _ in range(4):
            ws = stack.enter_context(player_ws(client, room.room_code, player))
            receive_until(ws, "room.updated")
        with pytest.raises(WebSocketDisconnect):
            with player_ws(client, room.room_code, player):
                pytest.fail("fifth socket must be denied")
        ws.send_json(envelope("player.join", {}, room.game_id))
        assert receive_until(ws, "room.updated")["payload"]["players"][0]["connected"]


def test_message_flood_closes_connection():
    from starlette.websockets import WebSocketDisconnect
    with TestClient(_app()) as client:
        room = create_room(client)
        player = join(client, room.room_code, "Dana")
        with player_ws(client, room.room_code, player) as ws:
            receive_until(ws, "room.updated")
            for _ in range(120):
                ws.send_text("bad json")
                receive_until(ws, "error")
            ws.send_text("bad json")
            with pytest.raises(WebSocketDisconnect) as closed:
                ws.receive_json()
            assert closed.value.code == 1013
