"""Base contracts and shared types for trading strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


SIGNAL_HOLD = 'HOLD'
SIGNAL_LONG_ENTRY = 'LONG_ENTRY'
SIGNAL_LONG_EXIT = 'LONG_EXIT'
SIGNAL_SHORT_ENTRY = 'SHORT_ENTRY'
SIGNAL_SHORT_EXIT = 'SHORT_EXIT'

VALID_SIGNALS = {
    SIGNAL_HOLD,
    SIGNAL_LONG_ENTRY,
    SIGNAL_LONG_EXIT,
    SIGNAL_SHORT_ENTRY,
    SIGNAL_SHORT_EXIT,
}


@dataclass(frozen=True)
class BacktestCandle:
    """Normalized market candle used by strategies and backtest engine."""

    security_id: int
    ticker: str
    candle_date: date
    timeframe: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    features: dict[str, Decimal | str] | None = None


class StrategyBase(ABC):
    """Abstract base class for all strategies in the framework."""

    strategy_name = 'base'
    supports_long = True
    supports_short = True

    def __init__(self, **params: object) -> None:
        self.params = params

    @property
    def warmup_bars(self) -> int:
        """Bars required before the strategy can emit active entry/exit signals."""
        return 0

    @abstractmethod
    def generate_signal(self, index: int, candles: list[BacktestCandle], position: str) -> str:
        """Generate one signal for a candle index.

        Args:
            index: Current candle index.
            candles: Ordered candle list for one security.
            position: Current position state: FLAT, LONG, or SHORT.

        Returns:
            One of the strategy signal constants.
        """

    def validate_signal(self, signal: str) -> str:
        """Validate and normalize strategy output signal."""
        normalized = signal.strip().upper()
        if normalized not in VALID_SIGNALS:
            raise ValueError(f'Invalid signal {signal!r} from strategy {self.strategy_name}')
        return normalized
