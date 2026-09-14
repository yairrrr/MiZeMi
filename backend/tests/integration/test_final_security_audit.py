"""Adversarial audit regressions using only synthetic local participants."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from starlette.websockets import WebSocketDisconnect

from app.domain.game import GameState
from app.infrastructure.database.models import GameRow
from app.infrastructure.repositories import SqlAlchemyGameRepository
from tests.fixtures.live import (collect_until, create_room, envelope, host_ws, join,
                                player_ws, profile_fields, receive_until)
from tests.integration.test_game_flow_hardening import Table, _app


@pytest.mark.parametrize('name', ['Dana\u200b', 'Dana\u202e', 'Dana\u2066', '\u200b', 'Da\x00na', 'Da\ud800na'])
def test_invisible_control_and_surrogate_names_are_rejected(name):
    with TestClient(_app()) as client:
        room = create_room(client)
        response = client.post(f'/api/v1/rooms/{room.room_code}/players',
                               content=json.dumps({'display_name': name}), headers={'content-type': 'application/json'})
        assert response.status_code in (400, 422)
        assert len(client.app.state.room_registry.get(room.room_code).game.players) == 0


@pytest.mark.parametrize('first,second', [('Café', 'Cafe\u0301'), ('Dana Lee', 'Dana  Lee'), ('דָּנָה', 'דָּנָה')])
def test_equivalent_display_names_cannot_create_a_second_identity(first, second):
    with TestClient(_app()) as client:
        room = create_room(client)
        join(client, room.room_code, first)
        response = client.post(f'/api/v1/rooms/{room.room_code}/players', json={'display_name': second})
        assert response.status_code == 409
        assert response.json()['error']['code'] == 'NAME_TAKEN'


@pytest.mark.parametrize('value', ['Saw\u202e', 'חיפה\u200b', 'x\x00y', '\ud800'])
def test_profile_controls_are_rejected_without_echo(value):
    with TestClient(_app()) as client:
        room = create_room(client)
        player = join(client, room.room_code, 'דנה Dana')
        fields = profile_fields()
        fields.append({'field_key': 'favorite_movie', 'value': value, 'allow_question_usage': False})
        with player_ws(client, room.room_code, player) as ws:
            ws.send_text(json.dumps(envelope('player.profile_submit', {'player_id': player.player_id, 'fields': fields}, room.game_id)))
            error = receive_until(ws, 'error')
            assert error['payload']['error']['code'] == 'VALIDATION_ERROR'
            assert value not in error['payload']['error']['message']


@pytest.mark.parametrize('value', ['', ' ', None, 123, True, {}, [], 'x' * 101])
def test_invalid_display_name_types_and_bounds(value):
    with TestClient(_app()) as client:
        room = create_room(client)
        assert client.post(f'/api/v1/rooms/{room.room_code}/players', json={'display_name': value}).status_code in (400, 422)


@pytest.mark.parametrize('origin,allowed', [('https://classroom.example', True), ('https://evil.example', False), ('http://localhost:5173', False), ('null', False), (None, True)])
@pytest.mark.parametrize('role', ['host', 'player'])
def test_websocket_origin_gate_even_with_valid_credentials(origin, allowed, role):
    with TestClient(_app(cors_origins=['https://classroom.example'])) as client:
        room = create_room(client)
        player = join(client, room.room_code, 'Dana')
        headers = {} if origin is None else {'origin': origin}
        socket = host_ws(client, room, headers=headers) if role == 'host' else player_ws(client, room.room_code, player, headers=headers)
        if allowed:
            with socket as ws:
                assert receive_until(ws, 'room.updated')['payload']['room_code'] == room.room_code
        else:
            with pytest.raises(WebSocketDisconnect) as closed:
                with socket:
                    pytest.fail('untrusted browser origin accepted')
            assert closed.value.code == 4403


@pytest.mark.parametrize('extra', [{'player_id': 'another-player'}, {'answered_at': '2000-01-01T00:00:00Z'}, {'score': 99999}, {'is_correct': True}])
def test_answer_never_accepts_client_identity_time_score_or_correctness(extra):
    app = _app(questions_per_game=1)
    with TestClient(app) as client, Table(client, app) as table:
        question = table.start()
        table.player_send('Dana', 'answer.submit', {'question_id': question['question_id'], 'option_id': question['options'][0]['option_id'], **extra})
        assert receive_until(table.sockets['Dana'], 'error')['payload']['error']['code'] == 'VALIDATION_ERROR'
        assert not table.game.answers_for(question['question_id'])


@pytest.mark.parametrize('ready', [False, True])
def test_reconnect_lobby_and_ready_never_disclose_profiles_or_credentials(ready):
    app = _app()
    with TestClient(app) as client, Table(client, app) as table:
        if ready:
            table.ready_everyone()
        with player_ws(client, table.room.room_code, table.players['Dana']) as ws:
            snapshot = receive_until(ws, 'room.updated')
        assert snapshot['payload']['state'] == ('READY' if ready else table.game.state.value)
        assert not any(key in json.dumps(snapshot) for key in ['fields', 'host_token', 'player_token', 'correct_option_id'])


def test_answered_reconnect_hides_answer_key_and_preserves_deadline():
    app = _app(questions_per_game=1)
    with TestClient(app) as client, Table(client, app) as table:
        original = table.start()
        table.answer('Dana', correct=True)
        receive_until(table.sockets['Dana'], 'answer.accepted')
        with player_ws(client, table.room.room_code, table.players['Dana']) as ws:
            messages = collect_until(ws, 'answer.accepted')
        assert 'correct_option_id' not in json.dumps(messages)
        question = next(m['payload'] for m in messages if m['event'] == 'question.started')
        assert question['started_at'] == original['started_at']
        assert question['time_limit_seconds'] == original['time_limit_seconds']


def test_concurrent_duplicate_answer_and_timeout_close_score_once():
    app = _app(questions_per_game=1)
    with TestClient(app) as client, Table(client, app) as table:
        question = table.start()
        for name in ['Dana', 'Omer']:
            table.answer(name, correct=True)
            receive_until(table.sockets[name], 'answer.accepted')
        hub = app.state.game_hub
        room = app.state.room_registry.get(table.room.room_code)
        player_id = table.players['Noa'].player_id
        handle = next(h for h in app.state.room_connections.handles_for(room.room_code) if h.player_id == player_id)
        raw = json.dumps(envelope('answer.submit', {'question_id': question['question_id'], 'option_id': table.game.current_question.correct_option_id}, table.room.game_id))
        barrier = Barrier(3)
        def action(close):
            barrier.wait(timeout=5)
            if close:
                hub.close_if_active(room, question['question_id'])
            else:
                hub.handle_message(room, handle, raw)
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(action, close) for close in [False, False, True]]
            for future in futures:
                future.result(timeout=5)
        receive_until(table.host, 'question.ended')
        assert table.game.state is GameState.QUESTION_RESULTS
        assert len(table.game.answers_for(question['question_id'])) in (2, 3)
        scores = dict(table.game.scores)
        assert all(0 <= score <= 1000 for score in scores.values())
        assert hub.close_if_active(room, question['question_id']) is False
        assert table.game.scores == scores
        assert not hub.has_pending_deadline(room.room_code)


def test_forwarded_headers_do_not_change_http_rate_limit_identity():
    with TestClient(_app()) as client:
        for i in range(240):
            response = client.post('/api/v1/rooms/UNKNOWN/players', json={'display_name': 'Dana'}, headers={'x-forwarded-for': f'192.0.2.{i}', 'x-real-ip': f'198.51.100.{i}'})
            assert response.status_code == 404
        assert client.post('/api/v1/rooms', headers={'x-forwarded-for': '203.0.113.1'}).status_code == 429


def test_retention_is_bounded_and_preserves_active_and_recent_games(db_session):
    old = datetime.now(UTC) - timedelta(days=8)
    rows = [GameRow(game_id=f'expired-{i}', state='FINISHED', created_at=old, updated_at=old) for i in range(101)]
    rows += [GameRow(game_id='active', state='QUESTION_ACTIVE', created_at=old, updated_at=old), GameRow(game_id='recent', state='FINISHED')]
    db_session.add_all(rows)
    db_session.commit()
    repository = SqlAlchemyGameRepository(db_session)
    cutoff = datetime.now(UTC) - timedelta(days=7)
    assert repository.delete_older_than(cutoff) == 100
    db_session.commit()
    assert repository.delete_older_than(cutoff) == 1
    db_session.commit()
    assert set(db_session.scalars(select(GameRow.game_id))) == {'active', 'recent'}


@pytest.mark.parametrize('origin', ['https://*', 'https://name:password@example.invalid', 'https://example.invalid:bad', 'https://example.invalid:0', 'https://exa mple.invalid', 'https://example.invalid/path', 'https://example.invalid#fragment', 'http://example.invalid'])
def test_production_rejects_malformed_origins_without_echoing(origin):
    from app.main import create_app
    from app.infrastructure.settings import Settings
    with pytest.raises(ValueError) as error:
        create_app(Settings(env='production', database_url='postgresql://user:placeholder@db.example.invalid/game?sslmode=require', cors_origins=[origin], _env_file=None))
    assert origin not in str(error.value)
    assert 'password' not in str(error.value)


def test_huge_content_length_is_rejected_without_integer_conversion_error():
    with TestClient(_app()) as client:
        assert client.post('/api/v1/rooms', content='{}', headers={'content-length': '9' * 5000}).status_code == 413


def test_failed_finished_write_rolls_back_whole_tree_and_preserves_scores(monkeypatch, caplog):
    from sqlalchemy import func
    from app.infrastructure.database import Base
    original = SqlAlchemyGameRepository.save
    def fail_after_flush(repository, game):
        original(repository, game)
        raise RuntimeError('synthetic-private-failure-marker')
    app = _app(questions_per_game=1)
    with TestClient(app) as client, Table(client, app) as table:
        table.start()
        for name in table.players:
            table.answer(name, correct=True)
        receive_until(table.host, 'question.ended')
        scores = dict(table.game.scores)
        monkeypatch.setattr(SqlAlchemyGameRepository, 'save', fail_after_flush)
        table.host_send('game.next')
        receive_until(table.host, 'leaderboard.updated')
        table.host_send('game.next')
        receive_until(table.host, 'game.finished')
        app.state.game_hub.flush_persistence()
        assert table.game.state is GameState.FINISHED and table.game.scores == scores
        with app.state.database.session_factory() as session:
            assert all(session.scalar(select(func.count()).select_from(model)) == 0 for model in Base.metadata.sorted_tables)
    assert 'failed to persist a finished game' in caplog.text
    assert 'synthetic-private-failure-marker' not in caplog.text
