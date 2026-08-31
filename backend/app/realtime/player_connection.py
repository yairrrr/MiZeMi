"""Player WebSocket connection and gameplay commands (MASTER_SPEC.md §14).

Approved behavior only: resolve room/player (close without envelope when
unknown), maintain the ``connected`` flag, and expose the two approved
pre-game client intents — ``player.profile_submit`` and ``player.ready`` —
by delegating to the existing Game domain methods. No broadcasts or success
acknowledgements exist yet (``room.updated`` is deferred); errors reuse the
approved §17 payload inside the approved §14.3 envelope.
"""

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, WebSocket
from pydantic import ValidationError

from app.api.schemas import PlayerProfileSchema, PlayerReadyPayloadSchema
from app.domain.game import Game, PlayerProfile, ProfileField
from app.infrastructure.rooms import RoomNotFoundError, RoomRegistry
from app.realtime.envelope import (
    MalformedEnvelopeError,
    RealtimeEnvelope,
    UnknownEventError,
    parse_client_envelope,
)
from app.realtime.errors import ErrorCode, ErrorDetail, ErrorPayload
from app.realtime.events import ClientToServerEvent, ServerToClientEvent

# Internal implementation value for pre-resolution closes. Deliberately NOT a
# MiZeMi protocol guarantee: the spec promises only "closed without envelope".
_UNRESOLVED_CLOSE_CODE = 4404

_MALFORMED_MESSAGE = "The message is not a valid realtime envelope."

router = APIRouter()


def _error_envelope(game_id: str, code: ErrorCode, message: str) -> dict[str, Any]:
    envelope = RealtimeEnvelope(
        event=ServerToClientEvent.ERROR.value,
        payload=ErrorPayload(
            error=ErrorDetail(code=code, message=message)
        ).model_dump(mode="json"),
        timestamp=datetime.now(UTC),
        game_id=game_id,
    )
    return envelope.model_dump(mode="json")


async def _send_error(
    websocket: WebSocket, game_id: str, code: ErrorCode, message: str
) -> None:
    await websocket.send_json(_error_envelope(game_id, code, message))


async def _handle_profile_submit(
    websocket: WebSocket, game: Game, player_id: str, payload: dict[str, Any]
) -> None:
    try:
        schema = PlayerProfileSchema.model_validate(payload)
    except ValidationError:
        await _send_error(
            websocket,
            game.game_id,
            ErrorCode.VALIDATION_ERROR,
            "The payload is not a valid profile submission.",
        )
        return
    # The connected player is authoritative — a payload naming another
    # player is rejected, never honored.
    if schema.player_id != player_id:
        await _send_error(
            websocket,
            game.game_id,
            ErrorCode.VALIDATION_ERROR,
            "The profile player_id does not match this connection's player.",
        )
        return
    profile = PlayerProfile(
        player_id=player_id,
        fields=tuple(
            ProfileField(
                field_key=field.field_key,
                value=field.value,
                allow_question_usage=field.allow_question_usage,
            )
            for field in schema.fields
        ),
    )
    try:
        game.submit_initial_profile(player_id, profile)
    except ValueError:
        await _send_error(
            websocket,
            game.game_id,
            ErrorCode.VALIDATION_ERROR,
            "The profile submission was rejected.",
        )


async def _handle_player_ready(
    websocket: WebSocket, game: Game, player_id: str, payload: dict[str, Any]
) -> None:
    try:
        PlayerReadyPayloadSchema.model_validate(payload)
    except ValidationError:
        await _send_error(
            websocket,
            game.game_id,
            ErrorCode.VALIDATION_ERROR,
            "The player.ready payload must be exactly empty.",
        )
        return
    try:
        game.mark_player_ready(player_id)
    except ValueError:
        await _send_error(
            websocket,
            game.game_id,
            ErrorCode.VALIDATION_ERROR,
            "The ready request was rejected.",
        )


async def _handle_text_frame(
    websocket: WebSocket, game: Game, player_id: str, raw_text: str
) -> None:
    game_id = game.game_id
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        await _send_error(websocket, game_id, ErrorCode.VALIDATION_ERROR, _MALFORMED_MESSAGE)
        return
    if not isinstance(data, dict):
        await _send_error(websocket, game_id, ErrorCode.VALIDATION_ERROR, _MALFORMED_MESSAGE)
        return
    try:
        event, envelope = parse_client_envelope(data)
    except MalformedEnvelopeError:
        await _send_error(websocket, game_id, ErrorCode.VALIDATION_ERROR, _MALFORMED_MESSAGE)
        return
    except UnknownEventError:
        await _send_error(websocket, game_id, ErrorCode.UNKNOWN_EVENT, "Unknown event.")
        return
    if envelope.game_id != game_id:
        await _send_error(
            websocket,
            game_id,
            ErrorCode.VALIDATION_ERROR,
            "The envelope game_id does not match this connection's game.",
        )
        return

    if event is ClientToServerEvent.PLAYER_PROFILE_SUBMIT:
        await _handle_profile_submit(websocket, game, player_id, envelope.payload)
    elif event is ClientToServerEvent.PLAYER_READY:
        await _handle_player_ready(websocket, game, player_id, envelope.payload)
    # Registry-known events without a handler yet (player.join, game.start,
    # answer.submit, game.next) are a temporary implementation gap: no
    # mutation, no reply. This is NOT a protocol guarantee — each event's
    # own task defines its behavior.


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
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            raw_text = message.get("text")
            if raw_text is None:
                await _send_error(
                    websocket,
                    room.game.game_id,
                    ErrorCode.VALIDATION_ERROR,
                    _MALFORMED_MESSAGE,
                )
                continue
            await _handle_text_frame(websocket, room.game, player_id, raw_text)
    finally:
        player.connected = False
