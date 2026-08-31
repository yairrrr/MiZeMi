"""Active-room resolution: room-code generation and the in-memory registry.

MASTER_SPEC.md §8 (room-code format) and §15 (first-vertical in-memory
registry). Infrastructure layer: no FastAPI, SQLAlchemy, or Pydantic —
transport mapping of these exceptions (e.g. to ROOM_NOT_FOUND) happens at
the presentation boundary, not here.
"""

import secrets

from app.domain.game import Room

ROOM_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
ROOM_CODE_LENGTH = 6


def generate_room_code() -> str:
    """Return one random 6-character code from the approved alphabet (§8).

    Pure generation only: uniqueness among active rooms is enforced by the
    registry, and collision retry belongs to the room-creation orchestration.
    """
    return "".join(secrets.choice(ROOM_CODE_ALPHABET) for _ in range(ROOM_CODE_LENGTH))


def _canonical(room_code: str) -> str:
    return room_code.strip().upper()


class DuplicateRoomCodeError(Exception):
    """A room with this active room_code is already registered."""

    def __init__(self, room_code: str) -> None:
        super().__init__(f"active room_code already registered: {room_code}")
        self.room_code = room_code


class RoomNotFoundError(Exception):
    """No active room is registered under this room_code."""

    def __init__(self, room_code: str) -> None:
        super().__init__(f"no active room with room_code: {room_code}")
        self.room_code = room_code


class RoomRegistry:
    """In-memory registry of active rooms (MASTER_SPEC.md §15, first vertical).

    Keys are canonical uppercase room codes; lookups trim surrounding
    whitespace and uppercase their input, making resolution case-insensitive
    (§8). Instantiable — no global state; persistence, recovery, and
    retention remain deferred.
    """

    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}

    def register(self, room: Room) -> None:
        code = _canonical(room.room_code)
        if code in self._rooms:
            raise DuplicateRoomCodeError(code)
        self._rooms[code] = room

    def get(self, room_code: str) -> Room:
        code = _canonical(room_code)
        try:
            return self._rooms[code]
        except KeyError:
            raise RoomNotFoundError(code) from None

    def remove(self, room_code: str) -> None:
        code = _canonical(room_code)
        if code not in self._rooms:
            raise RoomNotFoundError(code)
        del self._rooms[code]
