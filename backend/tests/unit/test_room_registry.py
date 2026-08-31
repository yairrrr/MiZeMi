"""Unit tests for room-code generation and the in-memory RoomRegistry (§8, §15)."""

import pytest

from app.domain.game import Game, Room
from app.infrastructure.rooms import (
    ROOM_CODE_ALPHABET,
    ROOM_CODE_LENGTH,
    DuplicateRoomCodeError,
    RoomNotFoundError,
    RoomRegistry,
    generate_room_code,
)


def _room(room_code: str = "ABC234", game_id: str = "g1") -> Room:
    return Room(room_code=room_code, game=Game(game_id=game_id))


class TestGenerateRoomCode:
    def test_code_has_exactly_six_characters(self) -> None:
        assert len(generate_room_code()) == ROOM_CODE_LENGTH == 6

    def test_every_character_is_from_the_approved_alphabet(self) -> None:
        for _ in range(50):
            code = generate_room_code()
            assert all(char in ROOM_CODE_ALPHABET for char in code)

    def test_output_is_uppercase(self) -> None:
        for _ in range(50):
            code = generate_room_code()
            assert code == code.upper()

    def test_repeated_generation_yields_valid_independent_codes(self) -> None:
        codes = [generate_room_code() for _ in range(20)]

        assert all(len(code) == ROOM_CODE_LENGTH for code in codes)
        assert all(
            all(char in ROOM_CODE_ALPHABET for char in code) for code in codes
        )


class TestRoomRegistry:
    def test_register_then_get_returns_same_object(self) -> None:
        registry = RoomRegistry()
        room = _room()

        registry.register(room)

        assert registry.get("ABC234") is room

    def test_lookup_with_lowercase_room_code(self) -> None:
        registry = RoomRegistry()
        room = _room()
        registry.register(room)

        assert registry.get("abc234") is room

    def test_lookup_trims_surrounding_whitespace(self) -> None:
        registry = RoomRegistry()
        room = _room()
        registry.register(room)

        assert registry.get("  abc234  ") is room

    def test_duplicate_register_is_rejected(self) -> None:
        registry = RoomRegistry()
        registry.register(_room())

        with pytest.raises(DuplicateRoomCodeError):
            registry.register(_room(game_id="g2"))

    def test_duplicate_registration_does_not_replace_original(self) -> None:
        registry = RoomRegistry()
        original = _room()
        registry.register(original)

        with pytest.raises(DuplicateRoomCodeError):
            registry.register(_room(game_id="g2"))

        assert registry.get("ABC234") is original

    def test_unknown_get_raises_room_not_found(self) -> None:
        registry = RoomRegistry()

        with pytest.raises(RoomNotFoundError) as exc_info:
            registry.get("ZZZZZ2")

        assert exc_info.value.room_code == "ZZZZZ2"

    def test_remove_removes_a_room(self) -> None:
        registry = RoomRegistry()
        registry.register(_room())

        registry.remove("ABC234")

        with pytest.raises(RoomNotFoundError):
            registry.get("ABC234")

    def test_remove_accepts_lowercase_input(self) -> None:
        registry = RoomRegistry()
        registry.register(_room())

        registry.remove("  abc234 ")

        with pytest.raises(RoomNotFoundError):
            registry.get("ABC234")

    def test_removing_unknown_room_raises_room_not_found(self) -> None:
        registry = RoomRegistry()

        with pytest.raises(RoomNotFoundError):
            registry.remove("ZZZZZ2")

    def test_independent_registry_instances_do_not_share_state(self) -> None:
        registry_a = RoomRegistry()
        registry_b = RoomRegistry()
        registry_a.register(_room())

        with pytest.raises(RoomNotFoundError):
            registry_b.get("ABC234")
