"""Player WebSocket endpoint (MASTER_SPEC.md §14.1).

``/ws/rooms/{room_code}?player_id=...`` with the player token offered as the
subprotocol pair ``["mizemi.player", <token>]``. The room, the player and
the token are all verified before the socket is accepted; any failure closes
the connection without a realtime envelope (§14.1). Everything after that is
delegated to the ``GameHub``.
"""

from typing import Any

from fastapi import APIRouter, WebSocket

from app.realtime.connections import ConnectionHandle
from app.realtime.errors import ErrorCode
from app.realtime.game_events import build_error
from app.realtime.hub import GameHub
from app.realtime.transport import (
    FORBIDDEN_ORIGIN_CLOSE_CODE,
    PLAYER_PROTOCOL,
    UNRESOLVED_CLOSE_CODE,
    origin_allowed,
    receive_loop,
    requested_token,
)

router = APIRouter()


def _error_envelope(game_id: str, code: ErrorCode, message: str) -> dict[str, Any]:
    """Build an §17 error payload inside the canonical §14.3 envelope."""
    return build_error(game_id, code, message)


@router.websocket("/ws/rooms/{room_code}")
async def player_websocket(websocket: WebSocket, room_code: str, player_id: str) -> None:
    hub: GameHub = websocket.app.state.game_hub
    if not origin_allowed(websocket):
        await websocket.close(code=FORBIDDEN_ORIGIN_CLOSE_CODE)
        return
    room = hub.resolve_player(room_code, player_id, requested_token(websocket, PLAYER_PROTOCOL))
    if room is None:
        await websocket.close(code=UNRESOLVED_CLOSE_CODE)
        return

    await websocket.accept(subprotocol=PLAYER_PROTOCOL)
    handle = ConnectionHandle(websocket, role="player", player_id=player_id)
    hub.connect(room, handle)
    try:
        await receive_loop(websocket, hub, room, handle)
    finally:
        hub.disconnect(room, handle)
        await handle.shutdown()
