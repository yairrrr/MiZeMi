"""Room REST endpoints (MASTER_SPEC.md §13, first vertical)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.schemas import CreateRoomResponse
from app.application.create_room import CreateRoomService
from app.infrastructure.rooms import RoomRegistry

router = APIRouter()


def get_room_registry(request: Request) -> RoomRegistry:
    return request.app.state.room_registry


@router.post("/rooms", status_code=201)
def create_room(
    registry: Annotated[RoomRegistry, Depends(get_room_registry)],
) -> CreateRoomResponse:
    room = CreateRoomService(registry).create_room()
    return CreateRoomResponse(room_code=room.room_code, game_id=room.game.game_id)
