"""Run a compact parameter sweep for the bullish candle strategy and rank results."""

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.backtest import BacktestService


OUTPUT_DIR = PROJECT_ROOT / 'artifacts' / 'reports' / 'bullish_candle_optimization'


def _parse_date(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


def _as_float(value: Any) -> float:
    return float(Decimal(str(value)))


def _config_space() -> list[dict[str, Any]]:
    core_patterns = [
        'marubozu_full_bullish',
        'doji_dragonfly',
        'strong_bullish_candle',
        'rising_three_methods',
        'bullish_harami',
        'marubozu_close_bullish',
    ]

    extended_patterns = core_patterns + [
        'morning_star',
        'inverted_hammer',
        'bullish_engulfing',
        'piercing_line',
        'hammer',
    ]

    configs = [
        {
            'name': 'core_breakout_trend_strict',
            'entry_patterns': ','.join(core_patterns),
            'min_body_size_pct': Decimal('25'),
            'min_close_position_pct': Decimal('60'),
            'require_close_above_sma20': True,
            'require_sma20_above_sma50': True,
            'use_breakout_confirmation': True,
        },
        {
            'name': 'core_breakout_trend_balanced',
            'entry_patterns': ','.join(core_patterns),
            'min_body_size_pct': Decimal('20'),
            'min_close_position_pct': Decimal('55'),
            'require_close_above_sma20': True,
            'require_sma20_above_sma50': True,
            'use_breakout_confirmation': True,
        },
        {
            'name': 'core_no_breakout_trend',
            'entry_patterns': ','.join(core_patterns),
            'min_body_size_pct': Decimal('20'),
            'min_close_position_pct': Decimal('55'),
            'require_close_above_sma20': True,
            'require_sma20_above_sma50': True,
            'use_breakout_confirmation': False,
        },
        {
            'name': 'extended_breakout_trend',
            'entry_patterns': ','.join(extended_patterns),
            'min_body_size_pct': Decimal('20'),
            'min_close_position_pct': Decimal('55'),
            'require_close_above_sma20': True,
            'require_sma20_above_sma50': True,
            'use_breakout_confirmation': True,
        },
        {
            'name': 'extended_breakout_only_sma20',
            'entry_patterns': ','.join(extended_patterns),
            'min_body_size_pct': Decimal('20'),
            'min_close_position_pct': Decimal('55'),
            'require_close_above_sma20': True,
            'require_sma20_above_sma50': False,
            'use_breakout_confirmation': True,
        },
        {
            'name': 'extended_no_breakout_only_sma20',
            'entry_patterns': ','.join(extended_patterns),
            'min_body_size_pct': Decimal('20'),
            'min_close_position_pct': Decimal('55'),
            'require_close_above_sma20': True,
            'require_sma20_above_sma50': False,
            'use_breakout_confirmation': False,
        },
        {
            'name': 'extended_breakout_loose_quality',
            'entry_patterns': ','.join(extended_patterns),
            'min_body_size_pct': Decimal('15'),
            'min_close_position_pct': Decimal('50'),
            'require_close_above_sma20': True,
            'require_sma20_above_sma50': True,
            'use_breakout_confirmation': True,
        },
        {
            'name': 'extended_breakout_strict_quality',
            'entry_patterns': ','.join(extended_patterns),
            'min_body_size_pct': Decimal('30'),
            'min_close_position_pct': Decimal('65'),
            'require_close_above_sma20': True,
            'require_sma20_above_sma50': True,
            'use_breakout_confirmation': True,
        },
        {
            'name': 'core_breakout_no_trend_filters',
            'entry_patterns': ','.join(core_patterns),
            'min_body_size_pct': Decimal('25'),
            'min_close_position_pct': Decimal('60'),
            'require_close_above_sma20': False,
            'require_sma20_above_sma50': False,
            'use_breakout_confirmation': True,
        },
        {
            'name': 'extended_no_breakout_no_trend',
            'entry_patterns': ','.join(extended_patterns),
            'min_body_size_pct': Decimal('20'),
            'min_close_position_pct': Decimal('55'),
            'require_close_above_sma20': False,
            'require_sma20_above_sma50': False,
            'use_breakout_confirmation': False,
        },
    ]

    return configs


def _score(row: dict[str, Any]) -> tuple[float, float, float]:
    total_return = row['total_return_pct']
    sharpe = row['sharpe_ratio']
    drawdown = row['max_drawdown_pct']
    return (total_return, sharpe, -drawdown)


def main() -> None:
    parser = argparse.ArgumentParser(description='Optimize bullish candle strategy with compact config sweep.')
    parser.add_argument('--start-date', type=str, default=None, help='Optional start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', type=str, default=None, help='Optional end date (YYYY-MM-DD).')
    parser.add_argument('--max-configs', type=int, default=10, help='Max number of configs to run from internal sweep list.')
    args = parser.parse_args()

    service = BacktestService()
    configs = _config_space()[: max(1, args.max_configs)]
    start_date = _parse_date(args.start_date)
    end_date = _parse_date(args.end_date)

    rows: list[dict[str, Any]] = []
    for config in configs:
        params = {
            'entry_patterns': config['entry_patterns'],
            'initial_sl_pct': Decimal('3'),
            'trailing_sl_pct': Decimal('3'),
            'min_body_size_pct': config['min_body_size_pct'],
            'min_close_position_pct': config['min_close_position_pct'],
            'require_close_above_sma20': config['require_close_above_sma20'],
            'require_sma20_above_sma50': config['require_sma20_above_sma50'],
            'use_breakout_confirmation': config['use_breakout_confirmation'],
        }

        result = service.run_backtest(
            strategy_name='bullish_candle_signal',
            strategy_params=params,
            timeframe='1DAY',
            start_date=start_date,
            end_date=end_date,
            allow_short=False,
        )

        summary = result['summary']
        row = {
            'config_name': config['name'],
            'run_id': result['run_id'],
            'total_return_pct': _as_float(summary['total_return_pct']),
            'max_drawdown_pct': _as_float(summary['max_drawdown_pct']),
            'win_rate_pct': _as_float(summary['win_rate_pct']),
            'sharpe_ratio': _as_float(summary['sharpe_ratio']),
            'profit_factor': None if summary['profit_factor'] is None else _as_float(summary['profit_factor']),
            'avg_trade_return_pct': _as_float(summary['avg_trade_return_pct']),
            'avg_holding_period_bars': _as_float(summary['avg_holding_period_bars']),
            'total_trades': int(summary['total_trades']),
            'winning_trades': int(summary['winning_trades']),
            'losing_trades': int(summary['losing_trades']),
            'params': params,
        }
        rows.append(row)

        print(
            f"[{config['name']}] run_id={row['run_id']} return={row['total_return_pct']:.2f}% "
            f"sharpe={row['sharpe_ratio']:.2f} pf={row['profit_factor'] if row['profit_factor'] is not None else 'NA'} "
            f"dd={row['max_drawdown_pct']:.2f}% trades={row['total_trades']}"
        )

    rows.sort(key=_score, reverse=True)
    for rank, row in enumerate(rows, start=1):
        row['rank'] = rank

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_path = OUTPUT_DIR / f'optimization_{timestamp}.json'
    csv_path = OUTPUT_DIR / f'optimization_{timestamp}.csv'

    with json_path.open('w', encoding='utf-8') as handle:
        json.dump(
            {
                'generated_at': datetime.now().isoformat(timespec='seconds'),
                'start_date': args.start_date,
                'end_date': args.end_date,
                'rows': rows,
            },
            handle,
            indent=2,
            default=str,
        )

    fieldnames = [
        'rank',
        'config_name',
        'run_id',
        'total_return_pct',
        'max_drawdown_pct',
        'win_rate_pct',
        'sharpe_ratio',
        'profit_factor',
        'avg_trade_return_pct',
        'avg_holding_period_bars',
        'total_trades',
        'winning_trades',
        'losing_trades',
    ]
    with csv_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})

    print('')
    print('Top 5 configs:')
    for row in rows[:5]:
        print(
            f"  #{row['rank']} {row['config_name']} run_id={row['run_id']} "
            f"return={row['total_return_pct']:.2f}% sharpe={row['sharpe_ratio']:.2f} "
            f"pf={row['profit_factor'] if row['profit_factor'] is not None else 'NA'} dd={row['max_drawdown_pct']:.2f}%"
        )

    print('')
    print(f'Results saved: {json_path}')
    print(f'Results saved: {csv_path}')


if __name__ == '__main__':
    main()