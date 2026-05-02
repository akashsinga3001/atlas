"""CLI runner for ML walk-forward backtesting."""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from services.ml_backtest import MlBacktestService, WalkForwardConfig
from services.ml_risk import RiskParameters


def _print_json(payload: Any) -> None:
    """Print structured payload as readable JSON."""
    print(json.dumps(payload, indent=2, default=str))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Run ML walk-forward backtest',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Identity
    parser.add_argument('--name', type=str, default=f'wf_backtest_{date.today().isoformat()}',
                        help='Unique name for this backtest run')
    parser.add_argument('--notes', type=str, default=None, help='Optional notes to attach to the run')

    # Date range
    parser.add_argument('--start', type=str, required=True, help='Overall start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=True, help='Overall end date (YYYY-MM-DD)')

    # Walk-forward windows
    parser.add_argument('--train-window', type=int, default=365, help='Training window in days')
    parser.add_argument('--test-window', type=int, default=90, help='Test window in days')
    parser.add_argument('--step', type=int, default=90, help='Fold step size in days')

    # Model
    parser.add_argument('--model', type=str, default='ensemble',
                        choices=['rf', 'lgb', 'xgb', 'ensemble'], help='Model type to use')
    parser.add_argument('--top-n', type=int, default=5, help='Max signals per direction per day')

    # Risk parameters
    parser.add_argument('--portfolio', type=float, default=1_000_000.0, help='Starting portfolio value (INR)')
    parser.add_argument('--max-positions', type=int, default=3, help='Max simultaneous open positions')
    parser.add_argument('--trailing-stop', type=float, default=0.03, help='Trailing stop distance as fraction of high-water mark (e.g. 0.03 = 3%%)')
    parser.add_argument('--min-confidence', type=float, default=0.60, help='Minimum model confidence to enter')
    parser.add_argument('--commission', type=float, default=0.001, help='Round-trip commission fraction')

    # Direction filter
    parser.add_argument('--long-only', dest='long_only', action='store_true',
                        help='Trade long side only; skip short signal generation')

    # Execution mode
    parser.add_argument('--async', dest='async_mode', action='store_true',
                        help='Enqueue to Celery instead of running in-process')

    return parser.parse_args()


def _run_sync(args: argparse.Namespace) -> dict[str, Any]:
    """Execute backtest in-process."""
    risk = RiskParameters(
        portfolio_value=args.portfolio,
        max_open_positions=args.max_positions,
        trailing_stop_pct=args.trailing_stop,
        min_confidence=args.min_confidence,
        commission_pct=args.commission,
    )

    directions = ['long'] if args.long_only else ['long', 'short']

    config = WalkForwardConfig(
        backtest_name=args.name,
        total_start_date=date.fromisoformat(args.start),
        total_end_date=date.fromisoformat(args.end),
        train_window_days=args.train_window,
        test_window_days=args.test_window,
        step_days=args.step,
        horizon_days=int(settings.ML_HORIZON_DAYS),
        threshold_pct=float(settings.ML_MOVE_THRESHOLD_PCT),
        model_type=args.model,
        top_n_per_direction=args.top_n,
        risk=risk,
        notes=args.notes,
        directions=directions,
    )

    service = MlBacktestService()
    return service.run(config)


def _run_async(args: argparse.Namespace) -> dict[str, Any]:
    """Enqueue backtest task to Celery workers."""
    from jobs.backtest import run_ml_walk_forward

    async_result = run_ml_walk_forward.delay(
        backtest_name=args.name,
        total_start_date=args.start,
        total_end_date=args.end,
        train_window_days=args.train_window,
        test_window_days=args.test_window,
        step_days=args.step,
        model_type=args.model,
        top_n_per_direction=args.top_n,
        portfolio_value=args.portfolio,
        max_open_positions=args.max_positions,
        trailing_stop_pct=args.trailing_stop,
        min_confidence=args.min_confidence,
        commission_pct=args.commission,
        notes=args.notes,
    )
    return {
        'task': 'run_ml_walk_forward',
        'execution': 'async',
        'task_id': async_result.id,
        'status': async_result.status,
    }


def main() -> None:
    args = _parse_args()

    try:
        start = date.fromisoformat(args.start)
        end = date.fromisoformat(args.end)
    except ValueError as exc:
        print(f'ERROR: Invalid date format — {exc}')
        sys.exit(1)

    if end <= start:
        print('ERROR: --end must be after --start')
        sys.exit(1)

    if args.async_mode:
        result = _run_async(args)
    else:
        result = _run_sync(args)

    _print_json(result)


if __name__ == '__main__':
    main()
