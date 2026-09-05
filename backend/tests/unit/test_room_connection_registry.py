"""Unit tests for the room connection registry (MASTER_SPEC.md §14)."""

import asyncio
from typing import Any

from app.realtime.connections import RoomConnectionRegistry


class RecordingSink:
    def __init__(self, fail: bool = False) -> None:
        self.received: list[dict[str, Any]] = []
        self._fail = fail

    async def send_json(self, data: Any) -> None:
        if self._fail:
            raise RuntimeError("socket is gone")
        self.received.append(data)


class TestRoomConnectionRegistry:
    def test_new_registry_has_no_connections(self) -> None:
        assert RoomConnectionRegistry().connections_for("ABC234") == ()

    def test_add_then_lookup_returns_connection(self) -> None:
        registry = RoomConnectionRegistry()
        sink = RecordingSink()

        registry.add("ABC234", sink)

        assert registry.connections_for("ABC234") == (sink,)

    def test_lookup_normalizes_room_code(self) -> None:
        registry = RoomConnectionRegistry()
        sink = RecordingSink()

        registry.add("  abc234 ", sink)

        assert registry.connections_for("ABC234") == (sink,)

    def test_remove_drops_only_that_connection(self) -> None:
        registry = RoomConnectionRegistry()
        first, second = RecordingSink(), RecordingSink()
        registry.add("ABC234", first)
        registry.add("ABC234", second)

        registry.remove("ABC234", first)

        assert registry.connections_for("ABC234") == (second,)

    def test_remove_unknown_connection_is_ignored(self) -> None:
        registry = RoomConnectionRegistry()
        registry.add("ABC234", RecordingSink())

        registry.remove("ABC234", RecordingSink())
        registry.remove("ZZZZZ2", RecordingSink())

        assert len(registry.connections_for("ABC234")) == 1

    def test_same_player_may_hold_multiple_connections(self) -> None:
        """No player_id keying: the registry defines no replacement policy."""
        registry = RoomConnectionRegistry()
        first, second = RecordingSink(), RecordingSink()

        registry.add("ABC234", first)
        registry.add("ABC234", second)

        assert registry.connections_for("ABC234") == (first, second)

    def test_broadcast_reaches_every_connection_in_the_room(self) -> None:
        registry = RoomConnectionRegistry()
        first, second, other_room = RecordingSink(), RecordingSink(), RecordingSink()
        registry.add("ABC234", first)
        registry.add("ABC234", second)
        registry.add("DEF567", other_room)

        delivered = asyncio.run(registry.broadcast("abc234", {"event": "question.started"}))

        assert delivered == 2
        assert first.received == [{"event": "question.started"}]
        assert second.received == [{"event": "question.started"}]
        assert other_room.received == []

    def test_broadcast_to_empty_room_delivers_nothing(self) -> None:
        assert asyncio.run(RoomConnectionRegistry().broadcast("ABC234", {"event": "x"})) == 0

    def test_failing_sink_is_dropped_without_blocking_others(self) -> None:
        registry = RoomConnectionRegistry()
        broken, healthy = RecordingSink(fail=True), RecordingSink()
        registry.add("ABC234", broken)
        registry.add("ABC234", healthy)

        delivered = asyncio.run(registry.broadcast("ABC234", {"event": "x"}))

        assert delivered == 1
        assert healthy.received == [{"event": "x"}]
        assert registry.connections_for("ABC234") == (healthy,)
