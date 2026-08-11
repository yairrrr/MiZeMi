"""Unit tests for the Room domain object (MASTER_SPEC.md §8).

Structural behavior only — deferred join policies (capacity, allowed states,
name rules, host authorization, room-code uniqueness) are deliberately
untested because Room deliberately does not enforce them.
"""

import pytest

from app.domain.game import Game, Player, Room


def _room() -> Room:
    return Room(room_code="ABC123", game=Game(game_id="g1"))


class TestRoomConstruction:
    def test_room_stores_supplied_room_code(self) -> None:
        room = _room()

        assert room.room_code == "ABC123"

    def test_room_exposes_the_exact_game_instance_supplied(self) -> None:
        game = Game(game_id="g1")

        room = Room(room_code="ABC123", game=game)

        assert room.game is game

    def test_room_does_not_create_or_replace_the_game(self) -> None:
        game = Game(game_id="g1")
        game.add_player(Player(player_id="p1", display_name="Dana"))

        room = Room(room_code="ABC123", game=game)

        assert room.game is game
        assert room.game.players == game.players

    def test_same_room_code_on_two_rooms_is_not_a_domain_invariant(self) -> None:
        room_a = Room(room_code="ABC123", game=Game(game_id="g1"))
        room_b = Room(room_code="ABC123", game=Game(game_id="g2"))

        assert room_a.room_code == room_b.room_code
        assert room_a.game is not room_b.game


class TestRoomJoin:
    def test_join_delegates_to_game_add_player(self) -> None:
        room = _room()
        player = Player(player_id="p1", display_name="Dana")

        room.join(player)

        assert room.game.get_player("p1") is player
        assert room.game.players == (player,)

    def test_room_owns_no_separate_player_collection(self) -> None:
        room = _room()

        room.join(Player(player_id="p1", display_name="Dana"))

        assert not hasattr(room, "players")
        assert not hasattr(room, "_players")

    def test_duplicate_join_behavior_is_games_behavior(self) -> None:
        room = _room()
        original = Player(player_id="p1", display_name="Dana")
        room.join(original)

        with pytest.raises(ValueError):
            room.join(Player(player_id="p1", display_name="Someone Else"))

        assert room.game.players == (original,)
