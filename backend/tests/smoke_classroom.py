"""Real TCP smoke test: python backend/tests/smoke_classroom.py [--url URL].

Starts a disposable local backend by default. Uses only synthetic profiles.
Never prints credentials, profile values or raw WebSocket frames.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime

import httpx
from websockets.asyncio.client import connect


async def scenario(url: str, player_count: int = 20) -> None:
    ws_base = url.replace('http', 'ws', 1)
    sockets = []
    started = time.monotonic()
    async with httpx.AsyncClient(base_url=url, timeout=10) as client:
        response = await client.post('/api/v1/rooms')
        response.raise_for_status()
        room = response.json()
        code, game_id = room['room_code'], room['game_id']
        async def send(ws, event, payload=None):
            await ws.send(json.dumps({'event': event, 'payload': payload or {},
                                     'game_id': game_id, 'timestamp': datetime.now(UTC).isoformat().replace('+00:00', 'Z')}))
        async def until(ws, event, predicate=lambda p: True):
            async with asyncio.timeout(15):
                while True:
                    message = json.loads(await ws.recv())
                    assert message['game_id'] == game_id
                    assert message['timestamp'].endswith('Z')
                    assert 'host_token' not in str(message) and 'player_token' not in str(message)
                    assert 'fields' not in message['payload']
                    assert message['event'] != 'error', message['payload']['error']['code'] if message['event'] == 'error' else ''
                    if message['event'] == event and predicate(message['payload']):
                        return message['payload']
        try:
            host = await connect(f'{ws_base}/ws/rooms/{code}/host', subprotocols=['mizemi.host', room['host_token']])
            sockets.append(host)
            await until(host, 'room.updated')
            async def join_one(i):
                response = await client.post(f'/api/v1/rooms/{code}/players', json={'display_name': f'Player {i:02d}'})
                response.raise_for_status()
                return response.json()
            joined = await asyncio.gather(*(join_one(i) for i in range(player_count)))
            players = await asyncio.gather(*(connect(f"{ws_base}/ws/rooms/{code}?player_id={p['player']['player_id']}",
                subprotocols=['mizemi.player', p['player_token']]) for p in joined))
            sockets.extend(players)
            snapshot = await until(host, 'room.updated', lambda p: len(p['players']) == player_count and all(x['connected'] for x in p['players']))
            assert len(snapshot['players']) == player_count
            async def ready_one(i, ws):
                values = {'city': ['Haifa', 'Eilat', 'Jerusalem'][i % 3],
                          'favorite_food': ['pizza', 'sushi'][i % 2],
                          'hobby': ['chess', 'guitar', 'running', 'painting'][i % 4],
                          'favorite_music': ['Rock', 'Pop', 'Jazz'][i % 3]}
                await send(ws, 'player.profile_submit', {'player_id': joined[i]['player']['player_id'],
                    'fields': [{'field_key': k, 'value': v, 'allow_question_usage': True} for k, v in values.items()]})
                await send(ws, 'player.ready')
            await asyncio.gather(*(ready_one(i, ws) for i, ws in enumerate(players)))
            await until(host, 'room.updated', lambda p: p['state'] == 'READY')
            await send(host, 'game.start')
            game = await until(host, 'game.started')
            rounds = game['total_questions']
            for round_index in range(rounds):
                questions = await asyncio.gather(*(until(ws, 'question.started') for ws in sockets))
                question = questions[0]
                assert all(q == question for q in questions)
                assert question['index'] == round_index
                assert 'correct_option_id' not in question
                await asyncio.gather(*(send(ws, 'answer.submit', {'question_id': question['question_id'],
                    'option_id': question['options'][i % len(question['options'])]['option_id']}) for i, ws in enumerate(players)))
                results = await asyncio.gather(*(until(ws, 'question.ended') for ws in sockets))
                assert all(result['statistics']['answered_count'] == player_count for result in results)
                assert sum(o['count'] for o in results[0]['statistics']['answer_distribution']) == player_count
                assert results[0]['player_result'] is None
                await send(host, 'game.next')
                boards = await asyncio.gather(*(until(ws, 'leaderboard.updated') for ws in sockets))
                assert all(board == boards[0] for board in boards)
                await send(host, 'game.next')
            finals = await asyncio.gather(*(until(ws, 'game.finished') for ws in sockets))
            assert all(final == finals[0] for final in finals)
            assert len(finals[0]['leaderboard']['entries']) == player_count
            assert finals[0]['winners']
        finally:
            await asyncio.gather(*(ws.close() for ws in sockets))
    print(f'PASS: 1 host + {player_count} players ({player_count + 1} real WebSockets), {rounds} rounds, connect/answer bursts, identical broadcasts and final results; {time.monotonic() - started:.2f}s')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', help='An already running local backend; otherwise starts an isolated server.')
    args = parser.parse_args()
    if args.url:
        asyncio.run(scenario(args.url))
        return
    with tempfile.TemporaryDirectory(prefix='mizemi-smoke-') as tmp:
        url = 'http://127.0.0.1:8766'
        env = {**os.environ, 'APP_ENV': 'test', 'MIZEMI_ENV': 'test', 'HOST': '127.0.0.1', 'PORT': '8766',
               'MIZEMI_HOST': '127.0.0.1', 'MIZEMI_PORT': '8766',
               'MIZEMI_DATABASE_URL': f'sqlite:///{tmp}/game.db', 'MIZEMI_QUESTIONS_PER_GAME': '3'}
        with open(Path(tmp) / 'server.log', 'w') as log:
            process = subprocess.Popen([sys.executable, '-m', 'app'], cwd=Path(__file__).resolve().parents[1], env=env, stdout=log, stderr=log)
            try:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError('Local smoke server failed to start.')
                    try:
                        if httpx.get(f'{url}/api/v1/health', timeout=.5).status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(.1)
                else:
                    raise RuntimeError('Local smoke server did not become healthy.')
                asyncio.run(scenario(url))
            finally:
                process.terminate()
                process.wait(timeout=30)


if __name__ == '__main__':
    main()
