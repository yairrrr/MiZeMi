"""Create-room use case (MASTER_SPEC.md §8, §13, §15 — first vertical).

Application layer: orchestrates domain and infrastructure; no FastAPI or
Pydantic imports. Room-code collision retry lives here — the generator stays
pure and the registry only enforces uniqueness.
"""

from collections.abc import Callable
from uuid import uuid4

from app.domain.game import Game, Room
from app.infrastructure.rooms import (
    DuplicateRoomCodeError,
    RoomRegistry,
    generate_room_code,
)

MAX_ROOM_CODE_ATTEMPTS = 10


class RoomCreationFailedError(Exception):
    """No unique room_code could be registered within the bounded attempts."""


class CreateRoomService:
    """Creates a Game + Room pair and registers it as an active room."""

    def __init__(
        self,
        registry: RoomRegistry,
        code_generator: Callable[[], str] | None = None,
    ) -> None:
        self._registry = registry
        # Late-bound default keeps the generator patchable in tests.
        self._generate_code = code_generator if code_generator is not None else generate_room_code

    def create_room(self) -> Room:
        game = Game(game_id=str(uuid4()))
        for _ in range(MAX_ROOM_CODE_ATTEMPTS):
            room = Room(room_code=self._generate_code(), game=game)
            try:
                self._registry.register(room)
            except DuplicateRoomCodeError:
                continue
            return room
        raise RoomCreationFailedError(
            f"could not allocate a unique room_code in {MAX_ROOM_CODE_ATTEMPTS} attempts"
        )
