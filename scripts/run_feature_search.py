"""Grid search over top-K feature counts to identify the optimal feature subset size.

Runs one full walk-forward backtest per top_k value and prints a ranked comparison
table sorted by profit_factor descending.

Usage:
    py scripts/run_feature_search.py --start 2024-01-01 --end 2024-12-31 \
        --train-window 180 --test-window 60 --step 60 \
        --model rf --min-confidence 0.55 --long-only \
        --top-k-values 15 20 25 30 35 40 45 50 0
"""

import argparse
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import joblib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from services.ml_backtest import MlBacktestService, WalkForwardConfig
from services.ml_risk import RiskParameters
from utils.ml_paths import weekly_run_directory
from utils.logger import logger


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Grid search over top-K feature counts',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Date range
    parser.add_argument('--start', type=str, required=True, help='Overall start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=True, help='Overall end date (YYYY-MM-DD)')

    # Walk-forward windows
    parser.add_argument('--train-window', type=int, default=180, help='Training window in days')
    parser.add_argument('--test-window', type=int, default=60, help='Test window in days')
    parser.add_argument('--step', type=int, default=60, help='Fold step size in days')

    # Model
    parser.add_argument('--model', type=str, default='rf',
                        choices=['rf', 'lgb', 'xgb', 'ensemble'], help='Model type')
    parser.add_argument('--top-n', type=int, default=5, help='Max signals per direction per day')

    # Risk
    parser.add_argument('--portfolio', type=float, default=1_000_000.0)
    parser.add_argument('--max-pos-pct', type=float, default=0.05)
    parser.add_argument('--max-positions', type=int, default=10)
    parser.add_argument('--stop-loss', type=float, default=0.03)
    parser.add_argument('--take-profit', type=float, default=0.08)
    parser.add_argument('--min-confidence', type=float, default=0.55)
    parser.add_argument('--commission', type=float, default=0.001)

    # Direction filter
    parser.add_argument('--long-only', dest='long_only', action='store_true',
                        help='Trade long side only')

    # Feature search grid
    parser.add_argument(
        '--top-k-values',
        type=int,
        nargs='+',
        default=[10, 15, 20, 25, 30, 35, 40, 45, 50, 0],
        help='List of top-K values to try. 0 = use all features.',
    )

    return parser.parse_args()


def _run_one(args: argparse.Namespace, top_k: int) -> dict[str, Any]:
    """Run a single backtest with a given top_k override.

    Args:
        args: Parsed CLI arguments.
        top_k: Number of top features to retain for this run.

    Returns:
        Result dict from MlBacktestService.run().
    """
    # Override the global setting for this run
    settings.ML_FEATURE_TOP_K = top_k

    label = 'all' if top_k == 0 else str(top_k)
    run_name = f'feat_search_k{label}_{date.today().isoformat()}_{int(time.time())}'

    directions = ['long'] if args.long_only else ['long', 'short']

    risk = RiskParameters(
        portfolio_value=args.portfolio,
        max_position_pct=args.max_pos_pct,
        max_open_positions=args.max_positions,
        stop_loss_pct=args.stop_loss,
        take_profit_pct=args.take_profit,
        min_confidence=args.min_confidence,
        commission_pct=args.commission,
    )

    config = WalkForwardConfig(
        backtest_name=run_name,
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
        notes=f'feature_search top_k={label}',
        directions=directions,
    )

    service = MlBacktestService()
    return service.run(config)


def _fold_windows(args: argparse.Namespace) -> list[tuple[date, date, date, date]]:
    """Build fold windows to locate per-fold model artifacts.

    Args:
        args: Parsed CLI args containing date range and windows.

    Returns:
        List of tuples: (train_start, train_end, test_start, test_end).
    """
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    windows: list[tuple[date, date, date, date]] = []

    test_start = start + timedelta(days=args.train_window)
    while test_start + timedelta(days=args.test_window - 1) <= end:
        train_start = test_start - timedelta(days=args.train_window)
        train_end = test_start - timedelta(days=1)
        test_end = test_start + timedelta(days=args.test_window - 1)
        windows.append((train_start, train_end, test_start, test_end))
        test_start += timedelta(days=args.step)

    return windows


def _collect_fold_feature_sets(args: argparse.Namespace) -> list[list[str]]:
    """Load selected feature columns from each fold's trained long model.

    Args:
        args: Parsed CLI arguments.

    Returns:
        List of feature lists, one per fold model that could be loaded.
    """
    model_file = f"long_{args.model}.joblib"
    fold_sets: list[list[str]] = []

    for _, train_end, _, _ in _fold_windows(args):
        model_dir = weekly_run_directory(settings.ML_ARTIFACT_DIR, train_end)
        model_path = Path(model_dir) / model_file
        if not model_path.exists():
            continue

        bundle = joblib.load(str(model_path).replace('\\', '/'))
        cols = bundle.get('feature_columns', [])
        if cols:
            fold_sets.append([str(c) for c in cols])

    return fold_sets


def _feature_stability(fold_sets: list[list[str]]) -> dict[str, Any]:
    """Summarize stable feature combinations across folds.

    Args:
        fold_sets: Selected feature columns per fold.

    Returns:
        Dict with consensus and frequent feature lists.
    """
    if not fold_sets:
        return {
            'fold_count': 0,
            'consensus_features': [],
            'features_in_at_least_2_folds': [],
            'stability_ratio': 0.0,
        }

    fold_count = len(fold_sets)
    as_sets = [set(cols) for cols in fold_sets]

    consensus = sorted(set.intersection(*as_sets)) if as_sets else []

    counts: dict[str, int] = {}
    for cols in fold_sets:
        for feature in set(cols):
            counts[feature] = counts.get(feature, 0) + 1

    at_least_2 = sorted(
        [feature for feature, count in counts.items() if count >= 2],
        key=lambda feat: (-counts[feat], feat),
    )

    baseline_size = len(fold_sets[0]) if fold_sets else 0
    stability_ratio = (len(consensus) / baseline_size) if baseline_size > 0 else 0.0

    return {
        'fold_count': fold_count,
        'consensus_features': consensus,
        'features_in_at_least_2_folds': at_least_2,
        'stability_ratio': round(stability_ratio, 4),
    }


def _print_table(rows: list[dict[str, Any]]) -> None:
    """Print a formatted comparison table sorted by profit_factor descending.

    Args:
        rows: List of result summary dicts, one per top_k value.
    """
    rows_sorted = sorted(rows, key=lambda r: r['profit_factor'], reverse=True)

    header = (
        f"{'top_k':>6}  {'return%':>8}  {'sharpe':>7}  {'drawdown%':>9}  "
        f"{'win_rate%':>9}  {'profit_f':>8}  {'avg_pnl%':>8}  {'stability':>9}  "
        f"{'trades':>6}  {'runtime_s':>9}"
    )
    sep = '-' * len(header)

    print('\n' + sep)
    print('FEATURE SEARCH RESULTS — sorted by profit_factor')
    print(sep)
    print(header)
    print(sep)

    for row in rows_sorted:
        k_label = 'all' if row['top_k'] == 0 else str(row['top_k'])
        print(
            f"{k_label:>6}  "
            f"{row['total_return_pct']:>8.3f}  "
            f"{row['sharpe_ratio']:>7.4f}  "
            f"{row['max_drawdown_pct']:>9.3f}  "
            f"{row['win_rate_pct']:>9.2f}  "
            f"{row['profit_factor']:>8.4f}  "
            f"{row['avg_pnl_pct']:>8.4f}  "
            f"{row['stability_ratio']:>9.4f}  "
            f"{row['total_trades']:>6.0f}  "
            f"{row['runtime_s']:>9.1f}"
        )

    print(sep)
    best = rows_sorted[0]
    k_label = 'all' if best['top_k'] == 0 else str(best['top_k'])
    print(f"\nBest top_k = {k_label}  profit_factor={best['profit_factor']:.4f}  "
          f"return={best['total_return_pct']:.3f}%  sharpe={best['sharpe_ratio']:.4f}")

    consensus = best.get('consensus_features', [])
    frequent = best.get('features_in_at_least_2_folds', [])

    print('\nBest combination candidates:')
    print(f"- Consensus across all folds ({len(consensus)}):")
    print(', '.join(consensus) if consensus else 'none')
    print(f"- Appearing in at least 2 folds ({len(frequent)}):")
    print(', '.join(frequent) if frequent else 'none')
    print(sep + '\n')


def main() -> None:
    """Entry point: iterate over top_k grid, collect results, print comparison."""
    args = _parse_args()
    direction_label = 'long-only' if args.long_only else 'long+short'
    logger.info(
        'Feature search starting grid={} model={} direction={} date_range={}/{}',
        args.top_k_values,
        args.model,
        direction_label,
        args.start,
        args.end,
    )

    results: list[dict[str, Any]] = []

    for top_k in args.top_k_values:
        k_label = 'all' if top_k == 0 else str(top_k)
        logger.info('--- Running top_k={} ---', k_label)
        t0 = time.perf_counter()

        try:
            result = _run_one(args, top_k)
            elapsed = round(time.perf_counter() - t0, 1)
            agg = result['aggregate_metrics']
            stability = _feature_stability(_collect_fold_feature_sets(args))
            results.append({
                'top_k': top_k,
                'total_return_pct': agg.get('total_return_pct', 0.0),
                'sharpe_ratio': agg.get('sharpe_ratio', 0.0),
                'max_drawdown_pct': agg.get('max_drawdown_pct', 0.0),
                'win_rate_pct': agg.get('win_rate_pct', 0.0),
                'profit_factor': agg.get('profit_factor', 0.0),
                'avg_pnl_pct': agg.get('avg_pnl_pct', 0.0),
                'total_trades': agg.get('total_trades', 0.0),
                'runtime_s': elapsed,
                'backtest_run_id': result['backtest_run_id'],
                'stability_ratio': stability['stability_ratio'],
                'consensus_features': stability['consensus_features'],
                'features_in_at_least_2_folds': stability['features_in_at_least_2_folds'],
            })
            logger.info(
                'top_k={} done: return={:.3f}% sharpe={:.4f} profit_factor={:.4f} stability={:.4f} runtime_s={}',
                k_label,
                agg.get('total_return_pct', 0.0),
                agg.get('sharpe_ratio', 0.0),
                agg.get('profit_factor', 0.0),
                stability['stability_ratio'],
                elapsed,
            )
        except Exception as exc:
            logger.error('top_k={} failed: {}', k_label, str(exc))
            results.append({
                'top_k': top_k,
                'total_return_pct': 0.0,
                'sharpe_ratio': -99.0,
                'max_drawdown_pct': 0.0,
                'win_rate_pct': 0.0,
                'profit_factor': 0.0,
                'avg_pnl_pct': 0.0,
                'total_trades': 0.0,
                'runtime_s': round(time.perf_counter() - t0, 1),
                'backtest_run_id': None,
                'stability_ratio': 0.0,
                'consensus_features': [],
                'features_in_at_least_2_folds': [],
            })

    if results:
        _print_table(results)
    else:
        logger.error('No results collected — all runs failed')


if __name__ == '__main__':
    main()
