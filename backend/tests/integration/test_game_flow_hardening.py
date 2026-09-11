"""End-to-end multiplayer game tests over the real REST + WebSocket stack.

One host and several players play complete games: profiles, readiness,
host start, live questions, answers, automatic and timed question closing,
scoring, statistics, leaderboard, progression, and the final result. Also
covers authorization, reconnection, and every answer rejection path.

Tests run the app with ``with TestClient(app)`` so everything shares one
long-lived event loop, exactly as in production (the question timer lives
on that loop). Every receive has a timeout, so a missing event fails the
test instead of hanging it.
"""

import contextlib

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.application.repositories import FinishedGameRecord
from app.domain.game import GameState
from app.infrastructure.repositories import SqlAlchemyGameRepository
from app.infrastructure.settings import Settings
from app.main import create_app
from tests.fixtures.live import (
    HOST_PROTOCOL,
    CreatedRoom,
    JoinedPlayer,
    collect_until,
    create_room,
    distinct_profiles,
    envelope,
    host_ws,
    join,
    player_ws,
    profile_fields,
    receive_json,
    receive_until,
    submit_profile_and_ready,
    wait_for_snapshot,
)

NAMES = ["Dana", "Omer", "Noa"]


def _app(**overrides):
    return create_app(Settings(_env_file=None, database_url="sqlite://", **overrides))


class Table:
    """A host and players connected to one room, with helpers to play."""

    def __init__(self, client: TestClient, app, names=NAMES) -> None:
        self.client = client
        self.app = app
        self.room: CreatedRoom = create_room(client)
        self.players: dict[str, JoinedPlayer] = {
            name: join(client, self.room.room_code, name) for name in names
        }
        self.profiles = distinct_profiles(names)
        self._sessions: list = []
        self.host = None
        self.sockets: dict = {}

    @property
    def game(self):
        return self.app.state.room_registry.get(self.room.room_code).game

    def __enter__(self) -> "Table":
        self.host = self._open(host_ws(self.client, self.room))
        for name, player in self.players.items():
            self.sockets[name] = self._open(player_ws(self.client, self.room.room_code, player))
        return self

    def _open(self, connection):
        session = connection.__enter__()
        self._sessions.append(session)
        return session

    def __exit__(self, *exc) -> None:
        for session in reversed(self._sessions):
            with contextlib.suppress(Exception):
                session.__exit__(None, None, None)

    def ready_everyone(self) -> None:
        for name, player in self.players.items():
            submit_profile_and_ready(self.sockets[name], self.room.game_id, player, **self.profiles[name])
        wait_for_snapshot(self.host, lambda room: room["state"] == "READY")

    def start(self) -> dict:
        self.ready_everyone()
        self.host_send("game.start")
        return receive_until(self.host, "question.started")["payload"]

    def host_send(self, event: str, payload: dict | None = None) -> None:
        self.host.send_json(envelope(event, payload or {}, self.room.game_id))

    def player_send(self, name: str, event: str, payload: dict | None = None) -> None:
        self.sockets[name].send_json(envelope(event, payload or {}, self.room.game_id))

    def answer(self, name: str, *, correct: bool) -> None:
        question = self.game.current_question
        wrong = next(o.option_id for o in question.options if o.option_id != question.correct_option_id)
        option = question.correct_option_id if correct else wrong
        self.player_send(name, "answer.submit", {"question_id": question.question_id, "option_id": option})


class TestCompleteGame:
    def test_host_and_three_players_play_a_full_game(self) -> None:
        app = _app(questions_per_game=2)
        with TestClient(app) as client, Table(client, app) as table:
            table.ready_everyone()

            # --- start ---------------------------------------------------
            table.host_send("game.start")
            assert receive_until(table.host, "game.started")["payload"]["total_questions"] == 2
            for socket in [table.host, *table.sockets.values()]:
                question = receive_until(socket, "question.started")["payload"]
                assert "correct_option_id" not in question
                assert question["index"] == 0

            # --- question 1: two right, one wrong -------------------------
            table.answer("Dana", correct=True)
            accepted = receive_until(table.sockets["Dana"], "answer.accepted")
            assert accepted["payload"]["question_id"] == table.game.current_question.question_id
            table.answer("Omer", correct=True)
            table.answer("Noa", correct=False)

            # The last answer closes the question automatically.
            host_view = receive_until(table.host, "question.ended")["payload"]
            assert host_view["player_result"] is None
            stats = host_view["statistics"]
            assert stats["answered_count"] == 3 and stats["player_count"] == 3
            assert sum(o["count"] for o in stats["answer_distribution"]) == 3
            assert round(sum(o["percentage"] for o in stats["answer_distribution"])) == 100
            assert stats["correct_option_id"] == host_view["correct_option_id"]

            dana_view = receive_until(table.sockets["Dana"], "question.ended")["payload"]
            noa_view = receive_until(table.sockets["Noa"], "question.ended")["payload"]
            assert dana_view["player_result"]["is_correct"] is True
            assert 500 <= dana_view["player_result"]["points_awarded"] <= 1000
            assert dana_view["player_result"]["total_score"] == dana_view["player_result"]["points_awarded"]
            assert noa_view["player_result"]["is_correct"] is False
            assert noa_view["player_result"]["points_awarded"] == 0
            assert noa_view["player_result"]["option_id"] != noa_view["correct_option_id"]
            assert table.game.state is GameState.QUESTION_RESULTS

            # --- leaderboard ----------------------------------------------
            table.host_send("game.next")
            board = receive_until(table.host, "leaderboard.updated")["payload"]["entries"]
            assert board[-1]["display_name"] == "Noa" and board[-1]["total_score"] == 0
            assert board[0]["rank"] == 1

            # --- question 2 ------------------------------------------------
            table.host_send("game.next")
            assert receive_until(table.host, "question.started")["payload"]["index"] == 1
            for name in NAMES:
                table.answer(name, correct=True)
            receive_until(table.host, "question.ended")
            table.host_send("game.next")
            receive_until(table.host, "leaderboard.updated")

            # --- finish ------------------------------------------------------
            table.host_send("game.next")
            finished = receive_until(table.host, "game.finished")["payload"]
            player_final = receive_until(table.sockets["Noa"], "game.finished")["payload"]

        entries = finished["leaderboard"]["entries"]
        assert player_final == finished
        assert len(entries) == 3
        scores = [e["total_score"] for e in entries]
        assert scores == sorted(scores, reverse=True)
        assert finished["winners"] == [e for e in entries if e["rank"] == 1]
        assert table.game.state is GameState.FINISHED
        assert table.game.scores[table.players["Noa"].player_id] > 0

    def test_finished_game_is_persisted(self) -> None:
        app = _app(questions_per_game=1)
        with TestClient(app) as client, Table(client, app) as table:
            table.start()
            for name in NAMES:
                table.answer(name, correct=True)
            receive_until(table.host, "question.ended")
            table.host_send("game.next")
            receive_until(table.host, "leaderboard.updated")
            table.host_send("game.next")
            receive_until(table.host, "game.finished")

            app.state.game_hub.flush_persistence()
            with app.state.database.session_factory() as session:
                record = SqlAlchemyGameRepository(session).get(table.room.game_id)

        assert isinstance(record, FinishedGameRecord)
        assert record.state == "FINISHED"
        assert {p.display_name for p in record.players} == set(NAMES)

    def test_correct_answer_never_reaches_players_before_the_question_ends(self) -> None:
        app = _app(questions_per_game=1)
        with TestClient(app) as client, Table(client, app) as table:
            table.ready_everyone()
            table.host_send("game.start")
            seen = collect_until(table.sockets["Omer"], "question.started")
            table.answer("Dana", correct=True)
            while True:
                message = receive_json(table.sockets["Omer"])
                seen.append(message)
                if message["event"] == "statistics.updated" and message["payload"]["answered_count"] == 1:
                    break

        assert all("correct_option_id" not in str(message) for message in seen)


class TestQuestionClosing:
    def test_question_closes_at_the_deadline_when_nobody_answers(self) -> None:
        app = _app(questions_per_game=1, question_time_limit_seconds=1)
        with TestClient(app) as client, Table(client, app) as table:
            table.start()
            ended = receive_until(table.host, "question.ended")["payload"]
            player_view = receive_until(table.sockets["Dana"], "question.ended")["payload"]

        assert ended["statistics"]["answered_count"] == 0
        assert player_view["player_result"]["option_id"] is None
        assert player_view["player_result"]["points_awarded"] == 0
        assert table.game.state is GameState.QUESTION_RESULTS

    def test_timeout_after_partial_answers_scores_only_the_answers(self) -> None:
        app = _app(questions_per_game=1, question_time_limit_seconds=1)
        with TestClient(app) as client, Table(client, app) as table:
            table.start()
            table.answer("Dana", correct=True)
            ended = receive_until(table.host, "question.ended")["payload"]

        assert ended["statistics"]["answered_count"] == 1
        scores = table.game.scores
        assert scores[table.players["Dana"].player_id] >= 500
        assert scores[table.players["Omer"].player_id] == 0

    def test_final_answer_closes_once_and_disarms_the_timer(self) -> None:
        app = _app(questions_per_game=1)
        with TestClient(app) as client, Table(client, app) as table:
            table.start()
            question_id = table.game.current_question.question_id
            assert app.state.game_hub.has_pending_deadline(table.room.room_code) is True
            for name in NAMES:
                table.answer(name, correct=True)
            receive_until(table.host, "question.ended")
            scores = dict(table.game.scores)
            room = app.state.room_registry.get(table.room.room_code)

            # The deadline path arriving second must find nothing to close.
            closed_again = app.state.game_hub.close_if_active(room, question_id)

        assert closed_again is False
        assert app.state.game_hub.has_pending_deadline(table.room.room_code) is False
        assert table.game.scores == scores


class TestAnswerRejections:
    def _reply(self, table: Table, name: str) -> dict:
        return receive_until(table.sockets[name], "error")["payload"]["error"]

    def test_duplicate_answer_is_rejected(self) -> None:
        app = _app(questions_per_game=2)
        with TestClient(app) as client, Table(client, app) as table:
            table.start()
            table.answer("Dana", correct=True)
            table.answer("Dana", correct=False)
            error = self._reply(table, "Dana")

        assert error["code"] == "ALREADY_ANSWERED"

    def test_answer_for_another_question_is_rejected(self) -> None:
        app = _app(questions_per_game=2)
        with TestClient(app) as client, Table(client, app) as table:
            table.start()
            table.player_send("Dana", "answer.submit", {"question_id": "not-this-one", "option_id": "a"})
            error = self._reply(table, "Dana")

        assert error["code"] == "QUESTION_CLOSED"

    def test_invalid_option_is_rejected(self) -> None:
        app = _app(questions_per_game=2)
        with TestClient(app) as client, Table(client, app) as table:
            question = table.start()
            table.player_send("Dana", "answer.submit", {"question_id": question["question_id"], "option_id": "zz"})
            error = self._reply(table, "Dana")

        assert error["code"] == "VALIDATION_ERROR"

    def test_malformed_answer_payload_is_rejected(self) -> None:
        app = _app(questions_per_game=2)
        with TestClient(app) as client, Table(client, app) as table:
            table.start()
            table.player_send("Dana", "answer.submit", {"option_id": "a", "answered_at": "2020"})
            error = self._reply(table, "Dana")

        assert error["message"] == "The payload is not a valid answer."

    def test_answer_after_the_question_ended_is_rejected(self) -> None:
        app = _app(questions_per_game=2)
        with TestClient(app) as client, Table(client, app) as table:
            question = table.start()
            for name in NAMES:
                table.answer(name, correct=True)
            receive_until(table.sockets["Dana"], "question.ended")
            table.player_send("Dana", "answer.submit", {"question_id": question["question_id"], "option_id": "a"})
            error = self._reply(table, "Dana")

        assert error["code"] == "QUESTION_CLOSED"

    def test_answer_before_the_game_starts_is_rejected(self) -> None:
        client = TestClient(create_app())
        room = create_room(client)
        dana = join(client, room.room_code, "Dana")

        with player_ws(client, room.room_code, dana) as ws:
            ws.send_json(envelope("answer.submit", {"question_id": "q", "option_id": "a"}, room.game_id))
            reply = receive_until(ws, "error")

        assert reply["payload"]["error"]["code"] == "QUESTION_CLOSED"


class TestAuthorization:
    def test_players_cannot_run_host_commands(self) -> None:
        app = _app(questions_per_game=1)
        with TestClient(app) as client, Table(client, app) as table:
            table.ready_everyone()
            codes = []
            for event, payload in (
                ("game.start", {}),
                ("game.next", {}),
                ("player.remove", {"player_id": table.players["Omer"].player_id}),
            ):
                table.player_send("Dana", event, payload)
                codes.append(receive_until(table.sockets["Dana"], "error")["payload"]["error"]["code"])

        assert codes == ["NOT_HOST", "NOT_HOST", "NOT_HOST"]
        assert table.game.state is GameState.READY
        assert len(table.game.players) == 3

    def test_host_cannot_act_as_a_player(self) -> None:
        client = TestClient(create_app())
        room = create_room(client)
        join(client, room.room_code, "Dana")

        with host_ws(client, room) as ws:
            ws.send_json(envelope("answer.submit", {"question_id": "q", "option_id": "a"}, room.game_id))
            reply = receive_until(ws, "error")

        assert reply["payload"]["error"]["message"] == "This action is only available to players."

    @pytest.mark.parametrize("token_kind", ["wrong", "player", "missing"])
    def test_host_socket_requires_the_host_token(self, token_kind: str) -> None:
        client = TestClient(create_app())
        room = create_room(client)
        dana = join(client, room.room_code, "Dana")
        protocols = {
            "wrong": [HOST_PROTOCOL, "not-the-token"],
            "player": [HOST_PROTOCOL, dana.player_token],
            "missing": [HOST_PROTOCOL],
        }[token_kind]

        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f"/ws/rooms/{room.room_code}/host", subprotocols=protocols):
                pytest.fail("session must not be established")  # pragma: no cover

    def test_host_token_of_another_room_is_rejected(self) -> None:
        client = TestClient(create_app())
        room_a = create_room(client)
        room_b = create_room(client)

        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                f"/ws/rooms/{room_b.room_code}/host", subprotocols=[HOST_PROTOCOL, room_a.host_token]
            ):
                pytest.fail("session must not be established")  # pragma: no cover


class TestHostCommands:
    def test_start_before_everyone_is_ready_is_rejected(self) -> None:
        client = TestClient(create_app())
        room = create_room(client)
        join(client, room.room_code, "Dana")

        with host_ws(client, room) as ws:
            ws.send_json(envelope("game.start", {}, room.game_id))
            reply = receive_until(ws, "error")

        assert reply["payload"]["error"]["code"] == "INVALID_STATE_TRANSITION"

    def test_start_with_no_usable_profile_data_is_rejected_safely(self) -> None:
        app = _app()
        with TestClient(app) as client, Table(client, app, names=["Dana", "Omer"]) as table:
            for name, player in table.players.items():
                fields = [dict(field, allow_question_usage=False) for field in profile_fields()]
                table.player_send(name, "player.profile_submit", {"player_id": player.player_id, "fields": fields})
                table.player_send(name, "player.ready")
            wait_for_snapshot(table.host, lambda room: room["state"] == "READY")
            table.host_send("game.start")
            reply = receive_until(table.host, "error")

        assert reply["payload"]["error"]["code"] == "NO_QUESTIONS_AVAILABLE"
        assert table.game.state is GameState.READY

    def test_next_during_an_active_question_is_rejected(self) -> None:
        app = _app(questions_per_game=1)
        with TestClient(app) as client, Table(client, app) as table:
            table.start()
            table.host_send("game.next")
            reply = receive_until(table.host, "error")

        assert reply["payload"]["error"]["code"] == "INVALID_STATE_TRANSITION"
        assert table.game.state is GameState.QUESTION_ACTIVE

    def test_host_commands_require_an_empty_payload(self) -> None:
        client = TestClient(create_app())
        room = create_room(client)

        with host_ws(client, room) as ws:
            ws.send_json(envelope("game.start", {"questions": 99}, room.game_id))
            reply = receive_until(ws, "error")

        assert reply["payload"]["error"]["message"] == "The game.start payload must be exactly empty."

    def test_host_can_remove_a_player_before_the_game(self) -> None:
        app = _app()
        with TestClient(app) as client, Table(client, app) as table:
            omer = table.players["Omer"]
            table.host_send("player.remove", {"player_id": omer.player_id})

            def without_omer(room: dict) -> bool:
                return omer.player_id not in [p["player_id"] for p in room["players"]]

            wait_for_snapshot(table.sockets["Omer"], without_omer)
            with pytest.raises(WebSocketDisconnect):
                for _ in range(20):
                    receive_json(table.sockets["Omer"])
            snapshot = wait_for_snapshot(table.host, without_omer)

        assert [p["display_name"] for p in snapshot["payload"]["players"]] == ["Dana", "Noa"]
        assert table.game.get_player(omer.player_id) is None
        assert not app.state.credentials.verify_player(table.room.room_code, omer.player_id, omer.player_token)

    def test_removing_the_last_unready_player_makes_the_room_ready(self) -> None:
        app = _app()
        with TestClient(app) as client, Table(client, app) as table:
            for name in ("Dana", "Omer"):
                submit_profile_and_ready(table.sockets[name], table.room.game_id, table.players[name], **table.profiles[name])
            table.host_send("player.remove", {"player_id": table.players["Noa"].player_id})
            snapshot = wait_for_snapshot(table.host, lambda room: room["state"] == "READY")

        assert len(snapshot["payload"]["players"]) == 2


class TestReconnection:
    def test_player_reconnecting_mid_question_gets_the_same_question_back(self) -> None:
        app = _app(questions_per_game=1)
        with TestClient(app) as client, Table(client, app) as table:
            table.ready_everyone()
            table.host_send("game.start")
            original = receive_until(table.sockets["Dana"], "question.started")["payload"]
            table.answer("Dana", correct=True)
            receive_until(table.sockets["Dana"], "answer.accepted")

            with player_ws(client, table.room.room_code, table.players["Dana"]) as again:
                messages = collect_until(again, "answer.accepted")

        assert messages[0]["event"] == "room.updated"
        replayed = next(m for m in messages if m["event"] == "question.started")["payload"]
        assert replayed["question_id"] == original["question_id"]
        assert replayed["started_at"] == original["started_at"]

    def test_host_reconnecting_at_the_leaderboard_gets_it_back(self) -> None:
        app = _app(questions_per_game=2)
        with TestClient(app) as client, Table(client, app) as table:
            table.start()
            for name in NAMES:
                table.answer(name, correct=True)
            receive_until(table.host, "question.ended")
            table.host_send("game.next")
            receive_until(table.host, "leaderboard.updated")

            with host_ws(client, table.room) as again:
                board = receive_until(again, "leaderboard.updated")

        assert len(board["payload"]["entries"]) == 3
