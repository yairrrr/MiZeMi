"""PostgreSQL DDL and opt-in real PostgreSQL transaction/game verification.

MIZEMI_TEST_POSTGRES_URL must point to a disposable test database whose role
can create schemas. Every run uses and removes its own isolated schema.
"""
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_mock_engine, func, select
from sqlalchemy.schema import CreateSchema, DropSchema

from app.infrastructure.database import Base, create_database_engine, create_session_factory
from app.infrastructure.repositories import SqlAlchemyGameRepository
from tests.integration.test_game_flow_hardening import Table, _app, NAMES
from tests.fixtures.live import receive_until


def test_all_tables_compile_for_postgres():
    statements = []
    engine = create_mock_engine('postgresql+psycopg://', lambda sql, *a, **kw: statements.append(str(sql.compile(dialect=engine.dialect))))
    Base.metadata.create_all(engine)
    assert len(statements) == 10
    assert any('TIMESTAMP WITH TIME ZONE' in sql for sql in statements)
    assert any('CREATE TABLE answers' in sql for sql in statements)
    assert any('CREATE TABLE scores' in sql for sql in statements)


@pytest.mark.skipif(not os.environ.get('MIZEMI_TEST_POSTGRES_URL'), reason='Set MIZEMI_TEST_POSTGRES_URL for a disposable PostgreSQL database')
@pytest.mark.parametrize("language", ["en", "he"])
def test_real_postgres_game_persistence_rollback_and_retention(language):
    engine = create_database_engine(os.environ['MIZEMI_TEST_POSTGRES_URL'])
    schema = f'mizemi_test_{uuid4().hex}'
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    scoped = engine.execution_options(schema_translate_map={None: schema})
    app = _app(questions_per_game=1)
    app.state.database.engine.dispose()
    app.state.database.engine = scoped
    app.state.database.session_factory = create_session_factory(scoped)
    try:
        with TestClient(app) as client, Table(client, app, config={"question_count":1,"language":language}) as table:
            # Startup creates all ten tables in the isolated schema.
            table.start()
            for name in NAMES:
                table.answer(name, correct=(name == 'Dana'))
            receive_until(table.host, 'question.ended')
            table.host_send('game.next')
            receive_until(table.host, 'leaderboard.updated')
            table.host_send('game.next')
            receive_until(table.host, 'game.finished')
            app.state.game_hub.flush_persistence()
            factory = app.state.database.session_factory
            with factory() as session:
                repository = SqlAlchemyGameRepository(session)
                record = repository.get(table.game.game_id)
                assert record.state == 'FINISHED'
                assert record.config.question_count == 1
                assert record.config.language == language
                assert record.questions[0].language == language
                assert record.questions[0].explanation == table.game.questions[0].explanation
                assert record.questions[0].knowledge_version == table.game.questions[0].knowledge_version
                assert record.questions[0].source_rule_id
                assert record.questions[0].difficulty == table.game.questions[0].difficulty.value
                assert {s.player_id: s.total_score for s in record.scores} == table.game.scores
                assert len(record.answers) == 3
                assert all(a.answered_at.tzinfo is not None for a in record.answers)
                repository.delete(table.game.game_id)
                session.rollback()
            with factory() as session:
                repository = SqlAlchemyGameRepository(session)
                assert repository.get(table.game.game_id) is not None
                # An upsert replaces the whole aggregate without duplicate rows.
                repository.save(table.game)
                session.commit()
                assert len(repository.get(table.game.game_id).answers) == 3
                assert repository.delete_older_than(datetime.now(UTC) + timedelta(days=1)) == 1
                session.commit()
                for model in Base.metadata.sorted_tables:
                    assert session.scalar(select(func.count()).select_from(model)) == 0
    finally:
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        engine.dispose()
