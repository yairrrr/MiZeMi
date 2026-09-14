"""Concurrent WebSocket upgrades must honor limits before accept yields."""
import asyncio
from types import SimpleNamespace

import pytest

from app.realtime.host_connection import host_websocket
from app.realtime.player_connection import player_websocket
from tests.integration.test_game_flow_hardening import _app


@pytest.mark.parametrize('role', ['host', 'player'])
def test_simultaneous_upgrades_cannot_bypass_socket_cap(role):
    app = _app()
    hub = app.state.game_hub
    hosted = hub.create_room()
    code = hosted.room.room_code
    joined = hub.join(code, 'Dana')
    token = hosted.host_token if role == 'host' else joined.player_token

    async def check():
        accepting, disconnect = asyncio.Event(), asyncio.Event()
        class Socket:
            def __init__(self):
                self.app = app
                self.headers = {}
                self.scope = {'subprotocols': ['mizemi.' + role, token]}
                self.closed = None
            async def accept(self, **kwargs):
                await accepting.wait()
            async def receive(self):
                await disconnect.wait()
                return {'type': 'websocket.disconnect'}
            async def send_json(self, data):
                pass
            async def close(self, code):
                self.closed = code

        sockets = [Socket() for _ in range(8)]
        tasks = [asyncio.create_task(host_websocket(s, code) if role == 'host' else player_websocket(s, code, joined.player.player_id)) for s in sockets]
        try:
            # Every upgrade reaches accept while no accepted handle exists.
            await asyncio.sleep(0.05)
            accepting.set()
            await asyncio.sleep(0.05)
            count = len(app.state.room_connections.handles_for(code))
        finally:
            accepting.set()
            disconnect.set()
            await asyncio.gather(*tasks)
        assert count == 4
        assert sum(s.closed == 4429 for s in sockets) == 4
        assert not app.state.room_connections.handles_for(code)
    try:
        asyncio.run(check())
    finally:
        hub.shutdown()
        app.state.database.engine.dispose()


@pytest.mark.parametrize('role', ['host', 'player'])
def test_failed_handshake_releases_reserved_slot(role):
    app = _app()
    hub = app.state.game_hub
    hosted = hub.create_room()
    code = hosted.room.room_code
    joined = hub.join(code, 'Dana')
    token = hosted.host_token if role == 'host' else joined.player_token
    class Socket:
        def __init__(self):
            self.app = app
            self.headers = {}
            self.scope = {'subprotocols': ['mizemi.' + role, token]}
        async def accept(self, **kwargs):
            raise RuntimeError('synthetic failed upgrade')
    async def check():
        for _ in range(5):
            with pytest.raises(RuntimeError, match='synthetic failed upgrade'):
                if role == 'host':
                    await host_websocket(Socket(), code)
                else:
                    await player_websocket(Socket(), code, joined.player.player_id)
        assert not app.state.room_connections._slots
    try:
        asyncio.run(check())
    finally:
        hub.shutdown()
        app.state.database.engine.dispose()
