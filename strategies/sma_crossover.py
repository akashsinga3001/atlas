"""Simple moving-average crossover strategy."""

from decimal import Decimal

from strategies.base import SIGNAL_HOLD, SIGNAL_LONG_ENTRY, SIGNAL_SHORT_ENTRY, BacktestCandle, StrategyBase


class SmaCrossoverStrategy(StrategyBase):
    """Standard SMA crossover strategy supporting long and short directions."""

    strategy_name = 'sma_crossover'

    def __init__(self, short_window: int = 20, long_window: int = 50, **params: object) -> None:
        if short_window < 1 or long_window < 2:
            raise ValueError('short_window must be >= 1 and long_window must be >= 2')
        if short_window >= long_window:
            raise ValueError('short_window must be smaller than long_window')

        super().__init__(short_window=short_window, long_window=long_window, **params)
        self.short_window = int(short_window)
        self.long_window = int(long_window)

    @property
    def warmup_bars(self) -> int:
        """Need at least long_window bars before crossover detection."""
        return self.long_window

    def generate_signal(self, index: int, candles: list[BacktestCandle], position: str) -> str:
        """Generate crossover entries with reversal support handled by the engine."""
        if index < self.long_window:
            return SIGNAL_HOLD

        short_now = self._sma(candles, index, self.short_window)
        long_now = self._sma(candles, index, self.long_window)
        short_prev = self._sma(candles, index - 1, self.short_window)
        long_prev = self._sma(candles, index - 1, self.long_window)

        bullish_cross = short_prev <= long_prev and short_now > long_now
        bearish_cross = short_prev >= long_prev and short_now < long_now

        if bullish_cross and self.supports_long:
            return SIGNAL_LONG_ENTRY

        if bearish_cross and self.supports_short:
            return SIGNAL_SHORT_ENTRY

        return SIGNAL_HOLD

    def _sma(self, candles: list[BacktestCandle], end_index: int, period: int) -> Decimal:
        """Compute a simple moving average ending at the given index."""
        start_index = end_index - period + 1
        closes = [candles[i].close for i in range(start_index, end_index + 1)]
        return sum(closes) / Decimal(period)
