"""Shared builders for domain objects used across tests (MASTER_SPEC.md §19).

Plain functions with sensible defaults and keyword overrides — deliberately
not a factory framework. They keep tests readable without hiding what a test
actually depends on: a test that cares about a value passes it explicitly;
everything else gets a boring default.

Nothing here is a pytest fixture — import the builders directly:

    from tests.fixtures.factories import make_player, make_game, ready_all
"""

from collections.abc import Iterable, Mapping, Sequence

from app.domain.game import Game, GameState, Player, PlayerProfile, ProfileField
from app.domain.questions import (
    ProfileDataset,
    Question,
    QuestionOption,
    QuestionType,
)

# --- profiles ---------------------------------------------------------------

_DEFAULT_FIELDS: tuple[tuple[str, str | int], ...] = (
    ("age", 27),
    ("city", "Haifa"),
    ("favorite_food", "pizza"),
    ("hobby", "rock climbing"),
)


def make_profile_field(
    field_key: str = "favorite_food",
    value: str | int = "pizza",
    *,
    allow_question_usage: bool = True,
) -> ProfileField:
    return ProfileField(
        field_key=field_key, value=value, allow_question_usage=allow_question_usage
    )


def make_profile(
    player_id: str = "p1",
    *,
    fields: Iterable[ProfileField] | None = None,
    allow_question_usage: bool = True,
) -> PlayerProfile:
    """A profile with the four default fields, or an explicit field list.

    ``allow_question_usage`` sets the consent flag on the default fields; it
    is ignored when ``fields`` is given explicitly.
    """
    if fields is None:
        fields = tuple(
            make_profile_field(key, value, allow_question_usage=allow_question_usage)
            for key, value in _DEFAULT_FIELDS
        )
    return PlayerProfile(player_id=player_id, fields=tuple(fields))


# --- players ---------------------------------------------------------------

_DEFAULT_NAMES = (
    "Dana", "Omer", "Noa", "Yael", "Amit", "Tal", "Roni", "Gal", "Shira", "Ido",
)


def make_player(
    player_id: str = "p1",
    display_name: str = "Dana",
    *,
    connected: bool = False,
    is_ready: bool = False,
    profile: PlayerProfile | None = None,
) -> Player:
    player = Player(
        player_id=player_id,
        display_name=display_name,
        connected=connected,
        is_ready=is_ready,
    )
    if profile is not None:
        player.assign_initial_profile(profile)
    return player


def make_players(count: int, *, with_profiles: bool = False) -> list[Player]:
    """``count`` players with ids ``p1..pN`` and distinct display names."""
    if count > len(_DEFAULT_NAMES):
        raise ValueError(f"make_players supports up to {len(_DEFAULT_NAMES)} players")
    players = []
    for index in range(count):
        pid = f"p{index + 1}"
        players.append(
            make_player(
                pid,
                _DEFAULT_NAMES[index],
                profile=make_profile(pid) if with_profiles else None,
            )
        )
    return players


# --- game ------------------------------------------------------------------

def make_game(
    game_id: str = "g1",
    *,
    players: Iterable[Player] | None = None,
) -> Game:
    """A Game in ``LOBBY`` with the given players added (default: 3 players)."""
    game = Game(game_id=game_id)
    for player in players if players is not None else make_players(3):
        game.add_player(player)
    return game


def collect_profiles(game: Game, *, allow_question_usage: bool = True) -> Game:
    """Submit a profile for every player through the real domain path.

    Drives ``LOBBY -> PROFILE_COLLECTION`` (§11). Players that already have a
    profile are skipped. Returns the same game for chaining.
    """
    for player in game.players:
        if not player.has_profile:
            game.submit_initial_profile(
                player.player_id,
                make_profile(player.player_id, allow_question_usage=allow_question_usage),
            )
    return game


def ready_all(game: Game) -> Game:
    """Mark every player ready (§11). Requires profiles already submitted."""
    for player in game.players:
        game.mark_player_ready(player.player_id)
    return game


def make_ready_game(
    game_id: str = "g1",
    *,
    players: Iterable[Player] | None = None,
) -> Game:
    """A Game walked through profile collection to ``READY`` via domain calls."""
    game = make_game(game_id, players=players)
    collect_profiles(game)
    ready_all(game)
    assert game.state is GameState.READY
    return game


def start_game(
    game: Game,
    *,
    questions: Sequence[Question] | None = None,
    question_count: int = 3,
) -> Game:
    """Start a ``READY`` game (§11). Builds a placeholder question set if none
    is given. Returns the game in ``QUESTION_ACTIVE``.
    """
    if questions is None:
        questions = tuple(
            make_question(
                f"q{i + 1}",
                index=i,
                total_questions=question_count,
                text=f"Placeholder question {i + 1}?",
            )
            for i in range(question_count)
        )
    game.start(questions)
    return game


def play_to_finished(game: Game) -> Game:
    """Drive a started game to ``FINISHED`` through the public state machine.

    A test convenience for persistence/lifecycle tests — it walks
    QUESTION_ACTIVE -> QUESTION_RESULTS -> LEADERBOARD -> next|FINISHED using
    only public ``Game`` methods; it makes no gameplay decisions.
    """
    while game.state is not GameState.FINISHED:
        if game.state is GameState.QUESTION_ACTIVE:
            game.transition_to(GameState.QUESTION_RESULTS)
        elif game.state is GameState.QUESTION_RESULTS:
            game.transition_to(GameState.LEADERBOARD)
        elif game.state is GameState.LEADERBOARD:
            game.advance_to_next_question()
        else:  # pragma: no cover - unreachable for a started game
            raise AssertionError(f"cannot drive to FINISHED from {game.state}")
    return game


# --- questions ------------------------------------------------------------

def make_question(
    question_id: str = "q1",
    *,
    index: int = 0,
    total_questions: int = 1,
    text: str = "How many players picked pizza as their favorite food?",
    option_ids: Sequence[str] = ("a", "b", "c", "d"),
    correct_option_id: str | None = None,
    time_limit_seconds: int = 20,
) -> Question:
    correct = correct_option_id if correct_option_id is not None else option_ids[0]
    return Question(
        question_id=question_id,
        index=index,
        total_questions=total_questions,
        question_type=QuestionType.MULTIPLE_CHOICE,
        text=text,
        options=tuple(
            QuestionOption(option_id=oid, text=oid.upper()) for oid in option_ids
        ),
        correct_option_id=correct,
        time_limit_seconds=time_limit_seconds,
    )


# --- datasets & answer sets --------------------------------------------------

def make_dataset(players: Iterable[Player] | None = None) -> ProfileDataset:
    """A ProfileDataset from players that already carry profiles (default: 4)."""
    return ProfileDataset(
        players if players is not None else make_players(4, with_profiles=True)
    )


def answers_from_counts(counts: Mapping[str, int]) -> list[str]:
    """Expand ``{"a": 2, "b": 6}`` into ``["a", "a", "b", ...]``.

    A prepared answer set for statistics tests — order follows the mapping.
    """
    answers: list[str] = []
    for option_id, count in counts.items():
        if count < 0:
            raise ValueError(f"count for {option_id!r} cannot be negative")
        answers.extend([option_id] * count)
    return answers
