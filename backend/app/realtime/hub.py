"""Per-room realtime coordination (MASTER_SPEC.md §11, §14).

``GameHub`` is the single entry point for everything that changes a room at
runtime: REST joins, WebSocket connects/disconnects, player and host
commands, and the question deadline.

Consistency rules:

* Every mutation of a room happens under that room's lock, and the messages
  it causes are queued before the lock is released. Queuing is synchronous
  and each connection drains its own FIFO queue, so every client sees events
  in exactly the order the state changed.
* A question closes exactly once: the server-side deadline timer and the
  final answer both call ``_close_question`` under the lock, and whichever
  runs second finds the question no longer active and does nothing.
* Only the connected, token-verified identity acts: player commands always
  use the connection's own ``player_id``; host commands require the host
  connection. Payload identities are never trusted.
"""

import asyncio
import json
import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor, wait
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from pydantic import ValidationError

from app.api.schemas import (
    AnswerSubmissionSchema,
    EmptyPayloadSchema,
    PlayerProfileSchema,
    RemovePlayerPayloadSchema,
)
from app.application.create_room import CreateRoomService, HostedRoom
from app.application.gameplay import GameplayService, NextStep
from app.application.join_player import JoinPlayerResult, JoinPlayerService
from app.application.profile_rules import ProfileValidationError, build_validated_profile
from app.application.start_game import GameNotStartableError, NoQuestionsGeneratedError
from app.domain.game import (
    AnswerRejectedError,
    AnswerRejection,
    Game,
    GameState,
    InvalidStateTransitionError,
    Room,
)
from app.domain.game.config import GameConfig
from app.infrastructure.credentials import CredentialStore
from app.infrastructure.rooms import RoomNotFoundError, RoomRegistry
from app.realtime import game_events as events
from app.realtime.connections import ConnectionHandle, RoomConnectionRegistry
from app.realtime.envelope import (
    MalformedEnvelopeError,
    UnknownEventError,
    parse_client_envelope,
)
from app.realtime.errors import ErrorCode
from app.realtime.events import ClientToServerEvent

logger = logging.getLogger("mizemi.realtime")

MAX_FRAME_CHARS = 16_384
MAX_ACTIVE_ROOMS = 100


class RoomLimitError(Exception):
    """The server is holding its classroom room limit."""

# Close slightly after the deadline so an answer the server stamped just
# before it is never raced by the timer.
DEADLINE_GRACE_SECONDS = 0.25
REMOVED_PLAYER_CLOSE_CODE = 4000

MALFORMED_MESSAGE = "The message is not a valid realtime envelope."
GAME_ID_MISMATCH_MESSAGE = "The envelope game_id does not match this connection's game."
INTERNAL_MESSAGE = "Something went wrong. Please try again."
NO_QUESTIONS_MESSAGE = (
    "We couldn't build any questions from the profiles yet. Ask players to share "
    "more answers and allow them to be used in questions."
)

_ANSWER_REJECTIONS: dict[AnswerRejection, tuple[ErrorCode, str]] = {
    AnswerRejection.QUESTION_NOT_ACTIVE: (
        ErrorCode.QUESTION_CLOSED,
        "This question is no longer open.",
    ),
    AnswerRejection.WRONG_QUESTION: (
        ErrorCode.QUESTION_CLOSED,
        "This question is no longer open.",
    ),
    AnswerRejection.DEADLINE_PASSED: (ErrorCode.QUESTION_CLOSED, "Time is up for this question."),
    AnswerRejection.ALREADY_ANSWERED: (
        ErrorCode.ALREADY_ANSWERED,
        "You already answered this question.",
    ),
    AnswerRejection.INVALID_OPTION: (
        ErrorCode.VALIDATION_ERROR,
        "That answer option does not exist.",
    ),
    AnswerRejection.UNKNOWN_PLAYER: (
        ErrorCode.VALIDATION_ERROR,
        "This player is not part of the game.",
    ),
}


@dataclass
class _RoomRuntime:
    lock: threading.RLock = field(default_factory=threading.RLock)
    deadline_timer: asyncio.TimerHandle | None = None
    last_activity: datetime | None = None


class GameHub:
    """Serializes room mutations, fans out events, and owns question timers."""

    def __init__(
        self,
        *,
        registry: RoomRegistry,
        credentials: CredentialStore,
        connections: RoomConnectionRegistry,
        gameplay: GameplayService,
        max_players: int,
        persist: Callable[[Game], None] | None = None,
    ) -> None:
        self._registry = registry
        self._credentials = credentials
        self._connections = connections
        self._gameplay = gameplay
        self._max_players = max_players
        self._persist = persist
        self._rooms: dict[str, _RoomRuntime] = {}
        self._guard = threading.Lock()
        # Finished games are written off the event loop on a single worker;
        # shutdown flushes pending writes so a just-finished game is kept.
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mizemi-persist")
        self._pending: set[Future[None]] = set()
        self._pending_lock = threading.Lock()

    # --- runtime bookkeeping ---------------------------------------------

    def _runtime(self, room_code: str) -> _RoomRuntime:
        code = room_code.strip().upper()
        with self._guard:
            runtime = self._rooms.get(code)
            if runtime is None:
                runtime = _RoomRuntime()
                self._rooms[code] = runtime
            return runtime

    def _touch(self, runtime: _RoomRuntime) -> None:
        runtime.last_activity = self._gameplay.now()

    # --- REST-triggered --------------------------------------------------

    def create_room(self, config: GameConfig | None = None) -> HostedRoom:
        if len(self._rooms) >= MAX_ACTIVE_ROOMS:
            raise RoomLimitError()
        hosted = CreateRoomService(self._registry, credentials=self._credentials).create_hosted_room(
            config if config is not None else GameConfig(question_count=self._gameplay.config.questions_per_game)
        )
        self._touch(self._runtime(hosted.room.room_code))
        return hosted

    def join(self, room_code: str, display_name: str) -> JoinPlayerResult:
        """Join through the application service, then announce the new player."""
        room = self._registry.get(room_code)  # RoomNotFoundError propagates
        runtime = self._runtime(room.room_code)
        with runtime.lock:
            result = JoinPlayerService(
                self._registry,
                credentials=self._credentials,
                max_players=self._max_players,
            ).join(room.room_code, display_name)
            self._touch(runtime)
            self._broadcast_room(room)
        return result

    # --- connection resolution -------------------------------------------

    def resolve_player(self, room_code: str, player_id: str, token: str | None) -> Room | None:
        try:
            room = self._registry.get(room_code)
        except RoomNotFoundError:
            return None
        if room.game.get_player(player_id) is None:
            return None
        if not self._credentials.verify_player(room.room_code, player_id, token):
            return None
        return room

    def resolve_host(self, room_code: str, token: str | None) -> Room | None:
        try:
            room = self._registry.get(room_code)
        except RoomNotFoundError:
            return None
        if not self._credentials.verify_host(room.room_code, token):
            return None
        return room

    # --- connection lifecycle ----------------------------------------------

    def connect(self, room: Room, handle: ConnectionHandle) -> None:
        runtime = self._runtime(room.room_code)
        with runtime.lock:
            self._connections.add(room.room_code, handle)
            if handle.role == "player" and handle.player_id is not None:
                player = room.game.get_player(handle.player_id)
                if player is not None:
                    player.connected = True
            self._touch(runtime)
            # Everyone else learns about the new connection; the newcomer gets
            # one full sync (which starts with the same snapshot) instead.
            self._broadcast_room(room, exclude=handle)
            self._send_sync(room, handle)

    def disconnect(self, room: Room, handle: ConnectionHandle) -> None:
        runtime = self._runtime(room.room_code)
        with runtime.lock:
            self._connections.remove(room.room_code, handle)
            if handle.role == "player" and handle.player_id is not None:
                player = room.game.get_player(handle.player_id)
                if player is not None:
                    # Connected while at least one socket remains (§14.1).
                    player.connected = (
                        self._connections.player_connection_count(
                            room.room_code, handle.player_id
                        )
                        > 0
                    )
            self._touch(runtime)
            self._broadcast_room(room)

    # --- inbound messages ----------------------------------------------------

    def handle_message(self, room: Room, handle: ConnectionHandle, raw: str | None) -> None:
        """Parse one frame and dispatch it; every failure answers with §17."""
        game = room.game
        if raw is None:
            self._reply_error(handle, game, ErrorCode.VALIDATION_ERROR, MALFORMED_MESSAGE)
            return
        if len(raw) > MAX_FRAME_CHARS:
            self._reply_error(handle, game, ErrorCode.VALIDATION_ERROR, "The message is too large.")
            return
        try:
            data = json.loads(raw)
        except (ValueError, RecursionError):
            self._reply_error(handle, game, ErrorCode.VALIDATION_ERROR, MALFORMED_MESSAGE)
            return
        if not isinstance(data, dict):
            self._reply_error(handle, game, ErrorCode.VALIDATION_ERROR, MALFORMED_MESSAGE)
            return
        try:
            event, envelope = parse_client_envelope(data)
        except MalformedEnvelopeError:
            self._reply_error(handle, game, ErrorCode.VALIDATION_ERROR, MALFORMED_MESSAGE)
            return
        except UnknownEventError:
            self._reply_error(handle, game, ErrorCode.UNKNOWN_EVENT, "Unknown event.")
            return
        if envelope.game_id != game.game_id:
            self._reply_error(handle, game, ErrorCode.VALIDATION_ERROR, GAME_ID_MISMATCH_MESSAGE)
            return

        runtime = self._runtime(room.room_code)
        with runtime.lock:
            self._touch(runtime)
            try:
                if handle.role == "host":
                    self._handle_host(room, handle, event, envelope.payload)
                else:
                    self._handle_player(room, handle, event, envelope.payload)
            except Exception:
                # Event name only — payloads may hold profile data (§10).
                logger.error("unexpected error handling %s", event.value)
                self._reply_error(handle, game, ErrorCode.INTERNAL_ERROR, INTERNAL_MESSAGE)

    # --- player commands -----------------------------------------------------

    def _handle_player(
        self,
        room: Room,
        handle: ConnectionHandle,
        event: ClientToServerEvent,
        payload: dict[str, Any],
    ) -> None:
        if event is ClientToServerEvent.PLAYER_PROFILE_SUBMIT:
            self._player_profile(room, handle, payload)
        elif event is ClientToServerEvent.PLAYER_READY:
            self._player_ready(room, handle, payload)
        elif event is ClientToServerEvent.ANSWER_SUBMIT:
            self._player_answer(room, handle, payload)
        elif event is ClientToServerEvent.PLAYER_JOIN:
            # The connection is already bound by URL + token; player.join is a
            # resync request that re-sends the current state (§14.2).
            self._send_sync(room, handle)
        else:
            self._reply_error(handle, room.game, ErrorCode.NOT_HOST, "Only the host can do that.")

    def _player_profile(self, room: Room, handle: ConnectionHandle, payload: dict[str, Any]) -> None:
        game, player_id = room.game, handle.player_id
        assert player_id is not None
        try:
            schema = PlayerProfileSchema.model_validate(payload)
        except ValidationError:
            self._reply_error(
                handle, game, ErrorCode.VALIDATION_ERROR,
                "The payload is not a valid profile submission.",
            )
            return
        if schema.player_id != player_id:
            self._reply_error(
                handle, game, ErrorCode.VALIDATION_ERROR,
                "The profile player_id does not match this connection's player.",
            )
            return
        try:
            profile = build_validated_profile(
                player_id,
                [(f.field_key, f.value, f.allow_question_usage) for f in schema.fields],
            )
        except ProfileValidationError as exc:
            self._reply_error(handle, game, ErrorCode.VALIDATION_ERROR, exc.message)
            return
        try:
            game.submit_initial_profile(player_id, profile)
        except ValueError:
            self._reply_error(
                handle, game, ErrorCode.VALIDATION_ERROR, "The profile submission was rejected."
            )
            return
        self._broadcast_room(room)

    def _player_ready(self, room: Room, handle: ConnectionHandle, payload: dict[str, Any]) -> None:
        game, player_id = room.game, handle.player_id
        assert player_id is not None
        if not self._is_empty(payload):
            self._reply_error(
                handle, game, ErrorCode.VALIDATION_ERROR,
                "The player.ready payload must be exactly empty.",
            )
            return
        try:
            game.mark_player_ready(player_id)
        except ValueError:
            self._reply_error(handle, game, ErrorCode.VALIDATION_ERROR, "The ready request was rejected.")
            return
        self._broadcast_room(room)

    def _player_answer(self, room: Room, handle: ConnectionHandle, payload: dict[str, Any]) -> None:
        game, player_id = room.game, handle.player_id
        assert player_id is not None
        try:
            submission = AnswerSubmissionSchema.model_validate(payload)
        except ValidationError:
            self._reply_error(handle, game, ErrorCode.VALIDATION_ERROR, "The payload is not a valid answer.")
            return
        try:
            outcome = self._gameplay.submit_answer(
                game, player_id, submission.question_id, submission.option_id
            )
        except AnswerRejectedError as exc:
            code, message = _ANSWER_REJECTIONS[exc.reason]
            self._reply_error(handle, game, code, message)
            return
        self._connections.enqueue_to_player(
            room.room_code, player_id, events.build_answer_accepted(game.game_id, outcome.answer)
        )
        self._connections.enqueue_all(room.room_code, events.build_answer_progress(game))
        if outcome.all_answered:
            self._close_question(room)

    # --- host commands -------------------------------------------------------

    def _handle_host(
        self,
        room: Room,
        handle: ConnectionHandle,
        event: ClientToServerEvent,
        payload: dict[str, Any],
    ) -> None:
        if event is ClientToServerEvent.GAME_START:
            self._host_start(room, handle, payload)
        elif event is ClientToServerEvent.GAME_NEXT:
            self._host_next(room, handle, payload)
        elif event is ClientToServerEvent.PLAYER_REMOVE:
            self._host_remove(room, handle, payload)
        elif event is ClientToServerEvent.PLAYER_JOIN:
            self._send_sync(room, handle)
        else:
            self._reply_error(
                handle, room.game, ErrorCode.VALIDATION_ERROR,
                "This action is only available to players.",
            )

    def _host_start(self, room: Room, handle: ConnectionHandle, payload: dict[str, Any]) -> None:
        game = room.game
        if not self._is_empty(payload):
            self._reply_error(
                handle, game, ErrorCode.VALIDATION_ERROR,
                "The game.start payload must be exactly empty.",
            )
            return
        try:
            self._gameplay.start_game(game)
        except GameNotStartableError:
            self._reply_error(
                handle, game, ErrorCode.INVALID_STATE_TRANSITION,
                "The game can start once every player is ready.",
            )
            return
        except NoQuestionsGeneratedError:
            self._reply_error(handle, game, ErrorCode.NO_QUESTIONS_AVAILABLE, NO_QUESTIONS_MESSAGE)
            return
        self._broadcast_room(room)
        self._connections.enqueue_all(room.room_code, events.build_game_started(game))
        self._open_question(room)

    def _host_next(self, room: Room, handle: ConnectionHandle, payload: dict[str, Any]) -> None:
        game = room.game
        if not self._is_empty(payload):
            self._reply_error(
                handle, game, ErrorCode.VALIDATION_ERROR,
                "The game.next payload must be exactly empty.",
            )
            return
        try:
            outcome = self._gameplay.next(game)
        except InvalidStateTransitionError:
            self._reply_error(
                handle, game, ErrorCode.INVALID_STATE_TRANSITION,
                "The game can't move on right now.",
            )
            return
        self._broadcast_room(room)
        if outcome.step is NextStep.LEADERBOARD:
            self._connections.enqueue_all(
                room.room_code,
                events.build_leaderboard_updated(game.game_id, self._gameplay.leaderboard(game)),
            )
        elif outcome.step is NextStep.QUESTION:
            self._open_question(room)
        else:
            self._connections.enqueue_all(
                room.room_code,
                events.build_game_finished(game.game_id, self._gameplay.leaderboard(game)),
            )
            self._persist_finished(game)

    def _host_remove(self, room: Room, handle: ConnectionHandle, payload: dict[str, Any]) -> None:
        game = room.game
        try:
            body = RemovePlayerPayloadSchema.model_validate(payload)
        except ValidationError:
            self._reply_error(
                handle, game, ErrorCode.VALIDATION_ERROR,
                "The payload is not a valid player removal.",
            )
            return
        try:
            game.remove_player(body.player_id)
        except ValueError:
            self._reply_error(
                handle, game, ErrorCode.VALIDATION_ERROR,
                "That player can't be removed right now.",
            )
            return
        self._credentials.forget_player(room.room_code, body.player_id)
        snapshot = events.build_room_updated(room.room_code, game)
        for connection in self._connections.handles_for(room.room_code):
            if connection.role == "player" and connection.player_id == body.player_id:
                self._connections.remove(room.room_code, connection)
                # The removed player sees a snapshot without themselves, then
                # the socket closes; their credential is already revoked.
                connection.enqueue(snapshot)
                connection.close(REMOVED_PLAYER_CLOSE_CODE)
        self._broadcast_room(room)

    # --- question lifecycle ----------------------------------------------------

    def _open_question(self, room: Room) -> None:
        game = room.game
        question = game.current_question
        if question is None:  # pragma: no cover - guarded by the state machine
            return
        started_at = game.question_opened_at or self._gameplay.now()
        self._connections.enqueue_all(
            room.room_code, events.build_question_started(question, game.game_id, started_at)
        )
        self._connections.enqueue_all(room.room_code, events.build_answer_progress(game))
        self._schedule_deadline(room, question.question_id, game.question_deadline)

    def _schedule_deadline(self, room: Room, question_id: str, deadline: datetime | None) -> None:
        runtime = self._runtime(room.room_code)
        self._cancel_deadline(runtime)
        if deadline is None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # synchronous callers (unit tests) close questions explicitly
        delay = max(0.0, (deadline - self._gameplay.now()).total_seconds())
        runtime.deadline_timer = loop.call_later(
            delay + DEADLINE_GRACE_SECONDS, self._on_deadline, room, question_id
        )

    @staticmethod
    def _cancel_deadline(runtime: _RoomRuntime) -> None:
        if runtime.deadline_timer is not None:
            runtime.deadline_timer.cancel()
            runtime.deadline_timer = None

    def _on_deadline(self, room: Room, question_id: str) -> None:
        """Timer callback: close the question if it is still the open one."""
        runtime = self._runtime(room.room_code)
        with runtime.lock:
            runtime.deadline_timer = None
            try:
                self.close_if_active(room, question_id)
            except Exception:  # pragma: no cover - defensive; never kill the loop
                logger.error("failed to close a question at its deadline")

    def close_if_active(self, room: Room, question_id: str) -> bool:
        """Close ``question_id`` if it is still active; idempotent."""
        runtime = self._runtime(room.room_code)
        with runtime.lock:
            game = room.game
            question = game.current_question
            if (
                game.state is not GameState.QUESTION_ACTIVE
                or question is None
                or question.question_id != question_id
            ):
                return False
            self._close_question(room)
            return True

    def _close_question(self, room: Room) -> None:
        game = room.game
        self._cancel_deadline(self._runtime(room.room_code))
        result = self._gameplay.close_question(game)
        statistics = self._gameplay.question_statistics(game, result)
        self._broadcast_room(room)
        for connection in self._connections.handles_for(room.room_code):
            recipient = connection.player_id if connection.role == "player" else None
            connection.enqueue(
                events.build_question_ended(game, result, statistics, player_id=recipient)
            )

    # --- persistence & maintenance ----------------------------------------------

    def _persist_finished(self, game: Game) -> None:
        if self._persist is None:
            return
        # The game is terminal — nothing mutates it again — so the worker
        # thread can read it while the event loop keeps serving other rooms.
        future = self._executor.submit(self._safe_persist, game)
        with self._pending_lock:
            self._pending.add(future)
        future.add_done_callback(self._forget_pending)

    def _forget_pending(self, future: Future[None]) -> None:
        with self._pending_lock:
            self._pending.discard(future)

    def flush_persistence(self, timeout: float = 10.0) -> None:
        """Block until every queued finished-game write has completed."""
        with self._pending_lock:
            pending = list(self._pending)
        if pending:
            wait(pending, timeout=timeout)

    def shutdown(self) -> None:
        """Cancel timers and finish database work before the engine is disposed."""
        for runtime in self._rooms.values():
            self._cancel_deadline(runtime)
        self._executor.shutdown(wait=True)

    def has_pending_deadline(self, room_code: str) -> bool:
        """Whether a question-deadline timer is armed for ``room_code``."""
        return self._runtime(room_code).deadline_timer is not None

    def _safe_persist(self, game: Game) -> None:
        assert self._persist is not None
        try:
            self._persist(game)
        except Exception:
            logger.error("failed to persist a finished game")

    def sweep_idle_rooms(self, *, idle_ttl: timedelta) -> int:
        """Forget rooms with no live connections and no activity within ``idle_ttl``.

        Keeps process memory bounded and drops in-memory profile data of
        abandoned rooms (§10.5). Returns the number of rooms removed.
        """
        now = self._gameplay.now()
        removed = 0
        with self._guard:
            codes = list(self._rooms)
        for code in codes:
            runtime = self._runtime(code)
            with runtime.lock:
                if self._connections.handles_for(code):
                    continue
                if runtime.last_activity is not None and now - runtime.last_activity < idle_ttl:
                    continue
                self._cancel_deadline(runtime)
                try:
                    self._registry.remove(code)
                except RoomNotFoundError:
                    pass
                self._credentials.forget_room(code)
                with self._guard:
                    self._rooms.pop(code, None)
                removed += 1
        return removed

    # --- outbound helpers -------------------------------------------------------

    def _send_sync(self, room: Room, handle: ConnectionHandle) -> None:
        """Bring one (re)connecting client up to date with the current state."""
        game = room.game
        recipient = handle.player_id if handle.role == "player" else None
        handle.enqueue(events.build_room_updated(room.room_code, game))
        state = game.state
        question = game.current_question
        if state is GameState.QUESTION_ACTIVE and question is not None:
            started_at = game.question_opened_at or self._gameplay.now()
            handle.enqueue(events.build_question_started(question, game.game_id, started_at))
            handle.enqueue(events.build_answer_progress(game))
            if recipient is not None:
                answer = game.answer_for(question.question_id, recipient)
                if answer is not None:
                    handle.enqueue(events.build_answer_accepted(game.game_id, answer))
        elif state is GameState.QUESTION_RESULTS and game.last_round is not None:
            statistics = self._gameplay.question_statistics(game, game.last_round)
            handle.enqueue(
                events.build_question_ended(game, game.last_round, statistics, player_id=recipient)
            )
        elif state is GameState.LEADERBOARD:
            handle.enqueue(
                events.build_leaderboard_updated(game.game_id, self._gameplay.leaderboard(game))
            )
        elif state is GameState.FINISHED:
            handle.enqueue(
                events.build_game_finished(game.game_id, self._gameplay.leaderboard(game))
            )

    def _broadcast_room(self, room: Room, *, exclude: ConnectionHandle | None = None) -> None:
        message = events.build_room_updated(room.room_code, room.game)
        for connection in self._connections.handles_for(room.room_code):
            if connection is not exclude:
                connection.enqueue(message)

    @staticmethod
    def _reply_error(handle: ConnectionHandle, game: Game, code: ErrorCode, message: str) -> None:
        handle.enqueue(events.build_error(game.game_id, code, message))

    @staticmethod
    def _is_empty(payload: dict[str, Any]) -> bool:
        try:
            EmptyPayloadSchema.model_validate(payload)
        except ValidationError:
            return False
        return True
