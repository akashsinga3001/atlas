# backend/app/strategies/base.py

from abc import ABC, abstractmethod

from app.strategies.context import StrategyContext
from app.strategies.observation import Observation


class Strategy(ABC):
    """
    Abstract base class for all strategies.
    This class defines the interface that all concrete strategy implementations must follow.
    """
    code: str
    name: str

    @abstractmethod
    def execute(self, context: StrategyContext) -> list[Observation]:
        """
        Execute the strategy using the provided context.

        Args:
            context (StrategyContext): The context in which the strategy operates.

        Returns:
            list[Observation]: The observations resulting from executing the strategy.
        """
        raise NotImplementedError("Subclasses must implement the execute method.")

    def build_run_metrics(self) -> dict:
        """Optional hook: return metrics about the just-completed execute() call to persist on
        the StrategyRun (StrategyRun.metrics). Called once, immediately after execute() returns.

        Default is a no-op so existing strategies are unaffected. A strategy that needs a stable
        historical record of something it decided today (e.g. "which tickers were top-10%") to
        compare a later run against overrides this — see RelativeLeadershipV1Strategy — rather
        than having that later run re-derive the same fact from feature data that may have since
        changed.
        """
        return {}
