# backend/app/exit_evaluators/bootstrap.py

from app.exit_evaluators.registry import ExitEvaluatorRegistry
from app.exit_evaluators.atr_trailing.evaluator import ATRTrailingStopEvaluator
from app.exit_evaluators.relative_leadership_deterioration.evaluator import RelativeLeadershipDeteriorationEvaluator


def register_exit_evaluators() -> None:
    """Registers all exit evaluators in the ExitEvaluatorRegistry."""
    ExitEvaluatorRegistry.register(ATRTrailingStopEvaluator)
    ExitEvaluatorRegistry.register(RelativeLeadershipDeteriorationEvaluator)
