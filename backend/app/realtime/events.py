"""Realtime event name registries (MASTER_SPEC.md §14.2).

Pure wire-contract layer: no domain, transport, or application imports.
The values are shared contract — changing them requires the §21 process
and a matching frontend change (frontend/src/types/realtime.ts).
"""

from enum import Enum, unique


@unique
class ClientToServerEvent(Enum):
    """Client-sent intents (MASTER_SPEC.md §14.2)."""

    PLAYER_JOIN = "player.join"
    PLAYER_PROFILE_SUBMIT = "player.profile_submit"
    PLAYER_READY = "player.ready"
    GAME_START = "game.start"
    ANSWER_SUBMIT = "answer.submit"
    GAME_NEXT = "game.next"


@unique
class ServerToClientEvent(Enum):
    """Server-sent facts (MASTER_SPEC.md §14.2)."""

    ROOM_UPDATED = "room.updated"
    PLAYER_JOINED = "player.joined"
    PLAYER_UPDATED = "player.updated"
    GAME_STARTED = "game.started"
    QUESTION_STARTED = "question.started"
    ANSWER_ACCEPTED = "answer.accepted"
    QUESTION_ENDED = "question.ended"
    STATISTICS_UPDATED = "statistics.updated"
    LEADERBOARD_UPDATED = "leaderboard.updated"
    GAME_FINISHED = "game.finished"
    ERROR = "error"
