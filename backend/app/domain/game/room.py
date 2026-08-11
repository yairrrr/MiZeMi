"""Room domain object (MASTER_SPEC.md §8).

Pure domain layer: no FastAPI, SQLAlchemy, Pydantic, or IO imports allowed.
"""

from app.domain.game.game import Game
from app.domain.game.player import Player


class Room:
    """The addressable, joinable session: pairs a room_code with its one Game.

    ``room_code`` is opaque here — format, generation, and cross-room
    uniqueness are deferred (registry/application concerns). Room owns no
    state, players, host, or capacity: the Game aggregate owns gameplay
    state, and the deferred join policies (allowed states, capacity, name
    rules, host authorization) are gated by the application layer before
    ``join`` is called.
    """

    def __init__(self, room_code: str, game: Game) -> None:
        self._room_code = room_code
        self._game = game

    @property
    def room_code(self) -> str:
        return self._room_code

    @property
    def game(self) -> Game:
        return self._game

    def join(self, player: Player) -> None:
        self._game.add_player(player)
