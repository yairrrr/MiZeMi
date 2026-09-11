"""Unit tests for GameState and structural transition rules (MASTER_SPEC.md §11).

Structural legality only — trigger conditions (readiness, timers, question
availability, host authorization) are deferred orchestration concerns and
are deliberately not tested here.
"""

import pytest

from app.domain.game import GameState, GameStateMachine

APPROVED_STATE_NAMES = {
    "LOBBY",
    "PROFILE_COLLECTION",
    "READY",
    "QUESTION_ACTIVE",
    "QUESTION_RESULTS",
    "LEADERBOARD",
    "FINISHED",
}

ALLOWED_TRANSITIONS = [
    (GameState.LOBBY, GameState.PROFILE_COLLECTION),
    (GameState.PROFILE_COLLECTION, GameState.READY),
    (GameState.READY, GameState.QUESTION_ACTIVE),
    (GameState.READY, GameState.PROFILE_COLLECTION),
    (GameState.QUESTION_ACTIVE, GameState.QUESTION_RESULTS),
    (GameState.QUESTION_RESULTS, GameState.LEADERBOARD),
    (GameState.LEADERBOARD, GameState.QUESTION_ACTIVE),
    (GameState.LEADERBOARD, GameState.FINISHED),
]

REJECTED_TRANSITION_EXAMPLES = [
    (GameState.LOBBY, GameState.QUESTION_ACTIVE),
    (GameState.READY, GameState.FINISHED),
    (GameState.QUESTION_ACTIVE, GameState.LOBBY),
    (GameState.FINISHED, GameState.LOBBY),
    (GameState.FINISHED, GameState.QUESTION_ACTIVE),
    (GameState.PROFILE_COLLECTION, GameState.QUESTION_ACTIVE),
    (GameState.QUESTION_RESULTS, GameState.QUESTION_ACTIVE),
]


def test_game_state_has_exactly_the_seven_approved_states() -> None:
    assert {state.name for state in GameState} == APPROVED_STATE_NAMES


def test_game_state_values_match_names_verbatim() -> None:
    assert all(state.value == state.name for state in GameState)


class TestGameStateMachine:
    @pytest.mark.parametrize(("current", "target"), ALLOWED_TRANSITIONS)
    def test_allowed_transition_is_accepted(self, current: GameState, target: GameState) -> None:
        assert GameStateMachine().is_transition_allowed(current, target) is True

    @pytest.mark.parametrize(("current", "target"), REJECTED_TRANSITION_EXAMPLES)
    def test_invalid_transition_is_rejected(self, current: GameState, target: GameState) -> None:
        assert GameStateMachine().is_transition_allowed(current, target) is False

    @pytest.mark.parametrize("state", list(GameState))
    def test_self_transition_is_rejected(self, state: GameState) -> None:
        assert GameStateMachine().is_transition_allowed(state, state) is False

    def test_finished_is_terminal(self) -> None:
        machine = GameStateMachine()

        assert not any(
            machine.is_transition_allowed(GameState.FINISHED, target) for target in GameState
        )
