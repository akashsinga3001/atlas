"""Strategy registry and factory for backtesting and ML pipelines."""

from collections.abc import Mapping

from strategies.base import StrategyBase
from strategies.ma_reversal_multitimeframe import MaReversalMultitimeframeStrategy
from strategies.sma_crossover import SmaCrossoverStrategy


def create_strategy(strategy_name: str, strategy_params: Mapping[str, object] | None = None) -> StrategyBase:
    """Create a strategy instance by name with optional parameter overrides."""
    params = dict(strategy_params or {})
    normalized = strategy_name.strip().lower()

    if normalized == 'sma_crossover':
        return SmaCrossoverStrategy(**params)

    if normalized == 'ma_reversal_multitimeframe':
        return MaReversalMultitimeframeStrategy(**params)

    raise ValueError(f'Unsupported strategy: {strategy_name}')


__all__ = ['StrategyBase', 'SmaCrossoverStrategy', 'MaReversalMultitimeframeStrategy', 'create_strategy']
