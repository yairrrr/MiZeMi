"""Question domain package (MASTER_SPEC.md §9.3, §12)."""

from app.domain.questions.candidate import QuestionCandidate
from app.domain.questions.dataset import ProfileDataset
from app.domain.questions.question import Question, QuestionOption, QuestionType
from app.domain.questions.rule import QuestionRule

__all__ = [
    "ProfileDataset",
    "Question",
    "QuestionCandidate",
    "QuestionOption",
    "QuestionRule",
    "QuestionType",
]
