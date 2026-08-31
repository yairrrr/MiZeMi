"""Room REST endpoints (MASTER_SPEC.md §13, first vertical)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.errors import error_response
from app.api.schemas import CreateRoomResponse, JoinRoomRequest, PlayerSchema
from app.application.create_room import CreateRoomService
from app.application.join_player import (
    InvalidDisplayNameError,
    JoinPlayerService,
    NameTakenError,
    RoomNotJoinableError,
)
from app.infrastructure.rooms import RoomNotFoundError, RoomRegistry
from app.realtime.errors import ErrorCode

router = APIRouter()


def get_room_registry(request: Request) -> RoomRegistry:
    return request.app.state.room_registry


@router.post("/rooms", status_code=201)
def create_room(
    registry: Annotated[RoomRegistry, Depends(get_room_registry)],
) -> CreateRoomResponse:
    room = CreateRoomService(registry).create_room()
    return CreateRoomResponse(room_code=room.room_code, game_id=room.game.game_id)


@router.post("/rooms/{room_code}/players", status_code=201, response_model=PlayerSchema)
def join_room(
    room_code: str,
    body: JoinRoomRequest,
    registry: Annotated[RoomRegistry, Depends(get_room_registry)],
):
    try:
        player = JoinPlayerService(registry).join(room_code, body.display_name)
    except RoomNotFoundError as exc:
        return error_response(
            404, ErrorCode.ROOM_NOT_FOUND, f"No room exists with code {exc.room_code}."
        )
    except RoomNotJoinableError:
        return error_response(
            409, ErrorCode.ROOM_NOT_JOINABLE, "The game can no longer be joined."
        )
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
    # score=0: the approved initial score for a newly joined player (§9.1).
    return PlayerSchema.from_domain(player, score=0)
