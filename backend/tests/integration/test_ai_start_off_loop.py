"""AI-mode start must never block the event loop (MASTER_SPEC.md §12.7).

Generating questions with an AI is a long blocking network call. If it ran on
the event loop it would freeze every room and drop sockets at the ping
timeout. These tests drive the real realtime stack with a fake, controllable
generator and prove: the server keeps answering meanwhile, a double start is
refused, a room that changed meanwhile is not started with stale questions,
and any AI failure falls back to the algorithmic engine.
"""

from __future__ import annotations

import threading
import time

from fastapi.testclient import TestClient

from app.domain.questions.question import Difficulty, Question, QuestionOption, QuestionType
from app.infrastructure.ai_client import AIGenerationError
from tests.fixtures.live import join, receive_until, submit_profile_and_ready
from tests.integration.test_game_flow_hardening import Table, _app

AI_TEXT = "Which city do most of you live in?"
AI_CONFIG = {"question_count": 3, "language": "en", "question_source": "ai"}


class FakeAIGenerator:
    """Stands in for AIQuestionGenerator; blocks until the test releases it."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.started = threading.Event()
        self.release = threading.Event()
        self.calls = 0

    def generate(self, dataset, *, question_count, time_limit_seconds, seed, language=None):
        self.calls += 1
        self.started.set()
        self.release.wait(10)
        if self.fail:
            raise AIGenerationError("boom")
        return (
            Question(
                question_id="ai-q1", index=0, total_questions=1,
                question_type=QuestionType.MULTIPLE_CHOICE, text=AI_TEXT,
                options=(QuestionOption("a", "Haifa"), QuestionOption("b", "Eilat")),
                correct_option_id="a", time_limit_seconds=time_limit_seconds,
                difficulty=Difficulty.EASY, language="en",
                source_rule_id="ai_group_insight", explanation="", knowledge_version="ai",
            ),
        )


def _enable_ai(app, fake: FakeAIGenerator) -> None:
    # Wire the fake exactly where main.py wires the real generator.
    hub = app.state.game_hub
    hub._gameplay._ai_generator = fake
    hub._ai_available = True


def _start_and_wait_until_generating(table: Table, fake: FakeAIGenerator) -> None:
    table.ready_everyone()
    table.host_send("game.start")
    assert fake.started.wait(5), "the AI generator was never called"


def test_server_keeps_serving_while_the_ai_is_generating():
    app = _app()
    fake = FakeAIGenerator()
    _enable_ai(app, fake)
    with TestClient(app) as client, Table(client, app, config=AI_CONFIG) as table:
        _start_and_wait_until_generating(table, fake)
        # Safety net: if the loop were blocked, this release would only fire
        # after the request, and the elapsed time below would expose it.
        safety = threading.Timer(4, fake.release.set)
        safety.start()
        try:
            began = time.monotonic()
            assert client.get("/api/v1/health").status_code == 200
            elapsed = time.monotonic() - began
        finally:
            safety.cancel()
        assert elapsed < 2, f"the event loop was blocked for {elapsed:.1f}s"

        fake.release.set()
        question = receive_until(table.host, "question.started")["payload"]
        assert question["text"] == AI_TEXT
        assert table.game.questions[0].source_rule_id == "ai_group_insight"


def test_a_second_start_while_generating_is_refused():
    app = _app()
    fake = FakeAIGenerator()
    _enable_ai(app, fake)
    with TestClient(app) as client, Table(client, app, config=AI_CONFIG) as table:
        _start_and_wait_until_generating(table, fake)
        table.host_send("game.start")
        error = receive_until(table.host, "error")["payload"]["error"]
        assert error["code"] == "INVALID_STATE_TRANSITION"
        assert "already being prepared" in error["message"]

        fake.release.set()
        receive_until(table.host, "question.started")
        assert fake.calls == 1  # the refused click never reached the AI


def test_a_room_that_changed_meanwhile_is_not_started_with_stale_questions():
    app = _app()
    fake = FakeAIGenerator()
    _enable_ai(app, fake)
    with TestClient(app) as client, Table(client, app, config=AI_CONFIG) as table:
        _start_and_wait_until_generating(table, fake)
        join(client, table.room.room_code, "Latecomer")  # READY -> PROFILE_COLLECTION
        fake.release.set()

        error = receive_until(table.host, "error")["payload"]["error"]
        assert error["code"] == "INVALID_STATE_TRANSITION"
        assert table.game.state.value == "PROFILE_COLLECTION"
        assert table.game.questions == ()


def test_the_host_can_start_again_after_a_changed_room():
    app = _app()
    fake = FakeAIGenerator()
    _enable_ai(app, fake)
    with TestClient(app) as client, Table(client, app, config=AI_CONFIG) as table:
        _start_and_wait_until_generating(table, fake)
        late = join(client, table.room.room_code, "Latecomer")
        fake.release.set()
        receive_until(table.host, "error")

        # The newcomer completes a profile; the room is READY again.
        with client.websocket_connect(
            f"/ws/rooms/{table.room.room_code}?player_id={late.player_id}",
            subprotocols=["mizemi.player", late.player_token],
        ) as ws:
            submit_profile_and_ready(
                ws, table.room.game_id, late,
                city="Haifa", favorite_food="pizza", hobby="chess", favorite_music="Rock",
            )
            for _ in range(80):
                if receive_until(table.host, "room.updated")["payload"]["state"] == "READY":
                    break
            table.host_send("game.start")
            receive_until(table.host, "question.started")


def test_an_ai_failure_falls_back_to_the_algorithmic_engine():
    app = _app()
    fake = FakeAIGenerator(fail=True)
    _enable_ai(app, fake)
    with TestClient(app) as client, Table(client, app, config=AI_CONFIG) as table:
        _start_and_wait_until_generating(table, fake)
        fake.release.set()
        question = receive_until(table.host, "question.started")["payload"]
        assert question["text"] != AI_TEXT
        assert table.game.questions[0].source_rule_id != "ai_group_insight"


def test_an_algorithmic_room_never_touches_the_ai_generator():
    app = _app()
    fake = FakeAIGenerator()
    fake.release.set()
    _enable_ai(app, fake)
    with TestClient(app) as client, Table(
        client, app, config={"question_count": 3, "language": "en"}
    ) as table:
        table.start()
        assert fake.calls == 0
