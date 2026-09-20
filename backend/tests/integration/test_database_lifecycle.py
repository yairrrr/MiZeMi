"""Deterministic reproduction of the CI cleanup/connection-close race."""
import asyncio
import os
import threading
from uuid import uuid4

import pytest

from app.main import create_app
from app.infrastructure.settings import Settings


@pytest.fixture(params=['sqlite-memory', 'sqlite-file', 'postgres'])
def lifecycle_app(request, tmp_path):
    """Exercise native connections, with a disposable schema for PostgreSQL."""
    from sqlalchemy.schema import CreateSchema, DropSchema
    from app.infrastructure.database import create_database_engine, create_session_factory

    if request.param == 'postgres' and not os.environ.get('MIZEMI_TEST_POSTGRES_URL'):
        pytest.skip('Set MIZEMI_TEST_POSTGRES_URL for a disposable PostgreSQL database')
    url = f'sqlite:///{tmp_path / "lifecycle.db"}' if request.param == 'sqlite-file' else 'sqlite://'
    app = create_app(Settings(database_url=url, _env_file=None))
    parent, schema = None, None
    try:
        if request.param == 'postgres':
            parent = create_database_engine(os.environ['MIZEMI_TEST_POSTGRES_URL'])
            schema = f'mizemi_lifecycle_{uuid4().hex}'
            with parent.begin() as connection:
                connection.execute(CreateSchema(schema))
            scoped = parent.execution_options(schema_translate_map={None: schema})
            app.state.database.engine.dispose()
            app.state.database.engine = scoped
            app.state.database.session_factory = create_session_factory(scoped)
        yield app
    finally:
        app.state.game_hub.shutdown()
        app.state.database.engine.dispose()
        if parent is not None:
            try:
                with parent.begin() as connection:
                    connection.execute(DropSchema(schema, cascade=True))
            finally:
                parent.dispose()


def test_shutdown_joins_live_retention_and_queued_persistence(lifecycle_app, monkeypatch):
    """Hold a real checked-out connection while shutdown and two writes start."""
    from sqlalchemy import event
    from app.infrastructure.repositories import SqlAlchemyGameRepository
    from tests.integration.test_game_repository import _finished_game

    app = lifecycle_app
    database, hub = app.state.database, app.state.game_hub
    entered, release, retained, saving = (threading.Event() for _ in range(4))
    order = []
    purge, save, dispose = database.purge_expired, database.save_finished_game, database.engine.dispose
    game = _finished_game('shutdown-game', question_count=1)

    def before_query(connection, cursor, statement, parameters, context, executemany):
        # PostgreSQL also SELECTs its catalog during startup. Pause the actual
        # retention query only, after the application has initialized.
        if statement.lstrip().upper().startswith('SELECT') and 'games.game_id' in statement and not entered.is_set():
            entered.set()
            assert release.wait(5), 'test must release the checked-out connection'

    def observed_purge(retention):
        result = purge(retention)
        retained.set()
        return result

    def observed_save(finished_game):
        saving.set()
        save(finished_game)
        order.append('committed')

    def observed_dispose(*args, **kwargs):
        assert retained.is_set(), 'engine disposed while retention still owned a connection'
        assert order == ['committed', 'committed'], 'queued persistence was not joined'
        assert not any(t.name.startswith('mizemi-persist') for t in threading.enumerate())
        with database.session_factory() as session:
            assert SqlAlchemyGameRepository(session).get(game.game_id).state == 'FINISHED'
        order.append('disposed')
        return dispose(*args, **kwargs)

    monkeypatch.setattr(database, 'purge_expired', observed_purge)
    # GameHub captured the bound method at construction.
    monkeypatch.setattr(hub, '_persist', observed_save)
    event.listen(database.engine, 'before_cursor_execute', before_query)

    async def check():
        async with app.router.lifespan_context(app):
            assert await asyncio.to_thread(entered.wait, 5)
            hub._persist_finished(game)
            hub._persist_finished(game)
            assert await asyncio.to_thread(saving.wait, 5)

            async def release_after_shutdown_starts():
                await asyncio.sleep(0.1)
                assert order == []
                release.set()

            releaser = asyncio.create_task(release_after_shutdown_starts())
        await releaser
        assert order == ['committed', 'committed', 'disposed']

    try:
        with monkeypatch.context() as patch:
            patch.setattr(database.engine, 'dispose', observed_dispose)
            asyncio.run(check())
    finally:
        release.set()
        event.remove(database.engine, 'before_cursor_execute', before_query)


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
