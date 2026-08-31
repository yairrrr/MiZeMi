"""Unit tests for the create-room application service (MASTER_SPEC.md §8, §13, §15)."""

from collections.abc import Iterator

import pytest

from app.application.create_room import (
    MAX_ROOM_CODE_ATTEMPTS,
    CreateRoomService,
    RoomCreationFailedError,
)
from app.domain.game import Game, GameState, Room
from app.infrastructure.rooms import RoomNotFoundError, RoomRegistry


def _sequence_generator(codes: list[str]) -> tuple[Iterator[str], list[str]]:
    """A deterministic code generator that records every call."""
    calls: list[str] = []

    def generate() -> str:
        code = codes[min(len(calls), len(codes) - 1)]
        calls.append(code)
        return code

    return generate, calls


class TestCreateRoomService:
    def test_creates_game_and_room_in_lobby(self) -> None:
        room = CreateRoomService(RoomRegistry()).create_room()

        assert isinstance(room, Room)
        assert isinstance(room.game, Game)
        assert room.game.state is GameState.LOBBY
        assert room.game.players == ()

    def test_returned_room_code_matches_registered_room(self) -> None:
        registry = RoomRegistry()

        room = CreateRoomService(registry).create_room()

        assert registry.get(room.room_code) is room

    def test_returned_game_id_matches_registered_rooms_game(self) -> None:
        registry = RoomRegistry()

        room = CreateRoomService(registry).create_room()

        assert registry.get(room.room_code).game.game_id == room.game.game_id

    def test_generated_identifiers_are_non_empty_strings(self) -> None:
        room = CreateRoomService(RoomRegistry()).create_room()

        assert isinstance(room.room_code, str) and room.room_code
        assert isinstance(room.game.game_id, str) and room.game.game_id

    def test_collision_causes_retry_with_new_code(self) -> None:
        registry = RoomRegistry()
        original = Room(room_code="AAAA22", game=Game(game_id="g-original"))
        registry.register(original)
        generate, calls = _sequence_generator(["AAAA22", "BBBB33"])

        room = CreateRoomService(registry, code_generator=generate).create_room()

        assert calls == ["AAAA22", "BBBB33"]
        assert room.room_code == "BBBB33"
        assert registry.get("BBBB33") is room

    def test_collision_retry_does_not_overwrite_existing_room(self) -> None:
        registry = RoomRegistry()
        original = Room(room_code="AAAA22", game=Game(game_id="g-original"))
        registry.register(original)
        generate, _ = _sequence_generator(["AAAA22", "BBBB33"])

        CreateRoomService(registry, code_generator=generate).create_room()

        assert registry.get("AAAA22") is original

    def test_exhausted_collision_attempts_raise_creation_failure(self) -> None:
        registry = RoomRegistry()
        registry.register(Room(room_code="AAAA22", game=Game(game_id="g-original")))
        generate, calls = _sequence_generator(["AAAA22"])  # always collides

        with pytest.raises(RoomCreationFailedError):
            CreateRoomService(registry, code_generator=generate).create_room()

        assert len(calls) == MAX_ROOM_CODE_ATTEMPTS

    def test_independent_registries_remain_independent(self) -> None:
        registry_a = RoomRegistry()
        registry_b = RoomRegistry()

        room = CreateRoomService(registry_a).create_room()

        with pytest.raises(RoomNotFoundError):
            registry_b.get(room.room_code)
