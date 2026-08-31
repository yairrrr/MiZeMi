"""Question domain package (MASTER_SPEC.md §9.3, §12)."""

from app.domain.questions.candidate import QuestionCandidate
from app.domain.questions.dataset import ProfileDataset
from app.domain.questions.generator import QuestionGenerator
from app.domain.questions.question import Question, QuestionOption, QuestionType
from app.domain.questions.rule import QuestionRule
from app.domain.questions.rules import (
    MostCommonValueRule,
    UniqueValueRule,
    ValueCountRule,
    default_rules,
)
from app.domain.questions.scorer import QuestionQualityScorer
from app.domain.questions.selector import QuestionSelector
from app.domain.questions.validator import QuestionValidator

__all__ = [
    "MostCommonValueRule",
    "ProfileDataset",
    "Question",
    "QuestionCandidate",
    "QuestionGenerator",
    "QuestionOption",
    "QuestionQualityScorer",
    "QuestionRule",
    "QuestionSelector",
    "QuestionType",
    "QuestionValidator",
    "UniqueValueRule",
    "ValueCountRule",
    "default_rules",
]
