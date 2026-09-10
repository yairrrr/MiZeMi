"""Aggregate answer statistics for a finished question (MASTER_SPEC.md §9.6).

Pure domain layer: no FastAPI, SQLAlchemy, Pydantic, or IO imports allowed.

Aggregate-only (§9.6, §10.6): this module counts answers per option and never
records, stores, or exposes which player chose what. It is deliberately
separate from scoring (§18) — points and leaderboards are not computed here.

The calculator is a pure function of its inputs: the finished ``Question`` and
the answers the caller decided should count (resubmission / late-answer policy
is deferred, §9.4). It does not read game state, so it can run — and be
tested — before any answer-persistence layer exists.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from app.domain.questions.question import Question


@dataclass(frozen=True)
class OptionCount:
    """How many counted answers selected one option (§9.6 ``answer_distribution``)."""

    option_id: str
    count: int


@dataclass(frozen=True)
class QuestionStatistics:
    """The §9.6 aggregate result for one finished question.

    ``answer_distribution`` lists every option on the question, in question
    order, including options nobody chose (count 0). It carries no per-player
    data by construction.
    """

    question_id: str
    correct_option_id: str
    answer_distribution: tuple[OptionCount, ...]
    answered_count: int
    player_count: int


class QuestionStatisticsCalculator:
    """Counts submitted answers per option for one finished question."""

    def calculate(
        self,
        question: Question,
        chosen_option_ids: Iterable[str],
        *,
        player_count: int,
    ) -> QuestionStatistics:
        """Aggregate ``chosen_option_ids`` into the §9.6 shape.

        ``chosen_option_ids`` is the flat set of answers that count — one
        entry per counted answer. ``player_count`` is the total number of
        players in the game (the denominator the frontend needs).

        Raises ``ValueError`` if an answer names an option the question does
        not have, if more answers are supplied than there are players, or if
        ``player_count`` is negative — all caller bugs, not user input.
        """
        if player_count < 0:
            raise ValueError("player_count cannot be negative")

        option_ids = tuple(option.option_id for option in question.options)
        counts: dict[str, int] = dict.fromkeys(option_ids, 0)

        answered_count = 0
        for option_id in chosen_option_ids:
            if option_id not in counts:
                raise ValueError(
                    f"answer references unknown option_id {option_id!r}"
                )
            counts[option_id] += 1
            answered_count += 1

        if answered_count > player_count:
            raise ValueError(
                f"answered_count ({answered_count}) exceeds "
                f"player_count ({player_count})"
            )

        distribution = tuple(
            OptionCount(option_id=option_id, count=counts[option_id])
            for option_id in option_ids
        )
        return QuestionStatistics(
            question_id=question.question_id,
            correct_option_id=question.correct_option_id,
            answer_distribution=distribution,
            answered_count=answered_count,
            player_count=player_count,
        )
