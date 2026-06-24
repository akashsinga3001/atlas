# backend/app/strategies/bootstrap.py

from app.strategies.registry import StrategyRegistry
from app.strategies.dummy import DummyStrategy
from app.strategies.momentum_screener import MomentumScreenerStrategy


def register_strategies() -> None:
    """
    Register all available strategies in the StrategyRegistry.
    """
    StrategyRegistry.register(DummyStrategy)
    StrategyRegistry.register(MomentumScreenerStrategy)
