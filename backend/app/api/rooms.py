"""Room REST endpoints (MASTER_SPEC.md §13).

``async`` handlers on purpose: they run on the event loop, like the
WebSocket handlers, so every room mutation goes through the ``GameHub`` on a
single thread and joins are broadcast to connected clients immediately.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.errors import error_response
from app.domain.game.config import GameConfig
from app.api.schemas import (
    CreateRoomResponse,
    CreateRoomRequest,
    GameConfigSchema,
    JoinRoomRequest,
    JoinRoomResponse,
    PlayerSchema,
)
from app.application.join_player import (
    InvalidDisplayNameError,
    NameTakenError,
    RoomFullError,
    RoomNotJoinableError,
)
from app.infrastructure.rooms import RoomNotFoundError, RoomRegistry
from app.realtime.errors import ErrorCode
from app.realtime.hub import GameHub, RoomLimitError

router = APIRouter()


def get_room_registry(request: Request) -> RoomRegistry:
    return request.app.state.room_registry


def get_game_hub(request: Request) -> GameHub:
    return request.app.state.game_hub


@router.post("/rooms", status_code=201)
async def create_room(hub: Annotated[GameHub, Depends(get_game_hub)], body: CreateRoomRequest | None = None):
    try:
        hosted = hub.create_room(GameConfig(**body.model_dump()) if body is not None else None)
    except RoomLimitError:
        return error_response(503, ErrorCode.ROOM_FULL, "The server has too many rooms. Please try again later.")
    return CreateRoomResponse(
        room_code=hosted.room.room_code,
        game_id=hosted.room.game.game_id,
        host_token=hosted.host_token,
        config=GameConfigSchema(question_count=hosted.room.game.config.question_count, language=hosted.room.game.config.language),
    )


@router.post("/rooms/{room_code}/players", status_code=201, response_model=JoinRoomResponse)
async def join_room(
    room_code: str,
    body: JoinRoomRequest,
    hub: Annotated[GameHub, Depends(get_game_hub)],
):
    try:
        result = hub.join(room_code, body.display_name)
    except RoomNotFoundError:
        return error_response(
            404, ErrorCode.ROOM_NOT_FOUND, "No room exists with that code."
        )
    except RoomNotJoinableError:
        return error_response(
            409, ErrorCode.ROOM_NOT_JOINABLE, "The game can no longer be joined."
        )
    except RoomFullError:
        return error_response(409, ErrorCode.ROOM_FULL, "This room is full.")
    except NameTakenError:
        return error_response(
            409, ErrorCode.NAME_TAKEN, "That display name is already taken in this room."
        )
    except InvalidDisplayNameError:
        return error_response(
            400,
            ErrorCode.VALIDATION_ERROR,
            "display_name must be 1-20 characters after trimming.",
        )
    assert result.player_token is not None  # the hub always issues credentials
    # score=0: the approved initial score for a newly joined player (§9.1).
    return JoinRoomResponse(
        game_id=result.game_id,
        player=PlayerSchema.from_domain(result.player, score=0),
        player_token=result.player_token,
    )
