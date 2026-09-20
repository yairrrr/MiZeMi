"""Integration tests for SqlAlchemyGameRepository (MASTER_SPEC.md §15).

Exercises a real SQLite database through the ``db_session`` fixture: save a
game aggregate, read it back as a FinishedGameRecord, and confirm the round
trip preserves result data while discarding raw profile values.
"""

import pytest
from sqlalchemy import func, select

from app.application.repositories import FinishedGameRecord
from app.domain.game import GameState
from app.infrastructure.database.models import GameRow, PlayerRow, ProfileFieldRow
from app.infrastructure.repositories import SqlAlchemyGameRepository
from tests.fixtures.factories import (
    make_game,
    make_player,
    make_profile,
    make_profile_field,
    make_question,
    make_ready_game,
    play_to_finished,
    start_game,
)


@pytest.fixture
def repo(db_session) -> SqlAlchemyGameRepository:
    return SqlAlchemyGameRepository(db_session)


def _finished_game(game_id: str = "g1", *, question_count: int = 3):
    game = make_ready_game(game_id)
    start_game(game, question_count=question_count)
    play_to_finished(game)
    assert game.state is GameState.FINISHED
    return game


class TestRoundTrip:
    def test_saves_and_reads_back_a_finished_game(self, repo, db_session) -> None:
        game = _finished_game()

        repo.save(game)
        db_session.commit()
        record = repo.get("g1")

        assert isinstance(record, FinishedGameRecord)
        assert record.game_id == "g1"
        assert record.state == "FINISHED"
        assert record.current_question_index is None
        assert len(record.players) == 3
        assert len(record.questions) == 3

    def test_preserves_player_order_without_persisting_raw_profiles(self, repo, db_session) -> None:
        players = [
            make_player("p1", "Dana", profile=make_profile("p1")),
            make_player(
                "p2",
                "Omer",
                profile=make_profile(
                    "p2",
                    fields=[
                        make_profile_field("age", 31),
                        make_profile_field(
                            "personal_fact", "was a lifeguard", allow_question_usage=False
                        ),
                    ],
                ),
            ),
        ]
        game = make_game("g2", players=players)

        repo.save(game)
        db_session.commit()
        record = repo.get("g2")

        assert [p.player_id for p in record.players] == ["p1", "p2"]
        omer = record.players[1]
        assert omer.has_profile is True
        assert omer.profile_fields == ()
        assert db_session.scalar(select(func.count()).select_from(ProfileFieldRow)) == 0
        # Persistence minimization does not change active in-memory profiles.
        assert players[1].profile.fields[1].value == "was a lifeguard"

    def test_preserves_question_options_and_correct_id(self, repo, db_session) -> None:
        game = make_ready_game("g3")
        start_game(
            game,
            questions=(
                make_question(
                    "qX", option_ids=("a", "b", "c"), correct_option_id="c", index=0, total_questions=1
                ),
            ),
        )
        play_to_finished(game)

        repo.save(game)
        db_session.commit()
        question = repo.get("g3").questions[0]

        assert question.question_id == "qX"
        assert [o.option_id for o in question.options] == ["a", "b", "c"]
        assert question.correct_option_id == "c"
        assert question.question_type == "multiple_choice"

    def test_player_without_a_profile_round_trips_as_no_profile(
        self, repo, db_session
    ) -> None:
        game = make_game("g4", players=[make_player("p1", "Dana")])

        repo.save(game)
        db_session.commit()
        player = repo.get("g4").players[0]

        assert player.has_profile is False
        assert player.profile_fields == ()

    def test_stores_a_non_finished_game_faithfully(self, repo, db_session) -> None:
        game = make_ready_game("g5")

        repo.save(game)
        db_session.commit()

        assert repo.get("g5").state == "READY"


class TestGetAndDelete:
    def test_get_unknown_game_returns_none(self, repo) -> None:
        assert repo.get("nope") is None

    def test_delete_removes_the_game_and_children(self, repo, db_session) -> None:
        repo.save(_finished_game("g6"))
        db_session.commit()

        repo.delete("g6")
        db_session.commit()

        assert repo.get("g6") is None
        assert db_session.execute(select(func.count()).select_from(PlayerRow)).scalar_one() == 0
        assert (
            db_session.execute(select(func.count()).select_from(ProfileFieldRow)).scalar_one()
            == 0
        )

    def test_delete_missing_game_is_a_no_op(self, repo, db_session) -> None:
        repo.delete("never-existed")  # must not raise
        db_session.commit()


class TestUpsert:
    def test_saving_twice_does_not_duplicate_rows(self, repo, db_session) -> None:
        game = _finished_game("g7")

        repo.save(game)
        db_session.commit()
        repo.save(game)
        db_session.commit()

        games = db_session.execute(select(func.count()).select_from(GameRow)).scalar_one()
        players = db_session.execute(
            select(func.count()).select_from(PlayerRow)
        ).scalar_one()
        assert games == 1
        assert players == 3

    def test_re_save_reflects_a_changed_state(self, repo, db_session) -> None:
        game = make_ready_game("g8")
        repo.save(game)
        db_session.commit()

        start_game(game)
        play_to_finished(game)
        repo.save(game)
        db_session.commit()

        assert repo.get("g8").state == "FINISHED"
