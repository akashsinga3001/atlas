# backend/app/strategies/bootstrap.py

from app.strategies.registry import StrategyRegistry
from app.strategies.dummy import DummyStrategy


def register_strategies() -> None:
    """
    Register all available strategies in the StrategyRegistry.
    """
    StrategyRegistry.register_strategy(DummyStrategy)
