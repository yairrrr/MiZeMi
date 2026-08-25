"""Polymorphic QuestionRule contract (MASTER_SPEC.md §12.2)."""

from abc import ABC, abstractmethod
from random import Random

from app.domain.questions.candidate import QuestionCandidate
from app.domain.questions.dataset import ProfileDataset


class QuestionRule(ABC):
    """Base contract for one independent deterministic question idea."""

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Return the stable identifier used for scoring and diversity."""

    @abstractmethod
    def generate(
        self,
        dataset: ProfileDataset,
        rng: Random,
    ) -> tuple[QuestionCandidate, ...]:
        """Return zero or more candidates supported by ``dataset``."""
