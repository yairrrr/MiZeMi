"""Join-player use case (MASTER_SPEC.md §9.1, §11, §13 — first vertical).

Application layer: orchestrates domain and infrastructure; no FastAPI or
Pydantic imports. Transport mapping of the exceptions raised here (and of
the registry's RoomNotFoundError) happens at the API boundary.
"""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from app.domain.game import GameState, Player
from app.infrastructure.credentials import CredentialStore, issue_token
from app.infrastructure.rooms import RoomRegistry

JOINABLE_STATES = (GameState.LOBBY, GameState.PROFILE_COLLECTION)
MAX_DISPLAY_NAME_LENGTH = 20


def generate_player_id() -> str:
    """UUID4 string — the approved MVP id implementation; opaque on the wire."""
    return str(uuid4())


class InvalidDisplayNameError(Exception):
    """display_name is empty after trimming or longer than 20 characters."""


class NameTakenError(Exception):
    """The trimmed display_name is already used in this room (case-insensitive)."""


class RoomFullError(Exception):
    """The room already holds the configured maximum number of players."""


class RoomNotJoinableError(Exception):
    """The game is not in a joinable state (LOBBY / PROFILE_COLLECTION)."""

    def __init__(self, state: GameState) -> None:
        super().__init__(f"game not joinable in state {state.value}")
        self.state = state


@dataclass(frozen=True)
class JoinPlayerResult:
    """Transport-independent outcome from one authoritative room resolution."""

    game_id: str
    player: Player
    # The player's bearer credential for the WebSocket (§14.1); returned only
    # to the joining client. None when the service has no CredentialStore.
    player_token: str | None = None


class JoinPlayerService:
    """Joins a new player to an active room through the domain's own APIs."""

    def __init__(
        self,
        registry: RoomRegistry,
        player_id_generator: Callable[[], str] | None = None,
        *,
        credentials: CredentialStore | None = None,
        token_generator: Callable[[], str] | None = None,
        max_players: int | None = None,
    ) -> None:
        self._registry = registry
        # Late-bound default keeps the generator patchable in tests.
        self._generate_player_id = (
            player_id_generator if player_id_generator is not None else generate_player_id
        )
        self._credentials = credentials
        self._generate_token = token_generator if token_generator is not None else issue_token
        self._max_players = max_players

    def join(self, room_code: str, display_name: str) -> JoinPlayerResult:
        room = self._registry.get(room_code)  # RoomNotFoundError propagates
        game = room.game
        if game.state not in JOINABLE_STATES:
            raise RoomNotJoinableError(game.state)

        name = display_name.strip()
        if not name or len(name) > MAX_DISPLAY_NAME_LENGTH:
            raise InvalidDisplayNameError(
                f"display_name must be 1-{MAX_DISPLAY_NAME_LENGTH} characters after trimming"
            )
        if self._max_players is not None and len(game.players) >= self._max_players:
            raise RoomFullError()
        normalized = name.casefold()
        if any(
            player.display_name.strip().casefold() == normalized
            for player in game.players
        ):
            raise NameTakenError(name)

        player = Player(player_id=self._generate_player_id(), display_name=name)
        room.join(player)
        player_token: str | None = None
        if self._credentials is not None:
            player_token = self._generate_token()
            self._credentials.register_player(room.room_code, player.player_id, player_token)
        return JoinPlayerResult(game_id=game.game_id, player=player, player_token=player_token)
