# backend/app/exit_evaluators/base.py

from abc import ABC, abstractmethod

from app.exit_evaluators.context import ExitEvaluatorContext
from app.exit_evaluators.decision import ExitDecision


class ExitEvaluator(ABC):
    """Abstract base class for exit evaluators, defining the interface for evaluating exit conditions."""
    code: str

    def prepare_run_context(self, feature_service, as_of_date) -> dict:
        """Optional hook: compute data shared across every trade in one evaluate_exits() run,
        before the per-trade loop — e.g. a cross-sectional ranking that a single trade's
        features can't answer on its own. Merged into every trade's ExitEvaluatorContext.
        Default: no extra context (most evaluators, like ATRTrailingStopEvaluator, are
        purely per-trade and don't need this)."""
        return {}

    @abstractmethod
    def evaluate(self, context: ExitEvaluatorContext) -> ExitDecision:
        raise NotImplementedError
