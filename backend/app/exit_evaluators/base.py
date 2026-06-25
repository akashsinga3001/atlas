# backend/app/exit_evaluators/base.py

from abc import ABC, abstractmethod

from app.exit_evaluators.context import ExitEvaluatorContext
from app.exit_evaluators.decision import ExitDecision


class ExitEvaluator(ABC):
    """Abstract base class for exit evaluators, defining the interface for evaluating exit conditions."""
    code: str

    @abstractmethod
    def evaluate(self, context: ExitEvaluatorContext) -> ExitDecision:
        raise NotImplementedError
