"""Game domain aggregate (MASTER_SPEC.md §8, §11).

Pure domain layer: no FastAPI, SQLAlchemy, Pydantic, or IO imports allowed.

The aggregate owns identity, state, players, the question sequence, the
answers submitted to each question, and every player's cumulative score
(§8). Time is always supplied by the caller — the domain never reads a
clock — so deadline checks and speed scoring stay deterministic and
testable. ``transition_to`` remains the only mutation path for state.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta

from app.domain.game.answer import (
    Answer,
    AnswerRejectedError,
    AnswerRejection,
    PlayerRoundResult,
    RoundResult,
)
from app.domain.game.player import Player
from app.domain.game.profile import PlayerProfile
from app.domain.game.state import GameState, GameStateMachine

# Imported from the module, not the questions package: the package __init__
# pulls in dataset.py, which imports app.domain.game — a circular import.
from app.domain.questions.question import Question
from app.domain.scoring.policy import ScoringPolicy

_PRE_GAME_STATES = (GameState.LOBBY, GameState.PROFILE_COLLECTION, GameState.READY)


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
    """Aggregate root for one game: owns its state, players, answers and scores.

    Policies the domain does not own (display-name rules, room capacity,
    host authorization, configuration values) are enforced by the
    application layer before it calls in.
    """

    def __init__(self, game_id: str) -> None:
        self._game_id = game_id
        self._state = GameState.LOBBY
        self._players: dict[str, Player] = {}
        self._state_machine = GameStateMachine()
        self._questions: tuple[Question, ...] = ()
        self._current_question_index: int | None = None
        self._question_opened_at: datetime | None = None
        # question_id -> player_id -> Answer, both in insertion order.
        self._answers: dict[str, dict[str, Answer]] = {}
        # player_id -> cumulative score, in join order.
        self._scores: dict[str, int] = {}
        self._last_round: RoundResult | None = None

    # --- read model -------------------------------------------------------

    @property
    def game_id(self) -> str:
        return self._game_id

    @property
    def state(self) -> GameState:
        return self._state

    @property
    def players(self) -> tuple[Player, ...]:
        return tuple(self._players.values())

    @property
    def questions(self) -> tuple[Question, ...]:
        return self._questions

    @property
    def current_question(self) -> Question | None:
        if self._current_question_index is None:
            return None
        return self._questions[self._current_question_index]

    @property
    def current_question_index(self) -> int | None:
        return self._current_question_index

    @property
    def question_opened_at(self) -> datetime | None:
        """Server time the current question opened, if the caller supplied it."""
        return self._question_opened_at

    @property
    def question_deadline(self) -> datetime | None:
        """When the current question stops accepting answers, if known."""
        question = self.current_question
        if question is None or self._question_opened_at is None:
            return None
        return self._question_opened_at + timedelta(seconds=question.time_limit_seconds)

    @property
    def scores(self) -> dict[str, int]:
        """A copy of every player's cumulative score, in join order."""
        return dict(self._scores)

    @property
    def last_round(self) -> RoundResult | None:
        """The result of the most recently closed question, if any."""
        return self._last_round

    def score_of(self, player_id: str) -> int:
        return self._scores.get(player_id, 0)

    def get_player(self, player_id: str) -> Player | None:
        return self._players.get(player_id)

    def answers_for(self, question_id: str) -> tuple[Answer, ...]:
        return tuple(self._answers.get(question_id, {}).values())

    def answer_for(self, question_id: str, player_id: str) -> Answer | None:
        return self._answers.get(question_id, {}).get(player_id)

    def all_players_answered(self) -> bool:
        """True when every current player answered the active question."""
        question = self.current_question
        if self._state is not GameState.QUESTION_ACTIVE or question is None:
            return False
        answered = self._answers.get(question.question_id, {})
        return bool(self._players) and all(
            player_id in answered for player_id in self._players
        )

    # --- pre-game ---------------------------------------------------------

    def add_player(self, player: Player) -> None:
        if player.player_id in self._players:
            raise ValueError(f"player_id already in game: {player.player_id}")
        self._players[player.player_id] = player
        self._scores[player.player_id] = 0
        if self._state is GameState.READY:
            # Readiness describes the current roster, not a closed lobby.
            # Only the host starting play closes admission to the room.
            self.transition_to(GameState.PROFILE_COLLECTION)

    def remove_player(self, player_id: str) -> None:
        """Remove a player before the game starts (host moderation).

        Allowed only in LOBBY / PROFILE_COLLECTION / READY. If the remaining
        players in PROFILE_COLLECTION are all ready, the removal completes the
        readiness condition and the game moves to READY (§11).
        """
        if self._state not in _PRE_GAME_STATES:
            raise ValueError(f"players cannot be removed in state {self._state.value}")
        if player_id not in self._players:
            raise ValueError(f"unknown player_id: {player_id}")
        del self._players[player_id]
        self._scores.pop(player_id, None)
        if (
            self._state is GameState.PROFILE_COLLECTION
            and self._players
            and all(p.is_ready for p in self._players.values())
        ):
            self.transition_to(GameState.READY)

    def transition_to(self, target: GameState) -> None:
        if not self._state_machine.is_transition_allowed(self._state, target):
            raise InvalidStateTransitionError(self._state, target)
        self._state = target

    def submit_initial_profile(self, player_id: str, profile: PlayerProfile) -> None:
        """Accept a player's first profile submission (MASTER_SPEC.md §11).

        Structurally accepted only in LOBBY or PROFILE_COLLECTION; the first
        accepted profile auto-transitions LOBBY -> PROFILE_COLLECTION. Field
        validation against the §9.2 schema happens upstream. Every rejection
        leaves the game and its players unchanged.
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

        Allowed only in PROFILE_COLLECTION, requires a submitted profile, and
        is idempotent. The denominator is every player in the game —
        ``connected`` does not affect the calculation.
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

    # --- gameplay ---------------------------------------------------------

    def start(
        self, questions: Sequence[Question], *, opened_at: datetime | None = None
    ) -> None:
        """Start the game with an already-generated question set (§11).

        ``opened_at`` is the server time the first question opens; supplying
        it enables the answer deadline and speed scoring. Validation precedes
        the transition, so a failed start leaves the aggregate untouched and
        QUESTION_ACTIVE is unreachable without a real active question.
        """
        question_tuple = tuple(questions)
        if not question_tuple:
            raise ValueError("cannot start a game with no questions")
        _require_aware(opened_at)
        self.transition_to(GameState.QUESTION_ACTIVE)
        self._questions = question_tuple
        self._current_question_index = 0
        self._question_opened_at = opened_at

    def submit_answer(
        self,
        player_id: str,
        question_id: str,
        option_id: str,
        answered_at: datetime,
    ) -> Answer:
        """Record one answer to the active question (§9.4).

        ``answered_at`` is the server receive time. Raises
        ``AnswerRejectedError`` — leaving the game unchanged — when no
        question is active, the id is not the active question, the player is
        unknown, the option does not exist, the player already answered, or
        the deadline has passed.
        """
        _require_aware(answered_at)
        question = self.current_question
        if self._state is not GameState.QUESTION_ACTIVE or question is None:
            raise AnswerRejectedError(AnswerRejection.QUESTION_NOT_ACTIVE)
        if question_id != question.question_id:
            raise AnswerRejectedError(AnswerRejection.WRONG_QUESTION)
        if player_id not in self._players:
            raise AnswerRejectedError(AnswerRejection.UNKNOWN_PLAYER)
        if option_id not in {option.option_id for option in question.options}:
            raise AnswerRejectedError(AnswerRejection.INVALID_OPTION)
        answered = self._answers.get(question.question_id, {})
        if player_id in answered:
            raise AnswerRejectedError(AnswerRejection.ALREADY_ANSWERED)
        deadline = self.question_deadline
        if deadline is not None and answered_at > deadline:
            raise AnswerRejectedError(AnswerRejection.DEADLINE_PASSED)

        answer = Answer(
            player_id=player_id,
            question_id=question.question_id,
            option_id=option_id,
            answered_at=answered_at,
        )
        self._answers.setdefault(question.question_id, {})[player_id] = answer
        return answer

    def close_question(self, scoring: ScoringPolicy) -> RoundResult:
        """End the active question: QUESTION_ACTIVE -> QUESTION_RESULTS (§11).

        Scores every current player (0 for no answer) with ``scoring`` and
        adds the points to their cumulative score. Points are computed before
        the transition and applied after it, so a rejected close changes
        nothing. Closing when no question is active raises
        ``InvalidStateTransitionError``.
        """
        question = self.current_question
        if self._state is not GameState.QUESTION_ACTIVE or question is None:
            raise InvalidStateTransitionError(self._state, GameState.QUESTION_RESULTS)

        answered = self._answers.get(question.question_id, {})
        results: list[PlayerRoundResult] = []
        for player_id in self._players:
            answer = answered.get(player_id)
            if answer is None:
                results.append(
                    PlayerRoundResult(
                        player_id=player_id,
                        option_id=None,
                        is_correct=False,
                        points_awarded=0,
                    )
                )
                continue
            is_correct = answer.option_id == question.correct_option_id
            points = scoring.points_for(
                is_correct=is_correct,
                answered_at=answer.answered_at,
                # Without a known opening time there is no speed signal; treat
                # the answer as instant so correct answers still score.
                opened_at=self._question_opened_at or answer.answered_at,
                time_limit_seconds=question.time_limit_seconds,
            )
            if points < 0:
                raise ValueError("a scoring policy returned negative points")
            results.append(
                PlayerRoundResult(
                    player_id=player_id,
                    option_id=answer.option_id,
                    is_correct=is_correct,
                    points_awarded=points,
                )
            )

        self.transition_to(GameState.QUESTION_RESULTS)
        for result in results:
            self._scores[result.player_id] = (
                self._scores.get(result.player_id, 0) + result.points_awarded
            )
        self._last_round = RoundResult(
            question=question,
            answers=tuple(answered.values()),
            player_results=tuple(results),
        )
        return self._last_round

    def show_leaderboard(self) -> None:
        """QUESTION_RESULTS -> LEADERBOARD (§11)."""
        self.transition_to(GameState.LEADERBOARD)

    def advance_to_next_question(self, *, opened_at: datetime | None = None) -> None:
        """Advance past the leaderboard: next question, or game over (§11).

        Owns only the two LEADERBOARD exits — QUESTION_ACTIVE when another
        question exists (opening at ``opened_at``), FINISHED when the final
        question was played. Every rejection leaves the aggregate untouched.
        """
        if self._state is not GameState.LEADERBOARD:
            raise ValueError(f"cannot advance from state {self._state.value}")
        if self._current_question_index is None:
            raise ValueError("no question sequence is in progress")
        _require_aware(opened_at)
        next_index = self._current_question_index + 1
        if next_index < len(self._questions):
            self.transition_to(GameState.QUESTION_ACTIVE)
            self._current_question_index = next_index
            self._question_opened_at = opened_at
        else:
            self.transition_to(GameState.FINISHED)
            self._current_question_index = None
            self._question_opened_at = None


def _require_aware(value: datetime | None) -> None:
    if value is not None and value.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
