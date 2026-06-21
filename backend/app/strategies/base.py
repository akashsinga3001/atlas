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
