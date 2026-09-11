"""Original production rules, preserved and rendered in both game languages."""

from random import Random

from app.domain.questions.language import normalize, label, say

from app.domain.questions.candidate import QuestionCandidate
from app.domain.questions.dataset import ProfileDataset
from app.domain.questions.question import QuestionOption
from app.domain.questions.rule import QuestionRule

_OPTION_IDS = "abcd"
_MAX_DISTRACTORS = 3


def _label(field_key: str) -> str:
    return field_key.replace("_", " ")


def _render(value: str | int) -> str:
    """Quote free-text values; leave numbers bare ("is 27", "is \"pizza\"")."""
    return str(value) if isinstance(value, int) else f'"{value}"'


def _group_key(value: str | int) -> str | int:
    """Case/whitespace-insensitive identity, so "Pizza" and " pizza" match."""
    return normalize(value)


def _grouped(dataset: ProfileDataset, field_key: str) -> dict[str | int, list[str]]:
    """Group player_ids by normalized value, preserving dataset order.

    Keys are the first-seen original spelling, so generated text shows a
    value exactly as a player typed it while still matching equivalent
    spellings from other players.
    """
    display: dict[str | int, str | int] = {}
    groups: dict[str | int, list[str]] = {}
    for player_id, value in dataset.values_for(field_key):
        key = _group_key(value)
        if key not in groups:
            display[key] = value
            groups[key] = []
        groups[key].append(player_id)
    return {display[key]: player_ids for key, player_ids in groups.items()}


def _build_options(
    correct_text: str, distractor_texts: list[str], rng: Random
) -> tuple[tuple[QuestionOption, ...], str]:
    """Shuffle correct + distractors deterministically; return (options, correct id)."""
    flagged = [(correct_text, True)] + [(text, False) for text in distractor_texts]
    rng.shuffle(flagged)
    options = tuple(
        QuestionOption(option_id=_OPTION_IDS[position], text=text)
        for position, (text, _) in enumerate(flagged)
    )
    correct_option_id = next(
        option.option_id
        for option, (_, is_correct) in zip(options, flagged, strict=True)
        if is_correct
    )
    return options, correct_option_id


class UniqueValueRule(QuestionRule):
    """Uniqueness detection: who is the only player with this value? (§12.2).

    Questions are truthful relative to the consent-safe ProfileDataset only:
    non-consented values are intentionally invisible to generation and are
    not used even to suppress otherwise-valid questions — suppression would
    itself leak withheld data (§10).
    """

    @property
    def rule_id(self) -> str:
        return "unique_value"

    def generate(
        self, dataset: ProfileDataset, rng: Random
    ) -> tuple[QuestionCandidate, ...]:
        if dataset.player_count < 2:
            return ()
        candidates: list[QuestionCandidate] = []
        for field_key in dataset.field_keys:
            for value, holders in _grouped(dataset, field_key).items():
                if len(holders) != 1:
                    continue
                subject = holders[0]
                others = [pid for pid in dataset.player_ids if pid != subject]
                distractors = rng.sample(others, k=min(_MAX_DISTRACTORS, len(others)))
                options, correct_option_id = _build_options(
                    dataset.display_name_for(subject),
                    [dataset.display_name_for(pid) for pid in distractors],
                    rng,
                )
                candidates.append(
                    QuestionCandidate(
                        text=say(dataset.language, "Who is the only player whose {field} is {value}?", "מי המשתתף היחיד שהערך שלו בשדה {field} הוא {value}?", field=label(field_key, dataset.language), value=_render(value)),
                        options=options,
                        correct_option_id=correct_option_id,
                        source_rule_id=self.rule_id,
                        source_field_keys=(field_key,),
                        involved_player_ids=(subject, *distractors),
                    )
                )
        return tuple(candidates)


class MostCommonValueRule(QuestionRule):
    """Frequency analysis: which value is strictly the most common? (§12.2)."""

    @property
    def rule_id(self) -> str:
        return "most_common_value"

    def generate(
        self, dataset: ProfileDataset, rng: Random
    ) -> tuple[QuestionCandidate, ...]:
        candidates: list[QuestionCandidate] = []
        for field_key in dataset.field_keys:
            groups = _grouped(dataset, field_key)
            if len(groups) < 2:
                continue
            ranked = sorted(
                groups.items(), key=lambda item: (-len(item[1]), str(item[0]))
            )
            top_value, top_holders = ranked[0]
            # Exactly-one-correct requires a strict winner seen at least twice.
            if len(top_holders) < 2 or len(top_holders) == len(ranked[1][1]):
                continue
            distractor_values = [value for value, _ in ranked[1 : 1 + _MAX_DISTRACTORS]]
            options, correct_option_id = _build_options(
                str(top_value), [str(value) for value in distractor_values], rng
            )
            candidates.append(
                QuestionCandidate(
                    text=say(dataset.language, "What is the most common {field} in this group?", "מהו הערך הנפוץ ביותר בשדה {field} בקבוצה?", field=label(field_key, dataset.language)),
                    options=options,
                    correct_option_id=correct_option_id,
                    source_rule_id=self.rule_id,
                    source_field_keys=(field_key,),
                    involved_player_ids=tuple(top_holders),
                )
            )
        return tuple(candidates)


class ValueCountRule(QuestionRule):
    """Counts: how many players share this value? (§12.2)."""

    @property
    def rule_id(self) -> str:
        return "value_count"

    def generate(
        self, dataset: ProfileDataset, rng: Random
    ) -> tuple[QuestionCandidate, ...]:
        candidates: list[QuestionCandidate] = []
        for field_key in dataset.field_keys:
            for value, holders in _grouped(dataset, field_key).items():
                count = len(holders)
                nearby = [count - 1, count + 1, count - 2, count + 2]
                distractors = [
                    n for n in nearby if 0 <= n <= dataset.player_count and n != count
                ][:_MAX_DISTRACTORS]
                if not distractors:
                    continue
                options, correct_option_id = _build_options(
                    str(count), [str(n) for n in distractors], rng
                )
                candidates.append(
                    QuestionCandidate(
                        text=say(dataset.language, "How many players have {value} as their {field}?", "כמה משתתפים בחרו בערך {value} בשדה {field}?", field=label(field_key, dataset.language), value=_render(value)),
                        options=options,
                        correct_option_id=correct_option_id,
                        source_rule_id=self.rule_id,
                        source_field_keys=(field_key,),
                        involved_player_ids=tuple(holders),
                    )
                )
        return tuple(candidates)


def default_rules() -> tuple[QuestionRule, ...]:
    """The production rule registry — adding a rule means one entry here (§12.2)."""
    from app.domain.questions.advanced_rules import advanced_rules
    return (UniqueValueRule(), MostCommonValueRule(), ValueCountRule(), *advanced_rules())
