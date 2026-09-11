"""Room-scoped realtime connection registry (MASTER_SPEC.md §14).

Tracks every accepted WebSocket per room. Approved connection policy
(§14.1): a player may hold several simultaneous connections — a phone and a
laptop, or a reconnect that overlaps a dying socket. None replaces another,
and the player counts as ``connected`` while at least one remains.

Outbound delivery goes through ``ConnectionHandle``: every accepted socket
gets its own FIFO queue and writer task, so each client receives messages in
exactly the order the server produced them, and one slow phone never blocks
delivery to the rest of the room.
"""

import asyncio
import contextlib
from dataclasses import dataclass
from typing import Any, Literal, Protocol

Role = Literal["host", "player"]


class MessageSink(Protocol):
    """Anything that can receive one JSON realtime message."""

    async def send_json(self, data: Any) -> None: ...  # pragma: no cover


class WebSocketLike(Protocol):
    async def send_json(self, data: Any) -> None: ...  # pragma: no cover

    async def close(self, code: int = 1000) -> None: ...  # pragma: no cover


@dataclass(frozen=True)
class _CloseRequest:
    code: int


class ConnectionHandle:
    """One accepted WebSocket: its role, player id, and ordered outbound queue.

    ``enqueue`` is synchronous and thread-safe, so the game hub can queue
    messages while it holds a room lock. Must be constructed inside the
    event loop that serves the socket.
    """

    def __init__(
        self, websocket: WebSocketLike, *, role: Role, player_id: str | None = None
    ) -> None:
        self.websocket = websocket
        self.role: Role = role
        self.player_id = player_id
        self._loop = asyncio.get_running_loop()
        self._queue: asyncio.Queue[Any] = asyncio.Queue()
        self._closed = False
        self._writer = self._loop.create_task(self._drain())

    @property
    def closed(self) -> bool:
        return self._closed

    def enqueue(self, message: dict[str, Any]) -> None:
        self._put(message)

    def close(self, code: int = 1000) -> None:
        """Flush messages already queued, then close the socket."""
        self._put(_CloseRequest(code))

    async def send_json(self, data: Any) -> None:
        """``MessageSink`` compatibility: queue rather than write directly."""
        self._put(data)

    async def shutdown(self) -> None:
        """Stop the writer when the connection has ended."""
        self._closed = True
        self._writer.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await self._writer

    def _put(self, item: Any) -> None:
        if self._closed:
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        try:
            if running is self._loop:
                self._queue.put_nowait(item)
            else:
                self._loop.call_soon_threadsafe(self._queue.put_nowait, item)
        except RuntimeError:
            # The loop that owned this socket has stopped.
            self._closed = True

    async def _drain(self) -> None:
        while True:
            item = await self._queue.get()
            if isinstance(item, _CloseRequest):
                self._closed = True
                with contextlib.suppress(Exception):
                    await self.websocket.close(code=item.code)
                return
            try:
                await self.websocket.send_json(item)
            except Exception:  # noqa: BLE001 - a dead socket just stops
                self._closed = True
                return


class RoomConnectionRegistry:
    """Live connections per room code; no global state (injected via app state)."""

    def __init__(self) -> None:
        self._connections: dict[str, list[MessageSink]] = {}

    @staticmethod
    def _canonical(room_code: str) -> str:
        return room_code.strip().upper()

    def add(self, room_code: str, connection: MessageSink) -> None:
        self._connections.setdefault(self._canonical(room_code), []).append(connection)

    def remove(self, room_code: str, connection: MessageSink) -> None:
        """Remove one connection; unknown connections are ignored."""
        code = self._canonical(room_code)
        sinks = self._connections.get(code)
        if sinks is None:
            return
        for index, existing in enumerate(sinks):
            if existing is connection:
                del sinks[index]
                break
        if not sinks:
            del self._connections[code]

    def connections_for(self, room_code: str) -> tuple[MessageSink, ...]:
        return tuple(self._connections.get(self._canonical(room_code), ()))

    def handles_for(self, room_code: str) -> tuple[ConnectionHandle, ...]:
        return tuple(
            sink for sink in self.connections_for(room_code) if isinstance(sink, ConnectionHandle)
        )

    def player_connection_count(self, room_code: str, player_id: str) -> int:
        return sum(
            1
            for handle in self.handles_for(room_code)
            if handle.role == "player" and handle.player_id == player_id
        )

    def enqueue_all(self, room_code: str, message: dict[str, Any]) -> int:
        handles = self.handles_for(room_code)
        for handle in handles:
            handle.enqueue(message)
        return len(handles)

    def enqueue_to_player(self, room_code: str, player_id: str, message: dict[str, Any]) -> int:
        delivered = 0
        for handle in self.handles_for(room_code):
            if handle.role == "player" and handle.player_id == player_id:
                handle.enqueue(message)
                delivered += 1
        return delivered

    def drop_room(self, room_code: str) -> tuple[MessageSink, ...]:
        return tuple(self._connections.pop(self._canonical(room_code), ()))

    async def broadcast(self, room_code: str, message: dict[str, Any]) -> int:
        """Send ``message`` to every connection in the room; return the count sent."""
        delivered = 0
        for connection in self.connections_for(room_code):
            try:
                await connection.send_json(message)
            except Exception:  # noqa: BLE001 - a dead socket must not block others
                self.remove(room_code, connection)
                continue
            delivered += 1
        return delivered
