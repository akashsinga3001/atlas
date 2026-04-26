"""Multi-timeframe moving-average touch strategy with monthly priority."""

from decimal import Decimal
from typing import Any

from strategies.base import SIGNAL_HOLD, SIGNAL_LONG_ENTRY, SIGNAL_SHORT_ENTRY, BacktestCandle, StrategyBase


class MaReversalMultitimeframeStrategy(StrategyBase):
    """MA-touch strategy using monthly gate with weekly/daily confirmation."""

    strategy_name = 'ma_reversal_multitimeframe'

    def __init__(self, short_window: int = 20, long_window: int = 50, initial_sl_pct: Decimal | float | str = Decimal('3'), trailing_sl_pct: Decimal | float | str = Decimal('3'), **params: object) -> None:
        if short_window < 1 or long_window < 2:
            raise ValueError('short_window must be >= 1 and long_window must be >= 2')
        if short_window >= long_window:
            raise ValueError('short_window must be smaller than long_window')

        initial_sl_decimal = Decimal(str(initial_sl_pct))
        trailing_sl_decimal = Decimal(str(trailing_sl_pct))
        if initial_sl_decimal <= 0 or trailing_sl_decimal <= 0:
            raise ValueError('initial_sl_pct and trailing_sl_pct must be > 0')

        super().__init__(short_window=short_window, long_window=long_window, initial_sl_pct=initial_sl_decimal, trailing_sl_pct=trailing_sl_decimal, **params)
        self.short_window = int(short_window)
        self.long_window = int(long_window)
        self.initial_sl_pct = initial_sl_decimal
        self.trailing_sl_pct = trailing_sl_decimal

    @property
    def warmup_bars(self) -> int:
        """Need long_window bars for SMA calculations."""
        return self.long_window

    def generate_signal(self, index: int, candles: list[BacktestCandle], position: str) -> str:
        """Single-timeframe mode is intentionally disabled for this strategy."""
        return SIGNAL_HOLD

    def generate_multitimeframe_signal(self, daily_candles: list[BacktestCandle], weekly_candles: list[BacktestCandle], monthly_candles: list[BacktestCandle], daily_index: int, weekly_index: int, monthly_index: int) -> str:
        """Generate signal using monthly gate and 2-timeframe agreement rule."""
        daily_direction = self._timeframe_direction(daily_candles, daily_index)
        weekly_direction = self._timeframe_direction(weekly_candles, weekly_index)
        monthly_direction = self._timeframe_direction(monthly_candles, monthly_index)

        if monthly_direction == 'LONG':
            aligned = sum([daily_direction == 'LONG', weekly_direction == 'LONG']) + 1
            if aligned >= 2 and self.supports_long:
                return SIGNAL_LONG_ENTRY

        if monthly_direction == 'SHORT':
            aligned = sum([daily_direction == 'SHORT', weekly_direction == 'SHORT']) + 1
            if aligned >= 2 and self.supports_short:
                return SIGNAL_SHORT_ENTRY

        return SIGNAL_HOLD

    def _timeframe_direction(self, candles: list[BacktestCandle], index: int) -> str:
        """Return LONG/SHORT/HOLD by MA trend plus candle-at-MA continuation/reversal signal."""
        if index < self.long_window - 1:
            return 'HOLD'

        short_sma = self._sma(candles, index, self.short_window)
        long_sma = self._sma(candles, index, self.long_window)
        candle = candles[index]

        touch_ma = self._touches_ma(candle, short_sma) or self._touches_ma(candle, long_sma)
        if not touch_ma:
            return 'HOLD'

        bullish = candle.close > candle.open
        bearish = candle.close < candle.open

        trend_long = short_sma > long_sma
        trend_short = short_sma < long_sma

        # Continuation and reversal are both accepted at MA touches.
        long_continuation = trend_long and bullish
        long_reversal = trend_short and bullish and candle.close > short_sma

        short_continuation = trend_short and bearish
        short_reversal = trend_long and bearish and candle.close < short_sma

        if long_continuation or long_reversal:
            return 'LONG'

        if short_continuation or short_reversal:
            return 'SHORT'

        return 'HOLD'

    def _touches_ma(self, candle: BacktestCandle, ma_value: Decimal) -> bool:
        """Check whether a candle range touches a moving average level."""
        return candle.low <= ma_value <= candle.high

    def _sma(self, candles: list[BacktestCandle], end_index: int, period: int) -> Decimal:
        """Compute a simple moving average ending at the given index."""
        start_index = end_index - period + 1
        closes = [candles[i].close for i in range(start_index, end_index + 1)]
        return sum(closes) / Decimal(period)

    def build_stop_levels(self, entry_price: Decimal, direction: str) -> dict[str, Decimal]:
        """Build initial stop level for a new position."""
        initial_ratio = self.initial_sl_pct / Decimal('100')
        if direction == 'LONG':
            stop_price = entry_price * (Decimal('1') - initial_ratio)
        else:
            stop_price = entry_price * (Decimal('1') + initial_ratio)

        return {'initial_stop': stop_price, 'trailing_stop': stop_price}

    def update_trailing_stop(self, direction: str, current_stop: Decimal, best_close: Decimal) -> Decimal:
        """Update trailing stop using best close since entry."""
        trailing_ratio = self.trailing_sl_pct / Decimal('100')
        if direction == 'LONG':
            candidate = best_close * (Decimal('1') - trailing_ratio)
            return max(current_stop, candidate)

        candidate = best_close * (Decimal('1') + trailing_ratio)
        return min(current_stop, candidate)

    def stop_hit(self, direction: str, candle: BacktestCandle, stop_price: Decimal) -> bool:
        """Check stop trigger by candle wick (low/high)."""
        if direction == 'LONG':
            return candle.low <= stop_price
        return candle.high >= stop_price

    def stop_exit_signal(self, stop_kind: str) -> str:
        """Build stop exit signal for persistence and analysis."""
        return f'{stop_kind.upper()}_STOP'
