"""Sanity tests for the shared test builders (tests/fixtures/factories.py).

They exist so a domain change that breaks a builder fails here, loudly, once
— instead of in every test that uses it.
"""

import pytest

from app.domain.game import GameState
from app.domain.questions import ProfileDataset
from app.domain.statistics import QuestionStatisticsCalculator
from tests.fixtures.factories import (
    answers_from_counts,
    collect_profiles,
    make_dataset,
    make_game,
    make_player,
    make_players,
    make_profile,
    make_question,
    make_ready_game,
    ready_all,
)


class TestPlayersAndProfiles:
    def test_make_player_defaults_are_a_valid_disconnected_player(self) -> None:
        player = make_player()
        assert player.player_id == "p1"
        assert player.connected is False
        assert player.has_profile is False

    def test_make_player_can_carry_a_profile(self) -> None:
        player = make_player("p9", profile=make_profile("p9"))
        assert player.has_profile is True

    def test_make_players_gives_distinct_ids_and_names(self) -> None:
        players = make_players(4)
        assert [p.player_id for p in players] == ["p1", "p2", "p3", "p4"]
        assert len({p.display_name for p in players}) == 4

    def test_make_players_rejects_more_than_the_name_pool(self) -> None:
        with pytest.raises(ValueError):
            make_players(50)

    def test_profile_consent_flag_is_honoured(self) -> None:
        withheld = make_profile("p1", allow_question_usage=False)
        assert withheld.consented_fields() == ()


class TestGame:
    def test_make_game_starts_in_lobby_with_players(self) -> None:
        game = make_game()
        assert game.state is GameState.LOBBY
        assert len(game.players) == 3

    def test_collect_profiles_moves_to_profile_collection(self) -> None:
        game = collect_profiles(make_game())
        assert game.state is GameState.PROFILE_COLLECTION
        assert all(p.has_profile for p in game.players)

    def test_ready_all_after_profiles_reaches_ready(self) -> None:
        game = ready_all(collect_profiles(make_game()))
        assert game.state is GameState.READY

    def test_make_ready_game_is_in_ready(self) -> None:
        assert make_ready_game().state is GameState.READY


class TestQuestionsDatasetsAnswers:
    def test_make_question_is_a_valid_multiple_choice_question(self) -> None:
        question = make_question(correct_option_id="c")
        assert question.correct_option_id == "c"
        assert [o.option_id for o in question.options] == ["a", "b", "c", "d"]

    def test_make_dataset_is_a_profile_dataset_with_consented_fields(self) -> None:
        dataset = make_dataset()
        assert isinstance(dataset, ProfileDataset)
        assert dataset.player_count == 4
        assert "favorite_food" in dataset.field_keys

    def test_answers_from_counts_expands_in_order(self) -> None:
        assert answers_from_counts({"a": 2, "b": 3}) == ["a", "a", "b", "b", "b"]

    def test_answers_from_counts_rejects_negative(self) -> None:
        with pytest.raises(ValueError):
            answers_from_counts({"a": -1})

    def test_builders_compose_for_a_statistics_scenario(self) -> None:
        question = make_question(option_ids=("a", "b", "c"))
        stats = QuestionStatisticsCalculator().calculate(
            question, answers_from_counts({"a": 1, "b": 4}), player_count=6
        )
        assert stats.answered_count == 5
        assert stats.player_count == 6
        assert [e.count for e in stats.answer_distribution] == [1, 4, 0]
