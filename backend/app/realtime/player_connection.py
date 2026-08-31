"""Player WebSocket connection endpoint (MASTER_SPEC.md §14.1, first vertical).

Approved MVP behavior only: resolve room (normalized code) and player, close
without any realtime envelope when either is unknown, and maintain the
player's server-authoritative ``connected`` flag for the accepted session.
Event handling, broadcasts, host connections, and reconnect/simultaneous-
connection policy are explicitly out of scope (deferred).
"""

from fastapi import APIRouter, WebSocket

from app.infrastructure.rooms import RoomNotFoundError, RoomRegistry

# Internal implementation value for pre-resolution closes. Deliberately NOT a
# MiZeMi protocol guarantee: the spec promises only "closed without envelope".
_UNRESOLVED_CLOSE_CODE = 4404

router = APIRouter()


@router.websocket("/ws/rooms/{room_code}")
async def player_websocket(websocket: WebSocket, room_code: str, player_id: str) -> None:
    registry: RoomRegistry = websocket.app.state.room_registry
    try:
        room = registry.get(room_code)
    except RoomNotFoundError:
        await websocket.close(code=_UNRESOLVED_CLOSE_CODE)
        return
    player = room.game.get_player(player_id)
    if player is None:
        await websocket.close(code=_UNRESOLVED_CLOSE_CODE)
        return

    await websocket.accept()
    player.connected = True
    try:
        # Frames are received only so the disconnect can be observed; client
        # event handling is a later task.
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
    finally:
        player.connected = False
