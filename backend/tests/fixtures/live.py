"""Helpers for driving the live app over REST + WebSocket in integration tests.

Plain functions, not fixtures — import them directly. They encode the wire
protocol (subprotocol credentials, envelopes, a valid §9.2 profile) in one
place so individual tests stay focused on behavior.
"""

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

import anyio
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

PLAYER_PROTOCOL = "mizemi.player"
HOST_PROTOCOL = "mizemi.host"
CLIENT_TIMESTAMP = "2026-09-11T10:00:00.000Z"
RECEIVE_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class CreatedRoom:
    room_code: str
    game_id: str
    host_token: str


@dataclass(frozen=True)
class JoinedPlayer:
    player_id: str
    player_token: str
    display_name: str


def create_room(client: TestClient, config: dict | None = None) -> CreatedRoom:
    response = client.post("/api/v1/rooms", **({"json": config} if config is not None else {}))
    assert response.status_code == 201, response.text
    body = response.json()
    return CreatedRoom(body["room_code"], body["game_id"], body["host_token"])


def join(client: TestClient, room_code: str, display_name: str) -> JoinedPlayer:
    response = client.post(
        f"/api/v1/rooms/{room_code}/players", json={"display_name": display_name}
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return JoinedPlayer(body["player"]["player_id"], body["player_token"], display_name)


def player_ws(client: TestClient, room_code: str, player: JoinedPlayer, **kwargs: Any):
    return client.websocket_connect(
        f"/ws/rooms/{room_code}?player_id={player.player_id}",
        subprotocols=[PLAYER_PROTOCOL, player.player_token],
        **kwargs,
    )


def host_ws(client: TestClient, room: CreatedRoom, **kwargs: Any):
    return client.websocket_connect(
        f"/ws/rooms/{room.room_code}/host",
        subprotocols=[HOST_PROTOCOL, room.host_token],
        **kwargs,
    )


def envelope(event: str, payload: dict[str, Any], game_id: str) -> dict[str, Any]:
    return {"event": event, "payload": payload, "timestamp": CLIENT_TIMESTAMP, "game_id": game_id}


def profile_fields(**values: Any) -> list[dict[str, Any]]:
    """A valid §9.2 field list; keyword overrides replace or add values."""
    base: dict[str, Any] = {
        "city": "Haifa",
        "favorite_food": "pizza",
        "hobby": "chess",
        "favorite_music": "Rock",
    }
    base.update(values)
    return [
        {"field_key": key, "value": value, "allow_question_usage": True}
        for key, value in base.items()
    ]


def profile_payload(player_id: str, **values: Any) -> dict[str, Any]:
    return {"player_id": player_id, "fields": profile_fields(**values)}


def receive_json(ws: Any, *, timeout: float = RECEIVE_TIMEOUT_SECONDS) -> dict[str, Any]:
    """``ws.receive_json()`` with a timeout, so a missing event fails fast.

    Starlette's test session blocks forever on ``receive``; this reads the
    same underlying stream through the session's portal under
    ``anyio.fail_after`` and mirrors its close handling.
    """

    async def _receive() -> Any:
        with anyio.fail_after(timeout):
            return await ws._send_rx.receive()

    message = ws.portal.call(_receive)
    if message["type"] == "websocket.close":
        raise WebSocketDisconnect(message.get("code", 1000), message.get("reason"))
    return json.loads(message["text"])


def receive_until(ws: Any, event: str, *, limit: int = 80) -> dict[str, Any]:
    """Read messages until one with ``event`` arrives; fail loudly otherwise."""
    seen: list[str] = []
    for _ in range(limit):
        message = receive_json(ws)
        if message["event"] == event:
            return message
        seen.append(message["event"])
    raise AssertionError(f"no {event!r} within {limit} messages; saw {seen}")


def collect_until(ws: Any, event: str, *, limit: int = 80) -> list[dict[str, Any]]:
    """Every message up to and including the first ``event``."""
    messages: list[dict[str, Any]] = []
    for _ in range(limit):
        message = receive_json(ws)
        messages.append(message)
        if message["event"] == event:
            return messages
    raise AssertionError(f"no {event!r} within {limit} messages")


def wait_for_snapshot(
    ws: Any, predicate: Callable[[dict[str, Any]], bool], *, limit: int = 80
) -> dict[str, Any]:
    """Read ``room.updated`` snapshots until ``predicate(payload)`` holds."""
    for _ in range(limit):
        snapshot = receive_until(ws, "room.updated")
        if predicate(snapshot["payload"]):
            return snapshot
    raise AssertionError("no matching room.updated snapshot")


def submit_profile_and_ready(
    ws: Any, game_id: str, player: JoinedPlayer, **values: Any
) -> None:
    ws.send_json(envelope("player.profile_submit", profile_payload(player.player_id, **values), game_id))
    ws.send_json(envelope("player.ready", {}, game_id))


def distinct_profiles(names: Iterable[str]) -> dict[str, dict[str, Any]]:
    """Per-player profile values with enough variety to generate questions."""
    cities = ["Haifa", "Tel Aviv", "Haifa", "Eilat", "Jerusalem", "Haifa"]
    foods = ["pizza", "sushi", "pizza", "falafel", "pizza", "hummus"]
    hobbies = ["chess", "running", "guitar", "chess", "painting", "surfing"]
    music = ["Rock", "Pop", "Rock", "Jazz", "Pop", "Rock"]
    return {
        name: {
            "city": cities[i % len(cities)],
            "favorite_food": foods[i % len(foods)],
            "hobby": hobbies[i % len(hobbies)],
            "favorite_music": music[i % len(music)],
        }
        for i, name in enumerate(names)
    }
