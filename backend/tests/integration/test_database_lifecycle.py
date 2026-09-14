"""Deterministic reproduction of the CI cleanup/connection-close race."""
import asyncio
import threading

import pytest

from app.main import create_app
from app.infrastructure.settings import Settings


@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_shutdown_waits_for_running_retention_before_disposing(monkeypatch, cleanup_fails):
    app = create_app(Settings(database_url="sqlite://", _env_file=None))
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    order = []
    database = app.state.database
    dispose = database.engine.dispose

    def cleanup(_):
        entered.set()
        try:
            assert release.wait(5), "test did not release retention worker"
            order.append("cleanup finished")
            if cleanup_fails:
                raise RuntimeError("synthetic retention failure")
        finally:
            finished.set()

    def observed_dispose(*args, **kwargs):
        order.append("dispose")
        dispose(*args, **kwargs)

    monkeypatch.setattr(database, "purge_expired", cleanup)
    monkeypatch.setattr(database.engine, "dispose", observed_dispose)

    async def check():
        async def release_worker():
            await asyncio.sleep(0.1)
            release.set()

        try:
            async with app.router.lifespan_context(app):
                assert await asyncio.to_thread(entered.wait, 5)
                releaser = asyncio.create_task(release_worker())
            await releaser
        finally:
            release.set()
            assert await asyncio.to_thread(finished.wait, 5)
        assert order == ["cleanup finished", "dispose"]

    asyncio.run(check())


def test_save_and_retention_do_not_share_a_native_transaction(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from datetime import timedelta
    from app.main import _Database
    from app.infrastructure.repositories import SqlAlchemyGameRepository
    database = _Database('sqlite://')
    entered, release, cleanup = threading.Event(), threading.Event(), threading.Event()
    overlap = []
    def save(self, game):
        entered.set()
        assert release.wait(5)
    def purge(self, cutoff):
        overlap.append(not release.is_set())
        cleanup.set()
        return 0
    monkeypatch.setattr(SqlAlchemyGameRepository, 'save', save)
    monkeypatch.setattr(SqlAlchemyGameRepository, 'delete_older_than', purge)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            saving = pool.submit(database.save_finished_game, None)
            assert entered.wait(5)
            purging = pool.submit(database.purge_expired, timedelta(days=7))
            try:
                assert not cleanup.wait(0.1)
            finally:
                release.set()
            saving.result(timeout=5)
            purging.result(timeout=5)
        assert overlap == [False]
    finally:
        release.set()
        database.engine.dispose()


def test_failed_database_startup_returns_only_safe_error(monkeypatch):
    app = create_app(Settings(database_url='sqlite://', _env_file=None))
    def fail():
        raise RuntimeError('private-profile-marker internal-db-marker')
    monkeypatch.setattr(app.state.database, 'ensure_schema', fail)
    async def check():
        with pytest.raises(RuntimeError) as error:
            async with app.router.lifespan_context(app):
                pytest.fail('startup must stop')
        assert 'private-profile-marker' not in str(error.value)
        assert 'internal-db-marker' not in str(error.value)
    try:
        asyncio.run(check())
    finally:
        app.state.game_hub.shutdown()
        app.state.database.engine.dispose()


def test_unavailable_postgres_fails_startup_without_connection_details():
    # An unused loopback port: never resolve or connect to production.
    import socket
    with socket.socket() as closed_port:
        closed_port.bind(('127.0.0.1', 0))
        port = closed_port.getsockname()[1]
        app = create_app(Settings(database_url=f'postgresql://postgres@127.0.0.1:{port}/audit', _env_file=None))
        async def check():
            with pytest.raises(RuntimeError) as error:
                async with app.router.lifespan_context(app):
                    pytest.fail('unavailable database must prevent startup')
            message = str(error.value)
            assert '127.0.0.1' not in message and str(port) not in message
            assert 'sqlalchemy' not in message and 'psycopg' not in message
        try:
            asyncio.run(check())
        finally:
            app.state.game_hub.shutdown()
            app.state.database.engine.dispose()
