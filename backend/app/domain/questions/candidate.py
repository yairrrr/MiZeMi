"""Internal candidate value object for the Question Engine pipeline."""

from dataclasses import dataclass

from app.domain.questions.question import QuestionOption


@dataclass(frozen=True)
class QuestionCandidate:
    """A rule-produced question awaiting validation, scoring, and selection.

    Candidates intentionally do not enforce final-question correctness. The
    separate ``QuestionValidator`` must be able to receive and reject malformed
    or ambiguous candidates produced by a faulty rule.
    """

    text: str
    options: tuple[QuestionOption, ...]
    correct_option_id: str
    source_rule_id: str
    source_field_keys: tuple[str, ...]
    involved_player_ids: tuple[str, ...]
    metadata: tuple[tuple[str, str | int | float | bool], ...] = ()
