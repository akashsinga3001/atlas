# backend/app/execution_engines/base.py

from abc import ABC, abstractmethod
from datetime import date

from app.models.strategy import StrategyVersion
from app.schemas.base import APIResponse


class TradeExecutionEngine(ABC):
    """
    Abstract base class for all trade execution engines.

    A Strategy produces signals; an execution engine turns those signals into
    broker orders (entry) and manages open positions (exit). Different asset
    classes/instrument shapes (single-leg equity, multi-leg options, ...) need
    different order-placement logic, so this is the seam a `Strategy` plugs
    into via `Strategy.execution_engine` — not the signal-generation interface
    itself.
    """
    code: str

    @abstractmethod
    def run_entry(self, strategy_version: StrategyVersion, as_of_date: date, **kwargs) -> APIResponse:
        """
        Evaluate the strategy's latest signal(s) and place entry orders as appropriate.

        Args:
            strategy_version (StrategyVersion): The active version to run entry for.
            as_of_date (date): The date entry logic should evaluate against.

        Returns:
            APIResponse: Outcome of the entry evaluation/placement.
        """
        raise NotImplementedError("Subclasses must implement the run_entry method.")

    @abstractmethod
    def run_exit_evaluation(self, strategy_version: StrategyVersion, as_of_date: date) -> APIResponse:
        """
        Evaluate open positions under a strategy version and close/adjust as appropriate.

        Args:
            strategy_version (StrategyVersion): The active version to evaluate exits for.
            as_of_date (date): The date exit logic should evaluate against.

        Returns:
            APIResponse: Outcome of the exit evaluation.
        """
        raise NotImplementedError("Subclasses must implement the run_exit_evaluation method.")
