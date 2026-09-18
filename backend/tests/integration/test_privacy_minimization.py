"""Factual privacy promises: no raw profile snapshots; bounded, safe cleanup."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.domain.game import GameState
from app.infrastructure.database.models import GameRow, PlayerRow, ProfileFieldRow
from app.infrastructure.repositories import SqlAlchemyGameRepository
from app.infrastructure.repositories.game_repository import LEGACY_PROFILE_BATCH_LIMIT
from app.infrastructure.settings import Settings
from app.main import create_app
from tests.fixtures.factories import make_game, make_profile, make_profile_field, ready_all, play_to_finished, start_game


def test_finish_discards_profiles_but_preserves_result_and_reconnect_data(db_session):
    game = make_game("private-game")
    for player in game.players:
        allowed = make_profile(player.player_id).fields
        private = make_profile_field("personal_fact", "DISABLED_PRIVATE_SENTINEL", allow_question_usage=False)
        game.submit_initial_profile(player.player_id, make_profile(player.player_id, fields=(*allowed, private)))
    ready_all(game)
    original = tuple(player.profile for player in game.players)
    start_game(game, question_count=2)
    assert tuple(player.profile for player in game.players) == original
    questions = game.questions
    play_to_finished(game)
    assert game.state is GameState.FINISHED
    assert all(p.has_profile and p.profile.fields == () for p in game.players)
    assert game.questions == questions
    assert "DISABLED_PRIVATE_SENTINEL" not in repr(questions)
    repo = SqlAlchemyGameRepository(db_session)
    repo.save(game)
    db_session.commit()
    record = repo.get(game.game_id)
    assert [p.display_name for p in record.players] == [p.display_name for p in game.players]
    assert all(p.has_profile and not p.profile_fields for p in record.players)
    assert {s.player_id: s.total_score for s in record.scores} == game.scores
    assert len(record.questions) == 2
    assert "DISABLED_PRIVATE_SENTINEL" not in repr(record)
    assert db_session.scalar(select(func.count()).select_from(ProfileFieldRow)) == 0


def add_legacy(session, game_id, state, count, when):
    game = GameRow(game_id=game_id, state=state, updated_at=when, created_at=when)
    player = PlayerRow(player_id=f"{game_id}-player", position=0, display_name="Synthetic",
                       connected=False, is_ready=True, has_profile=True)
    player.profile_fields = [ProfileFieldRow(position=i, field_key="personal_fact",
                            value="synthetic-private-marker", value_type="str",
                            allow_question_usage=bool(i % 2)) for i in range(count)]
    game.players = [player]
    session.add(game)
    session.commit()


def test_legacy_cleanup_is_bounded_preserves_active_games_and_retention_clock(db_session):
    when = datetime.now(UTC) - timedelta(days=1)
    add_legacy(db_session, "a-finished", "FINISHED", LEGACY_PROFILE_BATCH_LIMIT + 1, when)
    add_legacy(db_session, "b-active", "READY", 2, when)
    repo = SqlAlchemyGameRepository(db_session)
    assert repo.delete_legacy_finished_profiles() == LEGACY_PROFILE_BATCH_LIMIT
    db_session.commit()
    assert repo.delete_legacy_finished_profiles() == 1
    db_session.commit()
    assert repo.delete_legacy_finished_profiles() == 0
    db_session.expire_all()
    assert db_session.get(GameRow, "a-finished").updated_at == when
    assert len(repo.get("a-finished").players) == 1
    assert len(repo.get("b-active").players[0].profile_fields) == 2


def test_legacy_cleanup_rollback_does_not_half_delete_records(db_session):
    add_legacy(db_session, "rollback", "FINISHED", 3, datetime.now(UTC))
    repo = SqlAlchemyGameRepository(db_session)
    assert repo.delete_legacy_finished_profiles() == 3
    db_session.rollback()
    assert len(repo.get("rollback").players[0].profile_fields) == 3


@pytest.mark.parametrize("days,minutes", [(7, 120), (3, 15)])
def test_privacy_info_discloses_actual_configuration_only(days, minutes):
    app = create_app(Settings(database_url="sqlite://", retention_days=days,
                              room_idle_ttl_minutes=minutes, _env_file=None))
    with TestClient(app) as client:
        response = client.get("/api/v1/privacy-info")
        assert response.status_code == 200
        assert response.json() == {
            "policy_version": "2026-09-18", "retention_days": days,
            "room_idle_ttl_minutes": minutes, "maintenance_interval_seconds": 300,
            "raw_profiles_persisted": False,
        }
        assert response.headers["cache-control"] == "no-store"


def test_maintenance_removes_legacy_profiles_without_waiting_for_expiry():
    app = create_app(Settings(database_url="sqlite://", _env_file=None))
    database = app.state.database
    try:
        database.ensure_schema()
        with database.session_factory() as session:
            add_legacy(session, "legacy", "FINISHED", 2, datetime.now(UTC))
        assert database.purge_expired(timedelta(days=7)) == 0
        with database.session_factory() as session:
            record = SqlAlchemyGameRepository(session).get("legacy")
            assert record is not None and not record.players[0].profile_fields
    finally:
        app.state.game_hub.shutdown()
        database.engine.dispose()
