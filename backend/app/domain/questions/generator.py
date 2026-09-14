"""Question Engine pipeline orchestrator (MASTER_SPEC.md §12.1).

dataset → rules → validate → score → select → final ordered Questions.

With a knowledge base, rules read a category-first group summary built once
per generation (``group_summary.py``): consented answers are classified into
comparable categories before any question is considered.

Deterministic given (dataset, question_count, time_limit_seconds, seed):
question ids are minted from the seeded RNG, never from global state.
``question_count`` and ``time_limit_seconds`` come from validated game settings.
The domain engine neither reads environment variables nor decides room defaults.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from random import Random

from app.domain.questions.candidate import QuestionCandidate
from app.domain.questions.knowledge import KnowledgeBase
from app.domain.questions.dataset import ProfileDataset
from app.domain.questions.question import Question, QuestionType
from app.domain.questions.rule import QuestionRule
from app.domain.questions.rules import default_rules
from app.domain.questions.scorer import DiscoveryValueScorer, QuestionQualityScorer
from app.domain.questions.selector import QuestionSelector
from app.domain.questions.validator import QuestionValidator

_QUESTION_ID_BITS = 128


@dataclass(frozen=True)
class GenerationTrace:
    """Every stage of one generation, for diagnostics and pipeline tests."""

    raw: tuple[QuestionCandidate, ...]
    valid: tuple[QuestionCandidate, ...]
    rejected: tuple[tuple[QuestionCandidate, str], ...]
    scored: tuple[tuple[QuestionCandidate, float], ...]
    selected: tuple[QuestionCandidate, ...]
    questions: tuple[Question, ...]


class QuestionGenerator:
    """Runs the full engine pipeline over a consent-safe ProfileDataset."""

    def __init__(
        self,
        rules: Sequence[QuestionRule] | None = None,
        validator: QuestionValidator | None = None,
        scorer: QuestionQualityScorer | None = None,
        selector: QuestionSelector | None = None,
        knowledge: KnowledgeBase | None = None,
    ) -> None:
        self._rules = tuple(rules) if rules is not None else default_rules()
        if knowledge is not None:
            from app.domain.questions.discovery_rules import discovery_rules, production_rules
            self._rules = production_rules(knowledge) if rules is None else (*self._rules, *discovery_rules(knowledge))
        self._validator = validator if validator is not None else QuestionValidator()
        if scorer is None:
            scorer = DiscoveryValueScorer() if knowledge is not None else QuestionQualityScorer()
        self._scorer = scorer
        self._selector = selector if selector is not None else QuestionSelector(group_first=knowledge is not None)

    def generate(
        self,
        dataset: ProfileDataset,
        *,
        question_count: int,
        time_limit_seconds: int,
        seed: int,
        language: str | None = None,
    ) -> tuple[Question, ...]:
        """Return up to ``question_count`` final Questions in selection order.

        Returns fewer (possibly zero) when the dataset supports fewer valid,
        selectable candidates — questions are never fabricated.
        """
        return self.trace(dataset, question_count=question_count, time_limit_seconds=time_limit_seconds,
                          seed=seed, language=language).questions

    def trace(
        self,
        dataset: ProfileDataset,
        *,
        question_count: int,
        time_limit_seconds: int,
        seed: int,
        language: str | None = None,
    ) -> GenerationTrace:
        """Run the pipeline and keep every intermediate stage."""
        if question_count < 1:
            raise ValueError("question_count must be at least 1")
        if time_limit_seconds < 1:
            raise ValueError("time_limit_seconds must be at least 1")

        dataset = dataset.with_language(language or dataset.language)
        rng = Random(seed)
        raw: list[QuestionCandidate] = []
        for rule in self._rules:
            raw.extend(rule.generate(dataset, rng))
        valid: list[QuestionCandidate] = []
        rejected: list[tuple[QuestionCandidate, str]] = []
        explain = getattr(self._validator, "rejection_reason", None)
        for candidate in raw:
            if explain is not None:
                reason = explain(candidate, dataset)
            else:
                reason = None if self._validator.is_valid(candidate, dataset) else "invalid"
            if reason is None:
                valid.append(candidate)
            else:
                rejected.append((candidate, reason))
        scored = [(c, self._scorer.score(c, dataset)) for c in valid]
        selected = self._selector.select(scored, question_count=question_count)

        total = len(selected)
        questions = tuple(
            Question(
                question_id=f"{rng.getrandbits(_QUESTION_ID_BITS):032x}",
                index=index,
                total_questions=total,
                question_type=QuestionType.MULTIPLE_CHOICE,
                text=candidate.text,
                options=candidate.options,
                correct_option_id=candidate.correct_option_id,
                time_limit_seconds=time_limit_seconds,
                difficulty=candidate.difficulty,
                language=dataset.language,
                source_rule_id=candidate.source_rule_id,
                explanation=candidate.explanation,
                knowledge_version=candidate.knowledge_version,
            )
            for index, candidate in enumerate(selected)
        )
        return GenerationTrace(tuple(raw), tuple(valid), tuple(rejected), tuple(scored), selected, questions)
