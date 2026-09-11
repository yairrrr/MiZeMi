"""Host WebSocket endpoint (MASTER_SPEC.md §8, §14.1).

``/ws/rooms/{room_code}/host`` with the host token offered as the
subprotocol pair ``["mizemi.host", <token>]``. The host is not a Player
(§9.1): it controls the game (``game.start``, ``game.next``,
``player.remove``) and receives every room event, but never answers.
"""

from fastapi import APIRouter, WebSocket

from app.realtime.connections import ConnectionHandle
from app.realtime.hub import GameHub
from app.realtime.transport import (
    FORBIDDEN_ORIGIN_CLOSE_CODE,
    HOST_PROTOCOL,
    UNRESOLVED_CLOSE_CODE,
    origin_allowed,
    receive_loop,
    requested_token,
)

router = APIRouter()


@router.websocket("/ws/rooms/{room_code}/host")
async def host_websocket(websocket: WebSocket, room_code: str) -> None:
    hub: GameHub = websocket.app.state.game_hub
    if not origin_allowed(websocket):
        await websocket.close(code=FORBIDDEN_ORIGIN_CLOSE_CODE)
        return
    room = hub.resolve_host(room_code, requested_token(websocket, HOST_PROTOCOL))
    if room is None:
        await websocket.close(code=UNRESOLVED_CLOSE_CODE)
        return

    await websocket.accept(subprotocol=HOST_PROTOCOL)
    handle = ConnectionHandle(websocket, role="host")
    hub.connect(room, handle)
    try:
        await receive_loop(websocket, hub, room, handle)
    finally:
        hub.disconnect(room, handle)
        await handle.shutdown()
