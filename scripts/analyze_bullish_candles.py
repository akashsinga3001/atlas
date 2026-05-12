"""Analyze bullish candle patterns across EQ securities and report next-week upside performance."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from models.ohlcv import Ohlcv
from models.security import Security


TIMEFRAME = '1DAY'
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / 'artifacts' / 'reports' / 'bullish_candles'
MIN_PATTERN_BODY_PCT = 25.0

BULLISH_SINGLE_CANDLE_TYPES = {
    'bullish_candle',
    'strong_bullish_candle',
    'hammer',
    'inverted_hammer',
    'marubozu_full_bullish',
    'marubozu_close_bullish',
    'doji_dragonfly',
}


@dataclass
class CandleRow:
    """Normalized daily candle used by the pattern engine."""

    candle_date: Any
    ticker: str
    open: float
    high: float
    low: float
    close: float


@dataclass
class PatternStats:
    """Aggregated metrics for a candle pattern."""

    signal_count: int = 0
    success_count: int = 0
    gap_success_count: int = 0
    intraday_success_count: int = 0
    max_high_return_sum: float = 0.0
    close_return_sums: list[float] = field(default_factory=lambda: [0.0] * 5)

    def update(self, outcome: dict[str, float]) -> None:
        self.signal_count += 1
        if outcome['success']:
            self.success_count += 1
            if outcome['hit_driver'] == 'gap':
                self.gap_success_count += 1
            elif outcome['hit_driver'] == 'intraday':
                self.intraday_success_count += 1

        self.max_high_return_sum += outcome['max_high_return_pct']
        for index, value in enumerate(outcome['close_return_pcts']):
            self.close_return_sums[index] += value


def _parse_tickers(raw: str | None) -> list[str] | None:
    """Parse comma-separated ticker symbols into uppercase values."""
    if not raw:
        return None

    tickers = [item.strip().upper() for item in raw.split(',') if item.strip()]
    return tickers or None


def _parse_positive_float(value: str) -> float:
    """Parse a non-negative floating-point CLI value."""
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError('Value must be >= 0')
    return parsed


def _print_json(payload: Any) -> None:
    """Print structured output in readable JSON format."""
    print(json.dumps(payload, indent=2, default=str))


def _build_engine():
    """Create a SQLAlchemy engine using project settings."""
    return create_engine(settings.DATABASE_URL, echo=settings.DB_ECHO, future=True)


def _load_daily_rows(tickers: list[str] | None) -> dict[int, list[CandleRow]]:
    """Load all daily EQ candles grouped by security."""
    engine = _build_engine()
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    with session_factory() as session:
        query = (
            select(Ohlcv, Security)
            .join(Security, Security.id == Ohlcv.security_id)
            .where(Security.type == 'EQ', Ohlcv.timeframe == TIMEFRAME)
            .order_by(Ohlcv.security_id.asc(), Ohlcv.candle_date.asc(), Ohlcv.id.asc())
        )
        if tickers:
            query = query.where(Security.ticker.in_(tickers))

        rows = list(session.execute(query).all())

    grouped: dict[int, list[CandleRow]] = {}
    for ohlcv, security in rows:
        grouped.setdefault(ohlcv.security_id, []).append(
            CandleRow(
                candle_date=ohlcv.candle_date,
                ticker=security.ticker,
                open=float(ohlcv.open),
                high=float(ohlcv.high),
                low=float(ohlcv.low),
                close=float(ohlcv.close),
            )
        )

    return grouped


def _classify_candle(candle: CandleRow) -> str:
    """Classify a single candle using the same broad taxonomy as the feature pipeline."""
    candle_range = candle.high - candle.low
    if candle_range <= 0:
        return 'flat'

    body = abs(candle.close - candle.open)
    upper_wick = candle.high - max(candle.open, candle.close)
    lower_wick = min(candle.open, candle.close) - candle.low

    body_pct = (body / candle_range) * 100.0
    upper_pct = (upper_wick / candle_range) * 100.0
    lower_pct = (lower_wick / candle_range) * 100.0

    bias = _bias(candle)
    return _resolve_candle_type(body_pct, upper_pct, lower_pct, bias)


def _bias(candle: CandleRow) -> str:
    """Return the candle direction bias."""
    if candle.close > candle.open:
        return 'bullish'
    if candle.close < candle.open:
        return 'bearish'
    return 'doji'


def _resolve_candle_type(body_pct: float, upper_pct: float, lower_pct: float, bias: str) -> str:
    """Mirror the project's single-candle taxonomy for daily candles."""
    if body_pct == 0 and upper_pct == 0 and lower_pct == 0:
        return 'flat'

    if body_pct <= 10.0:
        if body_pct == 0 and upper_pct > 40.0 and lower_pct > 40.0:
            return 'doji_perfect'
        if upper_pct >= 60.0 and lower_pct <= 10.0:
            return 'doji_gravestone'
        if lower_pct >= 60.0 and upper_pct <= 10.0:
            return 'doji_dragonfly'
        if upper_pct >= 35.0 and lower_pct >= 35.0:
            return 'doji_long_legged'
        if 20.0 <= upper_pct <= 50.0 and 20.0 <= lower_pct <= 50.0:
            return 'doji_rickshaw_man'
        if (upper_pct >= 40.0 and lower_pct <= 15.0) or (lower_pct >= 40.0 and upper_pct <= 15.0):
            return 'doji_umbrella'
        return 'doji_small_body'

    if body_pct >= 90.0 and upper_pct <= 5.0 and lower_pct <= 5.0:
        return 'marubozu_full_bullish' if bias == 'bullish' else 'marubozu_full_bearish'

    if body_pct >= 80.0 and upper_pct <= 8.0 and lower_pct <= 8.0:
        return 'marubozu_close_bullish' if bias == 'bullish' else 'marubozu_close_bearish'

    if lower_pct >= 50.0 and upper_pct <= 15.0:
        return 'hammer' if bias == 'bullish' else 'hanging_man'

    if upper_pct >= 50.0 and lower_pct <= 15.0:
        return 'inverted_hammer' if bias == 'bullish' else 'shooting_star'

    if body_pct <= 30.0 and upper_pct >= 20.0 and lower_pct >= 20.0:
        if body_pct <= 15.0:
            return 'spinning_top_small'
        return 'spinning_top_large'

    if body_pct >= 60.0 and bias == 'bullish' and lower_pct <= 15.0:
        return 'strong_bullish_candle'

    if body_pct >= 60.0 and bias == 'bearish' and upper_pct <= 15.0:
        return 'strong_bearish_candle'

    if bias == 'bullish':
        return 'bullish_candle'
    if bias == 'bearish':
        return 'bearish_candle'
    return 'neutral_candle'


def _is_bullish_single(pattern_name: str) -> bool:
    """Return whether a candle type is bullish by taxonomy."""
    return pattern_name in BULLISH_SINGLE_CANDLE_TYPES


def _match_multi_candle_patterns(rows: list[CandleRow], index: int) -> list[str]:
    """Detect bullish multi-candle patterns ending at the current row."""
    matches: list[str] = []
    current = rows[index]
    current_type = _classify_candle(current)

    if _is_bullish_single(current_type):
        matches.append(current_type)

    if index < 1:
        return matches

    previous = rows[index - 1]
    current_bullish = current.close > current.open
    previous_bearish = previous.close < previous.open
    current_body = abs(current.close - current.open)
    previous_body = abs(previous.close - previous.open)

    if previous_bearish and current_bullish:
        if current.open <= previous.close and current.close >= previous.open:
            matches.append('bullish_engulfing')

        midpoint = previous.close + ((previous.open - previous.close) / 2.0)
        if current.open < previous.close and current.close > midpoint and current.close < previous.open:
            matches.append('piercing_line')

        if previous_body >= MIN_PATTERN_BODY_PCT and current_body <= previous_body * 0.75 and current_body >= MIN_PATTERN_BODY_PCT * 0.5:
            if min(previous.open, previous.close) < current.open < max(previous.open, previous.close):
                matches.append('bullish_harami')

        if abs(current.low - previous.low) / max(previous.low, 1e-9) <= 0.005:
            matches.append('tweezer_bottom')

    if index >= 2:
        first = rows[index - 2]
        second = rows[index - 1]
        third = current

        first_bearish = first.close < first.open
        second_small = abs(second.close - second.open) <= abs(first.close - first.open) * 0.4
        third_bullish = third.close > third.open
        first_midpoint = first.close + ((first.open - first.close) / 2.0)

        if first_bearish and second_small and third_bullish and third.close > first_midpoint:
            matches.append('morning_star')

        if first.close > first.open and second.close > second.open and third.close > third.open:
            if second.close > first.close and third.close > second.close:
                if second.open >= min(first.open, first.close) and second.open <= max(first.open, first.close):
                    if third.open >= min(second.open, second.close) and third.open <= max(second.open, second.close):
                        matches.append('three_white_soldiers')

    if index >= 4:
        first = rows[index - 4]
        second = rows[index - 3]
        third = rows[index - 2]
        fourth = rows[index - 1]
        fifth = current

        first_bullish = first.close > first.open
        def inside_first_body(item: CandleRow) -> bool:
            body_low = min(first.open, first.close)
            body_high = max(first.open, first.close)
            return body_low <= item.open <= body_high and body_low <= item.close <= body_high

        second_to_fourth_inside = inside_first_body(second) and inside_first_body(third) and inside_first_body(fourth)
        fifth_breakout = fifth.close > first.close and fifth.close > max(item.close for item in (second, third, fourth))

        if first_bullish and second_to_fourth_inside and fifth_breakout:
            matches.append('rising_three_methods')

    return sorted(set(matches))


def _evaluate_signal(rows: list[CandleRow], index: int, success_threshold_pct: float) -> dict[str, float] | None:
    """Evaluate next-five-day upside from the candle at index."""
    future_rows = rows[index + 1:index + 6]
    if len(future_rows) < 5:
        return None

    current_close = rows[index].close
    close_return_pcts = [((future.close / current_close) - 1.0) * 100.0 for future in future_rows]
    max_high = max(future.high for future in future_rows)
    max_high_return_pct = ((max_high / current_close) - 1.0) * 100.0

    success = False
    hit_driver = 'none'
    hit_day = None
    hit_return_pct = None
    first_day_open_return_pct = ((future_rows[0].open / current_close) - 1.0) * 100.0

    for day_index, future in enumerate(future_rows, start=1):
        day_open_return_pct = ((future.open / current_close) - 1.0) * 100.0
        day_high_return_pct = ((future.high / current_close) - 1.0) * 100.0
        if day_high_return_pct >= success_threshold_pct:
            success = True
            hit_day = float(day_index)
            hit_return_pct = day_high_return_pct
            hit_driver = 'gap' if day_open_return_pct >= success_threshold_pct else 'intraday'
            break

    return {
        'success': 1.0 if success else 0.0,
        'max_high_return_pct': max_high_return_pct,
        'close_return_pcts': close_return_pcts,
        'hit_driver': hit_driver,
        'hit_day': hit_day if hit_day is not None else 0.0,
        'hit_return_pct': hit_return_pct if hit_return_pct is not None else 0.0,
        'first_day_open_return_pct': first_day_open_return_pct,
    }


def _collect_pattern_stats(
    rows_by_security: dict[int, list[CandleRow]],
    success_threshold_pct: float,
) -> dict[str, PatternStats]:
    """Compute pattern metrics across all loaded securities."""
    stats_by_pattern: dict[str, PatternStats] = {}

    for security_rows in rows_by_security.values():
        if len(security_rows) < 6:
            continue

        for index in range(len(security_rows) - 5):
            patterns = _match_multi_candle_patterns(security_rows, index)
            if not patterns:
                continue

            outcome = _evaluate_signal(security_rows, index, success_threshold_pct)
            if outcome is None:
                continue

            for pattern_name in patterns:
                stats_by_pattern.setdefault(pattern_name, PatternStats()).update(outcome)

    return stats_by_pattern


def _format_pct(value: float) -> float:
    """Round percentage values for reporting."""
    return round(value, 4)


def _build_summary_rows(stats_by_pattern: dict[str, PatternStats]) -> list[dict[str, Any]]:
    """Convert aggregated metrics to serializable rows."""
    rows: list[dict[str, Any]] = []

    for pattern_name, stats in stats_by_pattern.items():
        if stats.signal_count == 0:
            continue

        row = {
            'pattern': pattern_name,
            'signal_count': stats.signal_count,
            'success_count': stats.success_count,
            'success_rate_pct': _format_pct((stats.success_count / stats.signal_count) * 100.0),
            'gap_success_count': stats.gap_success_count,
            'intraday_success_count': stats.intraday_success_count,
            'gap_success_rate_pct': _format_pct((stats.gap_success_count / stats.signal_count) * 100.0),
            'intraday_success_rate_pct': _format_pct((stats.intraday_success_count / stats.signal_count) * 100.0),
            'avg_max_high_return_pct': _format_pct(stats.max_high_return_sum / stats.signal_count),
        }

        for day_index, day_sum in enumerate(stats.close_return_sums, start=1):
            row[f'avg_close_return_day_{day_index}_pct'] = _format_pct(day_sum / stats.signal_count)

        rows.append(row)

    rows.sort(key=lambda item: (-item['success_rate_pct'], -item['signal_count'], item['pattern']))
    for rank, row in enumerate(rows, start=1):
        row['rank'] = rank

    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write summary rows to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        'rank',
        'pattern',
        'signal_count',
        'success_count',
        'success_rate_pct',
        'gap_success_count',
        'intraday_success_count',
        'gap_success_rate_pct',
        'intraday_success_rate_pct',
        'avg_max_high_return_pct',
        'avg_close_return_day_1_pct',
        'avg_close_return_day_2_pct',
        'avg_close_return_day_3_pct',
        'avg_close_return_day_4_pct',
        'avg_close_return_day_5_pct',
    ]
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write structured report to JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2, default=str)


def _print_console_summary(rows: list[dict[str, Any]], payload: dict[str, Any]) -> None:
    """Print a concise human-readable summary to stdout."""
    print('Bullish Candle Pattern Report')
    print(f"Generated at: {payload['generated_at']}")
    print(f"Universe: {payload['universe']}")
    print(f"Success threshold: {payload['success_threshold_pct']:.2f}%")
    print(f"Patterns found: {payload['pattern_count']}")
    print('')

    if not rows:
        print('No bullish patterns matched the selected universe.')
        return

    top = rows[0]
    print(
        f"Top pattern: {top['pattern']} | success_rate={top['success_rate_pct']:.2f}% | "
        f"gap={top['gap_success_count']} intraday={top['intraday_success_count']} | signals={top['signal_count']}"
    )
    print('')
    print('Top 10 patterns:')
    for row in rows[:10]:
        print(
            f"  {row['rank']:>2}. {row['pattern']:<24} "
            f"success={row['success_rate_pct']:>7.2f}% "
            f"gap={row['gap_success_count']:>6} "
            f"intraday={row['intraday_success_count']:>6} "
            f"signals={row['signal_count']:>6} "
            f"avg_max_high={row['avg_max_high_return_pct']:>8.2f}%"
        )


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description='Analyze bullish candle patterns on EQ securities.')
    parser.add_argument('--tickers', default=None, help='Comma-separated ticker symbols to limit the run.')
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT_DIR, help='Directory where CSV and JSON reports will be written.')
    parser.add_argument('--success-threshold-pct', type=_parse_positive_float, default=2.0, help='Minimum next-5-day upside, in percent, required to count as success.')
    return parser.parse_args()


def main() -> None:
    """Run the bullish candle pattern analysis and persist CSV/JSON reports."""
    args = _parse_args()
    tickers = _parse_tickers(args.tickers)
    rows_by_security = _load_daily_rows(tickers)
    stats_by_pattern = _collect_pattern_stats(rows_by_security, args.success_threshold_pct)
    summary_rows = _build_summary_rows(stats_by_pattern)

    payload = {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'universe': 'EQ securities' if tickers is None else f"EQ securities filtered by {', '.join(tickers)}",
        'success_threshold_pct': args.success_threshold_pct,
        'pattern_count': len(summary_rows),
        'summary': summary_rows,
    }

    csv_path = args.output_dir / 'bullish_candle_patterns.csv'
    json_path = args.output_dir / 'bullish_candle_patterns.json'
    payload['csv_path'] = str(csv_path)
    payload['json_path'] = str(json_path)
    _write_csv(csv_path, summary_rows)
    _write_json(json_path, payload)

    _print_console_summary(summary_rows, payload)
    _print_json(payload)


if __name__ == '__main__':
    main()