"""Game domain aggregate (MASTER_SPEC.md §8, §11).

Pure domain layer: no FastAPI, SQLAlchemy, Pydantic, or IO imports allowed.

The aggregate currently owns identity, state, and players only; the question
sequence, answers, and scores are added once their owning workstreams (§7)
deliver those types.
"""

from app.domain.game.player import Player
from app.domain.game.profile import PlayerProfile
from app.domain.game.state import GameState, GameStateMachine


class InvalidStateTransitionError(Exception):
    """A structurally illegal GameState transition was attempted.

    Maps to the ``INVALID_STATE_TRANSITION`` error code at the presentation
    boundary; carries no HTTP or wire-format concerns itself.
    """

    def __init__(self, current: GameState, target: GameState) -> None:
        super().__init__(f"illegal transition: {current.value} -> {target.value}")
        self.current = current
        self.target = target


class Game:
    """Aggregate root for one game: owns its state and players.

    ``transition_to`` is the only mutation path for state. Deferred policies
    (room capacity, display-name uniqueness, joining/late-join states, host
    rules, readiness conditions) are deliberately not enforced here — the
    application layer gates those before calling.
    """

    def __init__(self, game_id: str) -> None:
        self._game_id = game_id
        self._state = GameState.LOBBY
        self._players: dict[str, Player] = {}
        self._state_machine = GameStateMachine()

    @property
    def game_id(self) -> str:
        return self._game_id

    @property
    def state(self) -> GameState:
        return self._state

    @property
    def players(self) -> tuple[Player, ...]:
        return tuple(self._players.values())

    def add_player(self, player: Player) -> None:
        if player.player_id in self._players:
            raise ValueError(f"player_id already in game: {player.player_id}")
        self._players[player.player_id] = player

    def get_player(self, player_id: str) -> Player | None:
        return self._players.get(player_id)

    def transition_to(self, target: GameState) -> None:
        if not self._state_machine.is_transition_allowed(self._state, target):
            raise InvalidStateTransitionError(self._state, target)
        self._state = target

    def submit_initial_profile(self, player_id: str, profile: PlayerProfile) -> None:
        """Accept a player's first profile submission (MASTER_SPEC.md §11).

        Structurally accepted only in LOBBY or PROFILE_COLLECTION; the first
        accepted profile auto-transitions LOBBY -> PROFILE_COLLECTION.
        Field validation against the final profile schema is deferred and
        happens upstream once defined. Every rejection leaves the game and
        its players unchanged.
        """
        if self._state not in (GameState.LOBBY, GameState.PROFILE_COLLECTION):
            raise ValueError(
                f"profile submission not accepted in state {self._state.value}"
            )
        player = self._players.get(player_id)
        if player is None:
            raise ValueError(f"unknown player_id: {player_id}")
        player.assign_initial_profile(profile)
        if self._state is GameState.LOBBY:
            self.transition_to(GameState.PROFILE_COLLECTION)

    def mark_player_ready(self, player_id: str) -> None:
        """Mark a player ready; transition to READY once everyone is (§11).

        Approved MVP readiness contract: allowed only in PROFILE_COLLECTION,
        requires a submitted profile, idempotent, and no unready operation
        exists. The denominator is every player in the game — ``connected``
        does not affect the calculation. Late-join behavior after READY
        remains deferred.
        """
        if self._state is not GameState.PROFILE_COLLECTION:
            raise ValueError(f"readiness not accepted in state {self._state.value}")
        player = self._players.get(player_id)
        if player is None:
            raise ValueError(f"unknown player_id: {player_id}")
        if not player.has_profile:
            raise ValueError(f"player {player_id!r} has no profile")
        player.is_ready = True
        if all(p.is_ready for p in self._players.values()):
            self.transition_to(GameState.READY)
