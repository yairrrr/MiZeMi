"""Room-scoped realtime connection registry (MASTER_SPEC.md §14).

Pure delivery infrastructure for the approved requirement that server events
reach the players connected to a room (§14.2). Connections are tracked by
connection identity, never keyed by ``player_id``: registering a second
connection for the same player simply adds another sink, so this module
defines **no** reconnect, session-replacement, or simultaneous-connection
policy — all of which remain deferred (§0). It also does not touch player
identity, authorization, or the ``connected`` flag, which the connection
endpoint continues to own.
"""

from typing import Any, Protocol


class MessageSink(Protocol):
    """Anything that can receive one JSON realtime message (a WebSocket)."""

    async def send_json(self, data: Any) -> None: ...  # pragma: no cover


class RoomConnectionRegistry:
    """Tracks live connections per room code so events can be delivered.

    Instantiable and injected via application state — no global mutable
    state. Delivery is best-effort: a sink that raises (a socket that died
    between the state check and the send) is dropped and never blocks
    delivery to the remaining connections.
    """

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
