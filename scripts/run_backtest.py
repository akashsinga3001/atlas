"""Manual terminal runner for strategy backtesting tasks."""

import argparse
import json
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jobs.backtest import daily_backtest, on_demand_backtest


def _parse_date(value: str) -> date:
    """Parse YYYY-MM-DD date values from CLI arguments."""
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('Date must be YYYY-MM-DD') from exc


def _parse_decimal(value: str) -> Decimal:
    """Parse Decimal values for backtest numeric CLI arguments."""
    return Decimal(value)


def _non_negative_decimal(value: str) -> Decimal:
    """Parse a decimal value and ensure it is non-negative."""
    parsed = Decimal(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError('Value must be >= 0')
    return parsed


def _parse_tickers(raw: str | None) -> list[str] | None:
    """Parse comma-separated ticker list into uppercase symbols."""
    if not raw:
        return None

    parsed = [item.strip().upper() for item in raw.split(',') if item.strip()]
    return parsed or None


def _print_json(payload: Any) -> None:
    """Print structured output in readable JSON format."""
    print(json.dumps(payload, indent=2, default=str))


def _run_now(args: argparse.Namespace) -> dict[str, Any]:
    """Execute selected backtest task synchronously in current process."""
    strategy_params = {
        'short_window': args.short_window,
        'long_window': args.long_window,
    }

    kwargs = {
        'strategy_name': args.strategy,
        'strategy_params': strategy_params,
        'timeframe': args.timeframe,
        'start_date': args.start_date.isoformat() if args.start_date else None,
        'end_date': args.end_date.isoformat() if args.end_date else None,
        'tickers': _parse_tickers(args.tickers),
        'initial_capital': args.initial_capital,
        'transaction_cost_bps': args.transaction_cost_bps,
        'slippage_bps': args.slippage_bps,
        'allow_short': not args.disable_short,
    }

    if args.task == 'daily':
        result = daily_backtest.apply(kwargs=kwargs)
    else:
        kwargs['reason'] = args.reason
        result = on_demand_backtest.apply(kwargs=kwargs)

    return {'task': args.task, 'execution': 'sync', 'state': result.state, 'result': result.result}


def _enqueue(args: argparse.Namespace) -> dict[str, Any]:
    """Enqueue selected backtest task to a Celery worker."""
    strategy_params = {
        'short_window': args.short_window,
        'long_window': args.long_window,
    }

    kwargs = {
        'strategy_name': args.strategy,
        'strategy_params': strategy_params,
        'timeframe': args.timeframe,
        'start_date': args.start_date.isoformat() if args.start_date else None,
        'end_date': args.end_date.isoformat() if args.end_date else None,
        'tickers': _parse_tickers(args.tickers),
        'initial_capital': str(args.initial_capital),
        'transaction_cost_bps': str(args.transaction_cost_bps),
        'slippage_bps': str(args.slippage_bps),
        'allow_short': not args.disable_short,
    }

    if args.task == 'daily':
        async_result = daily_backtest.delay(**kwargs)
    else:
        async_result = on_demand_backtest.delay(reason=args.reason, **kwargs)

    return {'task': args.task, 'execution': 'async', 'task_id': async_result.id, 'status': async_result.status}


def main() -> None:
    """Parse CLI arguments and run or enqueue strategy backtests."""
    parser = argparse.ArgumentParser(description='Run or enqueue backtesting tasks.')
    parser.add_argument('--task', choices=['on_demand', 'daily'], default='on_demand', help='Which backtest task to trigger (default: on_demand).')
    parser.add_argument('--mode', choices=['sync', 'async'], default='sync', help='sync runs now in this process; async enqueues for Celery worker.')
    parser.add_argument('--reason', default='manual_terminal_trigger', help='Reason passed to on-demand backtest task.')

    parser.add_argument('--strategy', choices=['sma_crossover'], default='sma_crossover', help='Strategy to run for backtest.')
    parser.add_argument('--timeframe', choices=['1DAY', '1WEEK', '1MONTH'], default='1DAY', help='Timeframe for backtest candles.')
    parser.add_argument('--start-date', type=_parse_date, default=None, help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', type=_parse_date, default=None, help='End date (YYYY-MM-DD).')
    parser.add_argument('--tickers', default=None, help='Comma-separated ticker symbols to limit the run.')

    parser.add_argument('--short-window', type=int, default=20, help='Short SMA window for crossover strategy.')
    parser.add_argument('--long-window', type=int, default=50, help='Long SMA window for crossover strategy.')

    parser.add_argument('--initial-capital', type=_non_negative_decimal, default=Decimal('100000'), help='Initial capital for the backtest.')
    parser.add_argument('--transaction-cost-bps', type=_non_negative_decimal, default=Decimal('5'), help='Per-side transaction cost in basis points.')
    parser.add_argument('--slippage-bps', type=_non_negative_decimal, default=Decimal('2'), help='Per-trade slippage in basis points.')
    parser.add_argument('--disable-short', action='store_true', help='Disable short-side trades for this run.')

    args = parser.parse_args()
    payload = _enqueue(args) if args.mode == 'async' else _run_now(args)
    _print_json(payload)


if __name__ == '__main__':
    main()
