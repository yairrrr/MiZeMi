"""Shared WebSocket transport helpers (MASTER_SPEC.md §14.1).

Credentials travel in the ``Sec-WebSocket-Protocol`` header as a two-item
subprotocol list — ``["mizemi.player", <token>]`` or ``["mizemi.host",
<token>]`` — rather than in the URL, so they never appear in server or proxy
access logs. The server accepts by echoing only the role protocol.
"""

from typing import TYPE_CHECKING

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

if TYPE_CHECKING:  # pragma: no cover
    from app.domain.game import Room
    from app.realtime.connections import ConnectionHandle
    from app.realtime.hub import GameHub

PLAYER_PROTOCOL = "mizemi.player"
HOST_PROTOCOL = "mizemi.host"

# Internal close codes for connections that never become MiZeMi sessions.
# They are implementation values, not protocol guarantees: the contract is
# only "closed without an envelope" (§14.1).
UNRESOLVED_CLOSE_CODE = 4404
FORBIDDEN_ORIGIN_CLOSE_CODE = 4403


def origin_allowed(websocket: WebSocket) -> bool:
    """Reject cross-site browser connections (CSWSH defense).

    Browsers always send ``Origin`` on WebSocket upgrades; it must be one of
    the configured origins (``"*"`` allows any — local LAN demos only).
    Non-browser clients send no ``Origin`` and are judged by their token.
    """
    origin = websocket.headers.get("origin")
    if origin is None:
        return True
    allowed = websocket.app.state.settings.cors_origins
    return "*" in allowed or origin in allowed


def requested_token(websocket: WebSocket, protocol: str) -> str | None:
    """The bearer token offered alongside ``protocol``, if exactly one."""
    offered = list(websocket.scope.get("subprotocols") or [])
    if protocol not in offered:
        return None
    others = [item for item in offered if item != protocol]
    return others[0] if len(others) == 1 else None


async def receive_loop(
    websocket: WebSocket, hub: "GameHub", room: "Room", handle: "ConnectionHandle"
) -> None:
    """Feed every inbound frame to the hub until the socket closes."""
    while True:
        try:
            message = await websocket.receive()
        except (RuntimeError, WebSocketDisconnect):
            return
        if message["type"] == "websocket.disconnect":
            return
        hub.handle_message(room, handle, message.get("text"))
