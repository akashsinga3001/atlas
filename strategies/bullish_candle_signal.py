"""Long-only strategy driven purely by bullish candle signals."""

from decimal import Decimal
from typing import Iterable

from strategies.base import SIGNAL_HOLD, SIGNAL_LONG_ENTRY, BacktestCandle, StrategyBase


class BullishCandleSignalStrategy(StrategyBase):
    """Enter long when a bullish candle signal appears; exit only through stops."""

    strategy_name = 'bullish_candle_signal'
    supports_short = False

    DEFAULT_ENTRY_PATTERNS = (
        'marubozu_full_bullish',
        'doji_dragonfly',
        'strong_bullish_candle',
        'rising_three_methods',
        'bullish_harami',
        'marubozu_close_bullish',
        'morning_star',
        'inverted_hammer',
        'bullish_candle',
        'bullish_engulfing',
        'hammer',
        'piercing_line',
        'three_white_soldiers',
        'tweezer_bottom',
    )

    def __init__(
        self,
        entry_patterns: str | Iterable[str] | None = None,
        initial_sl_pct: Decimal | float | str = Decimal('3'),
        trailing_sl_pct: Decimal | float | str = Decimal('3'),
        **params: object,
    ) -> None:
        initial_sl_decimal = Decimal(str(initial_sl_pct))
        trailing_sl_decimal = Decimal(str(trailing_sl_pct))
        if initial_sl_decimal <= 0 or trailing_sl_decimal <= 0:
            raise ValueError('initial_sl_pct and trailing_sl_pct must be > 0')

        normalized_entry_patterns = self._normalize_entry_patterns(entry_patterns)
        super().__init__(
            entry_patterns=tuple(normalized_entry_patterns),
            initial_sl_pct=initial_sl_decimal,
            trailing_sl_pct=trailing_sl_decimal,
            **params,
        )

        self.entry_patterns = set(normalized_entry_patterns)
        self.initial_sl_pct = initial_sl_decimal
        self.trailing_sl_pct = trailing_sl_decimal

    @property
    def warmup_bars(self) -> int:
        """Need a few prior candles to validate multi-candle bullish patterns."""
        return 4

    def generate_signal(self, index: int, candles: list[BacktestCandle], position: str) -> str:
        """Emit a long entry when the current candle matches a bullish signal."""
        if position != 'FLAT':
            return SIGNAL_HOLD

        if index < self.warmup_bars:
            return SIGNAL_HOLD

        current_type = self._candle_type(candles[index])
        if current_type in self.entry_patterns:
            return SIGNAL_LONG_ENTRY

        matched_patterns = self._match_multi_candle_patterns(candles, index)
        if any(pattern in self.entry_patterns for pattern in matched_patterns):
            return SIGNAL_LONG_ENTRY

        return SIGNAL_HOLD

    def build_stop_levels(self, entry_price: Decimal, direction: str) -> dict[str, Decimal]:
        """Build the initial 3% stop and trailing stop for a new position."""
        initial_ratio = self.initial_sl_pct / Decimal('100')
        if direction == 'LONG':
            stop_price = entry_price * (Decimal('1') - initial_ratio)
        else:
            stop_price = entry_price * (Decimal('1') + initial_ratio)

        return {'initial_stop': stop_price, 'trailing_stop': stop_price}

    def update_trailing_stop(self, direction: str, current_stop: Decimal, best_close: Decimal) -> Decimal:
        """Move the trailing stop 3% behind the best close seen so far."""
        trailing_ratio = self.trailing_sl_pct / Decimal('100')
        if direction == 'LONG':
            candidate = best_close * (Decimal('1') - trailing_ratio)
            return max(current_stop, candidate)

        candidate = best_close * (Decimal('1') + trailing_ratio)
        return min(current_stop, candidate)

    def stop_hit(self, direction: str, candle: BacktestCandle, stop_price: Decimal) -> bool:
        """Check stop trigger by candle wick."""
        if direction == 'LONG':
            return candle.low <= stop_price
        return candle.high >= stop_price

    def stop_exit_signal(self, stop_kind: str) -> str:
        """Build stop exit signal for persistence and analysis."""
        return f'{stop_kind.upper()}_STOP'

    def _normalize_entry_patterns(self, entry_patterns: str | Iterable[str] | None) -> list[str]:
        """Normalize entry pattern names into a lowercase list."""
        if entry_patterns is None:
            return [pattern.lower() for pattern in self.DEFAULT_ENTRY_PATTERNS]

        if isinstance(entry_patterns, str):
            values = [item.strip() for item in entry_patterns.split(',')]
        else:
            values = [str(item).strip() for item in entry_patterns]

        normalized = [item.lower() for item in values if item]
        return normalized or [pattern.lower() for pattern in self.DEFAULT_ENTRY_PATTERNS]

    def _candle_type(self, candle: BacktestCandle) -> str:
        """Read the precomputed candle type or derive it from OHLC data."""
        if candle.features is not None:
            feature_type = candle.features.get('candle_type')
            if isinstance(feature_type, str) and feature_type:
                return feature_type.lower()

        return self._resolve_candle_type(candle)

    def _match_multi_candle_patterns(self, candles: list[BacktestCandle], index: int) -> list[str]:
        """Detect bullish multi-candle patterns ending at the current bar."""
        matches: list[str] = []
        current = candles[index]
        current_type = self._candle_type(current)

        if self._is_bullish_single(current_type):
            matches.append(current_type)

        if index < 1:
            return matches

        previous = candles[index - 1]
        current_bullish = current.close > current.open
        previous_bearish = previous.close < previous.open
        current_body = abs(current.close - current.open)
        previous_body = abs(previous.close - previous.open)
        current_range = current.high - current.low
        previous_range = previous.high - previous.low
        current_body_pct = (current_body / current_range) * Decimal('100') if current_range > 0 else Decimal('0')
        previous_body_pct = (previous_body / previous_range) * Decimal('100') if previous_range > 0 else Decimal('0')

        if previous_bearish and current_bullish:
            if current.open <= previous.close and current.close >= previous.open:
                matches.append('bullish_engulfing')

            midpoint = previous.close + ((previous.open - previous.close) / Decimal('2'))
            if current.open < previous.close and current.close > midpoint and current.close < previous.open:
                matches.append('piercing_line')

            if previous_body_pct >= Decimal('25') and current_body_pct <= previous_body_pct * Decimal('0.75') and current_body_pct >= Decimal('5'):
                if min(previous.open, previous.close) < current.open < max(previous.open, previous.close):
                    matches.append('bullish_harami')

            if previous.low > 0:
                low_delta = abs(current.low - previous.low) / previous.low
                if low_delta <= Decimal('0.005'):
                    matches.append('tweezer_bottom')

        if index >= 2:
            first = candles[index - 2]
            second = candles[index - 1]
            third = current

            first_bearish = first.close < first.open
            second_small = abs(second.close - second.open) <= abs(first.close - first.open) * Decimal('0.4')
            third_bullish = third.close > third.open
            first_midpoint = first.close + ((first.open - first.close) / Decimal('2'))

            if first_bearish and second_small and third_bullish and third.close > first_midpoint:
                matches.append('morning_star')

            if first.close > first.open and second.close > second.open and third.close > third.open:
                if second.close > first.close and third.close > second.close:
                    if second.open >= min(first.open, first.close) and second.open <= max(first.open, first.close):
                        if third.open >= min(second.open, second.close) and third.open <= max(second.open, second.close):
                            matches.append('three_white_soldiers')

        if index >= 4:
            first = candles[index - 4]
            second = candles[index - 3]
            third = candles[index - 2]
            fourth = candles[index - 1]
            fifth = current

            first_bullish = first.close > first.open

            def inside_first_body(item: BacktestCandle) -> bool:
                body_low = min(first.open, first.close)
                body_high = max(first.open, first.close)
                return body_low <= item.open <= body_high and body_low <= item.close <= body_high

            second_to_fourth_inside = inside_first_body(second) and inside_first_body(third) and inside_first_body(fourth)
            fifth_breakout = fifth.close > first.close and fifth.close > max(item.close for item in (second, third, fourth))

            if first_bullish and second_to_fourth_inside and fifth_breakout:
                matches.append('rising_three_methods')

        return sorted(set(matches))

    def _is_bullish_single(self, pattern_name: str) -> bool:
        """Return whether a candle type is a bullish single-candle signal."""
        return pattern_name in {
            'bullish_candle',
            'strong_bullish_candle',
            'hammer',
            'inverted_hammer',
            'marubozu_full_bullish',
            'marubozu_close_bullish',
            'doji_dragonfly',
        }

    def _resolve_candle_type(self, candle: BacktestCandle) -> str:
        """Classify one candle from raw OHLC data."""
        candle_range = candle.high - candle.low
        if candle_range <= 0:
            return 'flat'

        body = abs(candle.close - candle.open)
        upper_wick = candle.high - max(candle.open, candle.close)
        lower_wick = min(candle.open, candle.close) - candle.low

        body_pct = (body / candle_range) * Decimal('100')
        upper_pct = (upper_wick / candle_range) * Decimal('100')
        lower_pct = (lower_wick / candle_range) * Decimal('100')

        if candle.close > candle.open:
            bias = 'bullish'
        elif candle.close < candle.open:
            bias = 'bearish'
        else:
            bias = 'doji'

        if body_pct == 0 and upper_pct == 0 and lower_pct == 0:
            return 'flat'

        if body_pct <= Decimal('10'):
            if body_pct == 0 and upper_pct > Decimal('40') and lower_pct > Decimal('40'):
                return 'doji_perfect'
            if upper_pct >= Decimal('60') and lower_pct <= Decimal('10'):
                return 'doji_gravestone'
            if lower_pct >= Decimal('60') and upper_pct <= Decimal('10'):
                return 'doji_dragonfly'
            if upper_pct >= Decimal('35') and lower_pct >= Decimal('35'):
                return 'doji_long_legged'
            if upper_pct >= Decimal('20') and lower_pct >= Decimal('20') and upper_pct <= Decimal('50') and lower_pct <= Decimal('50'):
                return 'doji_rickshaw_man'
            if (upper_pct >= Decimal('40') and lower_pct <= Decimal('15')) or (lower_pct >= Decimal('40') and upper_pct <= Decimal('15')):
                return 'doji_umbrella'
            return 'doji_small_body'

        if body_pct >= Decimal('90') and upper_pct <= Decimal('5') and lower_pct <= Decimal('5'):
            return 'marubozu_full_bullish' if bias == 'bullish' else 'marubozu_full_bearish'

        if body_pct >= Decimal('80') and upper_pct <= Decimal('8') and lower_pct <= Decimal('8'):
            return 'marubozu_close_bullish' if bias == 'bullish' else 'marubozu_close_bearish'

        if lower_pct >= Decimal('50') and upper_pct <= Decimal('15'):
            return 'hammer' if bias == 'bullish' else 'hanging_man'

        if upper_pct >= Decimal('50') and lower_pct <= Decimal('15'):
            return 'inverted_hammer' if bias == 'bullish' else 'shooting_star'

        if body_pct <= Decimal('30') and upper_pct >= Decimal('20') and lower_pct >= Decimal('20'):
            if body_pct <= Decimal('15'):
                return 'doji_small_body'
            return 'spinning_top_large'

        if body_pct >= Decimal('60') and bias == 'bullish' and lower_pct <= Decimal('15'):
            return 'strong_bullish_candle'

        if body_pct >= Decimal('60') and bias == 'bearish' and upper_pct <= Decimal('15'):
            return 'strong_bearish_candle'

        if bias == 'bullish':
            return 'bullish_candle'
        if bias == 'bearish':
            return 'bearish_candle'
        return 'neutral_candle'
