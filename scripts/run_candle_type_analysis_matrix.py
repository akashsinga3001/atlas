"""Run candle-type strategy analysis matrix with portfolio-level constraints.

Hard rules enforced:
- Max 4 concurrent positions
- 3% initial stop-loss
- 3% trailing stop-loss based on best day high since entry
"""

from __future__ import annotations

import csv
import json
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from statistics import mean, median, stdev
from math import sqrt
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from models.feature import Feature
from models.ohlcv import Ohlcv
from models.security import Security


OUTPUT_DIR = PROJECT_ROOT / 'artifacts' / 'reports' / 'candle_type_matrix'
TIMEFRAME = '1DAY'
MAX_CONCURRENT_POSITIONS = 4
INITIAL_SL_PCT = Decimal('3')
TRAILING_SL_PCT = Decimal('3')
STOP_RATIO = Decimal('0.97')

ENTRY_PATTERNS = {
    'marubozu_full_bullish',
    'doji_dragonfly',
    'strong_bullish_candle',
    'rising_three_methods',
    'bullish_harami',
    'marubozu_close_bullish',
    'morning_star',
    'inverted_hammer',
    'bullish_engulfing',
    'piercing_line',
    'hammer',
}


@dataclass
class CandleRow:
    security_id: int
    ticker: str
    candle_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    candle_type: str
    body_size_pct: float
    close_position_pct: float


@dataclass
class Position:
    security_id: int
    ticker: str
    entry_date: date
    entry_price: Decimal
    initial_stop: Decimal
    trailing_stop: Decimal
    best_high: Decimal
    entry_pattern: str
    entry_body_size_pct: float
    entry_close_position_pct: float
    entry_signal_high: Decimal
    quantity: int
    invested_capital: Decimal
    bars_held: int = 0


def _load_rows() -> dict[int, list[CandleRow]]:
    engine = create_engine(settings.DATABASE_URL, echo=settings.DB_ECHO, future=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    with session_factory() as session:
        rows = list(
            session.execute(
                select(Ohlcv, Feature, Security)
                .join(Security, Security.id == Ohlcv.security_id)
                .outerjoin(Feature, Feature.ohlcv_id == Ohlcv.id)
                .where(Security.is_active.is_(True), Security.type == 'EQ', Ohlcv.timeframe == TIMEFRAME)
                .order_by(Ohlcv.candle_date.asc(), Ohlcv.security_id.asc(), Ohlcv.id.asc())
            ).all()
        )

    by_security: dict[int, list[CandleRow]] = {}
    for ohlcv, feature, security in rows:
        by_security.setdefault(ohlcv.security_id, []).append(
            CandleRow(
                security_id=int(ohlcv.security_id),
                ticker=str(security.ticker),
                candle_date=ohlcv.candle_date,
                open=Decimal(str(ohlcv.open)),
                high=Decimal(str(ohlcv.high)),
                low=Decimal(str(ohlcv.low)),
                close=Decimal(str(ohlcv.close)),
                volume=int(ohlcv.volume),
                candle_type=str(feature.candle_type) if feature is not None else 'unknown',
                body_size_pct=float(feature.body_size_pct) if feature is not None and feature.body_size_pct is not None else 0.0,
                close_position_pct=float(feature.close_position_pct) if feature is not None and feature.close_position_pct is not None else 0.0,
            )
        )

    return by_security


def _to_calendar(by_security: dict[int, list[CandleRow]]) -> tuple[list[date], dict[int, dict[date, CandleRow]]]:
    dates: set[date] = set()
    lookup: dict[int, dict[date, CandleRow]] = {}
    for security_id, rows in by_security.items():
        daily_map: dict[date, CandleRow] = {}
        for row in rows:
            dates.add(row.candle_date)
            daily_map[row.candle_date] = row
        lookup[security_id] = daily_map
    return sorted(dates), lookup


def _build_signal_flags(rows: list[CandleRow], config: dict[str, Any]) -> list[bool]:
    flags = [False] * len(rows)
    for idx in range(len(rows)):
        row = rows[idx]
        if row.candle_type not in ENTRY_PATTERNS:
            continue

        if row.body_size_pct < config['min_body_size_pct']:
            continue
        if row.close_position_pct < config['min_close_position_pct']:
            continue

        if config['breakout_confirmation']:
            if idx + 1 >= len(rows):
                continue
            next_row = rows[idx + 1]
            if next_row.close <= row.high:
                continue

        if config['min_prev_bars'] > 0 and idx < config['min_prev_bars']:
            continue

        closes = [float(item.close) for item in rows[: idx + 1]]
        if config['require_close_above_sma20']:
            sma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
            if sma20 is None or float(row.close) <= sma20:
                continue

        if config['require_sma20_above_sma50']:
            sma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
            sma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
            if sma20 is None or sma50 is None or sma20 <= sma50:
                continue

        signal_index = idx + 1 if config['breakout_confirmation'] else idx
        if signal_index < len(flags):
            flags[signal_index] = True
    return flags


def _make_configs() -> list[dict[str, Any]]:
    return [
        {
            'name': 'strict_trend_breakout_cooldown3_timestop10',
            'min_body_size_pct': 25.0,
            'min_close_position_pct': 60.0,
            'require_close_above_sma20': True,
            'require_sma20_above_sma50': True,
            'breakout_confirmation': True,
            'min_prev_bars': 50,
            'cooldown_bars': 3,
            'max_holding_bars': 10,
            'cooldown_after_stop_only': True,
            'position_size_fraction': 1.0,
            'score_body_weight': 1.0,
            'score_close_weight': 0.5,
            'score_momentum_weight': 0.8,
            'recent_stop_penalty': 6.0,
        },
        {
            'name': 'strict_trend_breakout_cooldown5_timestop8',
            'min_body_size_pct': 25.0,
            'min_close_position_pct': 60.0,
            'require_close_above_sma20': True,
            'require_sma20_above_sma50': True,
            'breakout_confirmation': True,
            'min_prev_bars': 50,
            'cooldown_bars': 5,
            'max_holding_bars': 8,
            'cooldown_after_stop_only': True,
            'position_size_fraction': 1.0,
            'score_body_weight': 1.0,
            'score_close_weight': 0.5,
            'score_momentum_weight': 0.8,
            'recent_stop_penalty': 8.0,
        },
        {
            'name': 'balanced_trend_breakout_cooldown3_timestop10',
            'min_body_size_pct': 20.0,
            'min_close_position_pct': 55.0,
            'require_close_above_sma20': True,
            'require_sma20_above_sma50': True,
            'breakout_confirmation': True,
            'min_prev_bars': 50,
            'cooldown_bars': 3,
            'max_holding_bars': 10,
            'cooldown_after_stop_only': True,
            'position_size_fraction': 1.0,
            'score_body_weight': 1.0,
            'score_close_weight': 0.5,
            'score_momentum_weight': 0.6,
            'recent_stop_penalty': 5.0,
        },
        {
            'name': 'balanced_trend_no_breakout_cooldown2_timestop8',
            'min_body_size_pct': 20.0,
            'min_close_position_pct': 55.0,
            'require_close_above_sma20': True,
            'require_sma20_above_sma50': True,
            'breakout_confirmation': False,
            'min_prev_bars': 50,
            'cooldown_bars': 2,
            'max_holding_bars': 8,
            'cooldown_after_stop_only': True,
            'position_size_fraction': 1.0,
            'score_body_weight': 1.0,
            'score_close_weight': 0.5,
            'score_momentum_weight': 0.4,
            'recent_stop_penalty': 4.0,
        },
        {
            'name': 'quality_only_breakout_cooldown3_timestop6',
            'min_body_size_pct': 25.0,
            'min_close_position_pct': 60.0,
            'require_close_above_sma20': False,
            'require_sma20_above_sma50': False,
            'breakout_confirmation': True,
            'min_prev_bars': 0,
            'cooldown_bars': 3,
            'max_holding_bars': 6,
            'cooldown_after_stop_only': True,
            'position_size_fraction': 1.0,
            'score_body_weight': 1.0,
            'score_close_weight': 0.7,
            'score_momentum_weight': 0.4,
            'recent_stop_penalty': 5.0,
        },
        {
            'name': 'quality_only_no_breakout_cooldown2_timestop6',
            'min_body_size_pct': 25.0,
            'min_close_position_pct': 60.0,
            'require_close_above_sma20': False,
            'require_sma20_above_sma50': False,
            'breakout_confirmation': False,
            'min_prev_bars': 0,
            'cooldown_bars': 2,
            'max_holding_bars': 6,
            'cooldown_after_stop_only': True,
            'position_size_fraction': 1.0,
            'score_body_weight': 1.0,
            'score_close_weight': 0.7,
            'score_momentum_weight': 0.2,
            'recent_stop_penalty': 3.0,
        },
    ]


def _current_equity(cash: Decimal, positions: dict[int, Position], by_security_date: dict[int, dict[date, CandleRow]], current_date: date) -> Decimal:
    market_value = Decimal('0')
    for security_id, position in positions.items():
        candle = by_security_date.get(security_id, {}).get(current_date)
        mark_price = candle.close if candle is not None else position.entry_price
        market_value += Decimal(position.quantity) * mark_price
    return cash + market_value


def _candidate_score(
    candle: CandleRow,
    rows: list[CandleRow],
    index: int,
    recently_stopped: bool,
    config: dict[str, Any],
) -> float:
    body_component = candle.body_size_pct * float(config['score_body_weight'])
    close_component = candle.close_position_pct * float(config['score_close_weight'])

    momentum_component = 0.0
    if index >= 5:
        past_close = float(rows[index - 5].close)
        if past_close > 0:
            momentum_5d_pct = ((float(candle.close) - past_close) / past_close) * 100.0
            momentum_component = momentum_5d_pct * float(config['score_momentum_weight'])

    penalty = float(config['recent_stop_penalty']) if recently_stopped else 0.0
    return body_component + close_component + momentum_component - penalty


def _simulate(
    by_security: dict[int, list[CandleRow]],
    dates: list[date],
    by_security_date: dict[int, dict[date, CandleRow]],
    config: dict[str, Any],
) -> dict[str, Any]:
    signal_flags = {security_id: _build_signal_flags(rows, config) for security_id, rows in by_security.items()}
    date_index_lookup: dict[int, dict[date, int]] = {
        security_id: {row.candle_date: idx for idx, row in enumerate(rows)} for security_id, rows in by_security.items()
    }

    initial_capital = Decimal('100000')
    cash = initial_capital
    peak = initial_capital
    max_drawdown_pct = Decimal('0')

    positions: dict[int, Position] = {}
    trades: list[dict[str, Any]] = []
    cooldown_until_index: dict[int, int] = {}
    last_stop_index: dict[int, int] = {}
    blocked_by_cooldown_signals = 0
    time_stop_exits = 0
    trailing_stop_exits = 0
    initial_stop_exits = 0
    utilization_samples: list[float] = []

    for current_index, current_date in enumerate(dates):
        # Exit pass first.
        exiting: list[int] = []
        for security_id, position in positions.items():
            candle = by_security_date.get(security_id, {}).get(current_date)
            if candle is None:
                continue

            position.bars_held += 1
            position.best_high = max(position.best_high, candle.high)
            candidate_trailing = position.best_high * STOP_RATIO
            if candidate_trailing > position.trailing_stop:
                position.trailing_stop = candidate_trailing

            exit_price: Decimal | None = None
            exit_signal = ''
            if candle.low <= position.trailing_stop:
                exit_price = position.trailing_stop
                if position.trailing_stop > position.initial_stop:
                    exit_signal = 'TRAILING_STOP'
                    trailing_stop_exits += 1
                else:
                    exit_signal = 'INITIAL_STOP'
                    initial_stop_exits += 1
            elif config['max_holding_bars'] > 0 and position.bars_held >= config['max_holding_bars']:
                exit_price = candle.close
                exit_signal = 'TIME_STOP'
                time_stop_exits += 1

            if exit_price is not None:
                proceeds = Decimal(position.quantity) * exit_price
                entry_value = Decimal(position.quantity) * position.entry_price
                net_pnl = proceeds - entry_value
                return_pct = (net_pnl / entry_value) * Decimal('100') if entry_value > 0 else Decimal('0')
                trades.append(
                    {
                        'security_id': security_id,
                        'ticker': position.ticker,
                        'entry_date': position.entry_date,
                        'exit_date': current_date,
                        'entry_price': position.entry_price,
                        'exit_price': exit_price,
                        'quantity': position.quantity,
                        'entry_value': entry_value,
                        'exit_value': proceeds,
                        'net_pnl': net_pnl,
                        'return_pct': return_pct,
                        'bars_held': position.bars_held,
                        'entry_pattern': position.entry_pattern,
                        'exit_signal': exit_signal,
                    }
                )
                cash += proceeds
                if config['cooldown_after_stop_only']:
                    if exit_signal in {'TRAILING_STOP', 'INITIAL_STOP'}:
                        cooldown_until_index[security_id] = current_index + int(config['cooldown_bars'])
                        last_stop_index[security_id] = current_index
                else:
                    cooldown_until_index[security_id] = current_index + int(config['cooldown_bars'])
                    if exit_signal in {'TRAILING_STOP', 'INITIAL_STOP'}:
                        last_stop_index[security_id] = current_index
                exiting.append(security_id)

        for security_id in exiting:
            positions.pop(security_id, None)

        slots = MAX_CONCURRENT_POSITIONS - len(positions)
        if slots > 0:
            candidates: list[tuple[float, int, CandleRow, int]] = []
            for security_id, rows in by_security.items():
                if security_id in positions:
                    continue

                candle = by_security_date.get(security_id, {}).get(current_date)
                if candle is None:
                    continue

                index = date_index_lookup[security_id].get(current_date)
                if index is None:
                    continue

                if not signal_flags[security_id][index]:
                    continue

                if current_index <= cooldown_until_index.get(security_id, -1):
                    blocked_by_cooldown_signals += 1
                    continue

                recently_stopped = (current_index - last_stop_index.get(security_id, -1000000)) <= 20
                score = _candidate_score(
                    candle=candle,
                    rows=rows,
                    index=index,
                    recently_stopped=recently_stopped,
                    config=config,
                )
                candidates.append((score, security_id, candle, index))

            candidates.sort(key=lambda item: item[0], reverse=True)
            for _score, security_id, candle, _index in candidates:
                slots_remaining = MAX_CONCURRENT_POSITIONS - len(positions)
                if slots_remaining <= 0:
                    break

                target_allocation = (cash / Decimal(slots_remaining)) * Decimal(str(config['position_size_fraction']))
                if target_allocation <= 0:
                    continue

                entry_price = candle.close
                quantity = int(target_allocation / entry_price) if entry_price > 0 else 0
                if quantity < 1:
                    continue

                invested_capital = Decimal(quantity) * entry_price
                if invested_capital > cash:
                    continue

                cash -= invested_capital
                initial_stop = entry_price * STOP_RATIO
                positions[security_id] = Position(
                    security_id=security_id,
                    ticker=candle.ticker,
                    entry_date=current_date,
                    entry_price=entry_price,
                    initial_stop=initial_stop,
                    trailing_stop=initial_stop,
                    best_high=candle.high,
                    entry_pattern=candle.candle_type,
                    entry_body_size_pct=candle.body_size_pct,
                    entry_close_position_pct=candle.close_position_pct,
                    entry_signal_high=candle.high,
                    quantity=quantity,
                    invested_capital=invested_capital,
                )

        equity = _current_equity(cash=cash, positions=positions, by_security_date=by_security_date, current_date=current_date)
        if equity > peak:
            peak = equity
        drawdown_pct = ((peak - equity) / peak) * Decimal('100') if peak > 0 else Decimal('0')
        if drawdown_pct > max_drawdown_pct:
            max_drawdown_pct = drawdown_pct

        invested_market_value = equity - cash
        utilization = float((invested_market_value / equity) * Decimal('100')) if equity > 0 else 0.0
        utilization_samples.append(utilization)

    # Close open positions at final close.
    if dates:
        final_date = dates[-1]
        for security_id, position in positions.items():
            candle = by_security_date.get(security_id, {}).get(final_date)
            if candle is None:
                continue

            exit_price = candle.close
            proceeds = Decimal(position.quantity) * exit_price
            entry_value = Decimal(position.quantity) * position.entry_price
            net_pnl = proceeds - entry_value
            return_pct = (net_pnl / entry_value) * Decimal('100') if entry_value > 0 else Decimal('0')
            trades.append(
                {
                    'security_id': security_id,
                    'ticker': position.ticker,
                    'entry_date': position.entry_date,
                    'exit_date': final_date,
                    'entry_price': position.entry_price,
                    'exit_price': exit_price,
                    'quantity': position.quantity,
                    'entry_value': entry_value,
                    'exit_value': proceeds,
                    'net_pnl': net_pnl,
                    'return_pct': return_pct,
                    'bars_held': position.bars_held,
                    'entry_pattern': position.entry_pattern,
                    'exit_signal': 'FORCE_CLOSE_END',
                }
            )
            cash += proceeds

    final_capital = cash

    return _build_summary(
        config=config,
        initial_capital=initial_capital,
        final_capital=final_capital,
        max_drawdown_pct=max_drawdown_pct,
        trades=trades,
        blocked_by_cooldown_signals=blocked_by_cooldown_signals,
        time_stop_exits=time_stop_exits,
        trailing_stop_exits=trailing_stop_exits,
        initial_stop_exits=initial_stop_exits,
        avg_capital_utilization_pct=mean(utilization_samples) if utilization_samples else 0.0,
    )


def _build_summary(
    config: dict[str, Any],
    initial_capital: Decimal,
    final_capital: Decimal,
    max_drawdown_pct: Decimal,
    trades: list[dict[str, Any]],
    blocked_by_cooldown_signals: int,
    time_stop_exits: int,
    trailing_stop_exits: int,
    initial_stop_exits: int,
    avg_capital_utilization_pct: float,
) -> dict[str, Any]:
    returns = [float(trade['return_pct']) for trade in trades]
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value <= 0]
    holdings = [trade['bars_held'] for trade in trades]
    gross_profit = sum([float(trade['net_pnl']) for trade in trades if float(trade['net_pnl']) > 0])
    gross_loss = abs(sum([float(trade['net_pnl']) for trade in trades if float(trade['net_pnl']) <= 0]))

    total_trades = len(trades)
    winning_trades = len(wins)
    losing_trades = len(losses)
    total_return_pct = float(((final_capital - initial_capital) / initial_capital) * Decimal('100')) if initial_capital > 0 else 0.0
    win_rate_pct = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0
    avg_trade_return_pct = mean(returns) if returns else 0.0
    avg_holding_period = mean(holdings) if holdings else 0.0
    avg_winner = mean(wins) if wins else 0.0
    avg_loser = mean(losses) if losses else 0.0
    median_trade_return = median(returns) if returns else 0.0
    sharpe_ratio = 0.0
    if len(returns) > 1:
        std = stdev(returns)
        if std > 0:
            sharpe_ratio = (mean(returns) / std) * sqrt(len(returns))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None
    best_trade = max(returns) if returns else 0.0
    worst_trade = min(returns) if returns else 0.0

    return {
        'config_name': config['name'],
        'hard_rules': {
            'max_concurrent_positions': MAX_CONCURRENT_POSITIONS,
            'initial_sl_pct': float(INITIAL_SL_PCT),
            'trailing_sl_pct': float(TRAILING_SL_PCT),
            'trailing_reference': 'best_day_high',
            'cooldown_bars': int(config['cooldown_bars']),
            'max_holding_bars': int(config['max_holding_bars']),
        },
        'filters': config,
        'summary': {
            'initial_capital': float(initial_capital),
            'final_capital': float(final_capital),
            'total_return_pct': round(total_return_pct, 4),
            'max_drawdown_pct': round(float(max_drawdown_pct), 4),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate_pct': round(win_rate_pct, 4),
            'avg_trade_return_pct': round(avg_trade_return_pct, 4),
            'avg_holding_period_bars': round(avg_holding_period, 4),
            'avg_winner_return_pct': round(avg_winner, 4),
            'avg_loser_return_pct': round(avg_loser, 4),
            'sharpe_ratio': round(sharpe_ratio, 4),
            'profit_factor': None if profit_factor is None else round(profit_factor, 4),
            'median_trade_return_pct': round(median_trade_return, 4),
            'best_trade_return_pct': round(best_trade, 4),
            'worst_trade_return_pct': round(worst_trade, 4),
            'blocked_by_cooldown_signals': blocked_by_cooldown_signals,
            'time_stop_exits': time_stop_exits,
            'trailing_stop_exits': trailing_stop_exits,
            'initial_stop_exits': initial_stop_exits,
            'avg_capital_utilization_pct': round(avg_capital_utilization_pct, 4),
        },
        'trades_preview': [
            {
                'ticker': trade['ticker'],
                'entry_date': str(trade['entry_date']),
                'exit_date': str(trade['exit_date']),
                'return_pct': round(float(trade['return_pct']), 4),
                'bars_held': trade['bars_held'],
                'entry_pattern': trade['entry_pattern'],
                'exit_signal': trade['exit_signal'],
                'quantity': trade.get('quantity', 0),
            }
            for trade in trades[:20]
        ],
    }


def main() -> None:
    by_security = _load_rows()
    dates, by_security_date = _to_calendar(by_security)
    configs = _make_configs()

    results = [_simulate(by_security=by_security, dates=dates, by_security_date=by_security_date, config=config) for config in configs]
    results.sort(key=lambda item: item['summary']['total_return_pct'], reverse=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_path = OUTPUT_DIR / f'analysis_matrix_{stamp}.json'
    csv_path = OUTPUT_DIR / f'analysis_matrix_{stamp}.csv'

    with json_path.open('w', encoding='utf-8') as handle:
        json.dump({'generated_at': datetime.now().isoformat(timespec='seconds'), 'results': results}, handle, indent=2)

    with csv_path.open('w', newline='', encoding='utf-8') as handle:
        fieldnames = [
            'config_name',
            'total_return_pct',
            'max_drawdown_pct',
            'win_rate_pct',
            'avg_trade_return_pct',
            'avg_holding_period_bars',
            'avg_winner_return_pct',
            'avg_loser_return_pct',
            'sharpe_ratio',
            'profit_factor',
            'blocked_by_cooldown_signals',
            'time_stop_exits',
            'trailing_stop_exits',
            'initial_stop_exits',
            'avg_capital_utilization_pct',
            'total_trades',
            'winning_trades',
            'losing_trades',
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in results:
            summary = item['summary']
            writer.writerow({'config_name': item['config_name'], **{k: summary[k] for k in fieldnames if k != 'config_name'}})

    print('Top configurations:')
    for idx, item in enumerate(results[:5], start=1):
        summary = item['summary']
        print(
            f"{idx}. {item['config_name']} return={summary['total_return_pct']:.2f}% "
            f"sharpe={summary['sharpe_ratio']:.2f} pf={summary['profit_factor']} dd={summary['max_drawdown_pct']:.2f}%"
        )

    print(f'JSON: {json_path}')
    print(f'CSV: {csv_path}')


if __name__ == '__main__':
    main()