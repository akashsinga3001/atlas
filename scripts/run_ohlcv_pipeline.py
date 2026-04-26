"""Manual terminal runner for OHLCV pipeline and individual tasks."""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jobs.ohlcv import daily_ohlcv_pipeline
from services.feature import FeatureService
from services.ohlcv import OhlcvService


def _print_json(payload: Any) -> None:
    """Print structured output in readable JSON format."""
    print(json.dumps(payload, indent=2, default=str))


def _print_pipeline_results(result: dict) -> None:
    """Display full pipeline results in readable format."""
    success = result.get('success')
    status = '✓ SUCCESS' if success else '✗ FAILED'

    print(f'\nOverall Status: {status}')
    print()

    # Ingestion
    ing = result.get('ingestion', {})
    print('📥 INGESTION (1DAY):')
    print(f'   Status: {"✓ Success" if ing.get("success") else "✗ Failed"}')
    print(f'   Securities processed: {ing.get("processed", 0)}')
    print(f'   Candles inserted/updated: {ing.get("inserted_or_updated", 0)}')
    print(f'   Errors: {ing.get("errors_count", 0)}')
    print(f'   Duplicates deduplicated: {ing.get("duplicate_candles_deduplicated", 0)}')
    print()

    # Weekly aggregation
    weekly = result.get('weekly_aggregation', {})
    print('📊 WEEKLY AGGREGATION (1WEEK):')
    print(f'   Status: {"✓ Success" if weekly.get("success") else "✗ Failed"}')
    print(f'   Candles created: {weekly.get("inserted_or_updated", 0)}')
    print(f'   Groups aggregated: {weekly.get("groups_aggregated", 0)}')
    print(f'   Affected securities: {weekly.get("affected_security_count", 0)}')
    print()

    # Monthly aggregation
    monthly = result.get('monthly_aggregation', {})
    print('📊 MONTHLY AGGREGATION (1MONTH):')
    print(f'   Status: {"✓ Success" if monthly.get("success") else "✗ Failed"}')
    print(f'   Candles created: {monthly.get("inserted_or_updated", 0)}')
    print(f'   Groups aggregated: {monthly.get("groups_aggregated", 0)}')
    print(f'   Affected securities: {monthly.get("affected_security_count", 0)}')
    print()

    # Features
    feat = result.get('features', {})
    print('🎯 FEATURES:')
    print(f'   Status: {"✓ Success" if feat.get("success") else "✗ Failed"}')
    print(f'   Candles processed: {feat.get("candles_processed", 0)}')
    print(f'   Features inserted/updated: {feat.get("inserted_or_updated", 0)}')
    print(f'   Lookback days: {feat.get("lookback_days", 0)}')
    print()


def _run_pipeline_sync(force_backfill: bool, feature_lookback_days: int, feature_backfill: bool) -> None:
    """Run the full orchestrator pipeline synchronously."""
    print(f'\n{"="*70}')
    print(f'Running OHLCV Pipeline (Sync Mode) - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'{"="*70}')
    print(f'Stages: ingestion → weekly aggregation → monthly aggregation → features')
    print(f'Feature mode: {"ALL OHLCV records (backfill)" if feature_backfill else f"Last {feature_lookback_days} days"}')
    print()

    svc = OhlcvService()
    result = svc.run_daily_pipeline(force_backfill=force_backfill, feature_lookback_days=feature_lookback_days, feature_backfill=feature_backfill)
    _print_pipeline_results(result)

    print(f'{"="*70}\n')


def _run_ingestion_sync(force_backfill: bool) -> None:
    """Run OHLCV ingestion stage synchronously."""
    print(f'\n{"="*70}')
    print(f'Running OHLCV Ingestion (1DAY) - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'{"="*70}')
    print()

    svc = OhlcvService()
    result = svc.upsert_daily_ohlcv(force_backfill=force_backfill)

    status = '✓ SUCCESS' if result.get('success') else '✗ FAILED'
    print(f'Status: {status}')
    print(f'Securities processed: {result.get("processed", 0)}')
    print(f'Candles inserted/updated: {result.get("inserted_or_updated", 0)}')
    print(f'Errors: {result.get("errors_count", 0)}')
    print(f'Duplicates deduplicated: {result.get("duplicate_candles_deduplicated", 0)}')

    if result.get('errors'):
        print(f'\nFirst 5 errors:')
        for err in result.get('errors', [])[:5]:
            print(f'  - {err}')

    print(f'\n{"="*70}\n')


def _run_features_sync(lookback_days: int, backfill: bool = False) -> None:
    """Run feature calculation stage synchronously.
    
    Args:
        lookback_days: Days to lookback (ignored if backfill=True)
        backfill: If True, calculate for ALL OHLCV records; if False, use lookback_days
    """
    print(f'\n{"="*70}')
    print(f'Running Feature Calculation - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'{"="*70}')
    mode = "ALL OHLCV records (backfill)" if backfill else f"Last {lookback_days} days"
    print(f'Mode: {mode}')
    print()

    svc = FeatureService()
    result = svc.upsert_features(lookback_days=lookback_days, backfill=backfill)

    status = '✓ SUCCESS' if result.get('success') else '✗ FAILED'
    print(f'Status: {status}')
    print(f'Candles processed: {result.get("candles_processed", 0)}')
    print(f'Features inserted/updated: {result.get("inserted_or_updated", 0)}')
    if not backfill:
        print(f'Lookback days: {result.get("lookback_days", 0)}')
    print()
    print(f'Lookback days: {result.get("lookback_days", 0)}')

    print(f'\n{"="*70}\n')


def _run_pipeline_async(force_backfill: bool, feature_lookback_days: int, feature_backfill: bool) -> None:
    """Enqueue the full orchestrator pipeline to Celery worker."""
    print(f'\n{"="*70}')
    print(f'Enqueueing OHLCV Pipeline (Async Mode) - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'{"="*70}')
    print()

    result = daily_ohlcv_pipeline.delay(force_backfill=force_backfill, feature_lookback_days=feature_lookback_days, feature_backfill=feature_backfill)

    print(f'✓ Task enqueued to Celery')
    print(f'Task ID: {result.id}')
    print(f'Status: {result.status}')

    print(f'\nTo check status: python scripts/run_ohlcv_pipeline.py --task pipeline --mode status --task-id {result.id}')
    print(f'{"="*70}\n')


def main() -> None:
    """Parse CLI arguments and run the requested OHLCV task."""
    parser = argparse.ArgumentParser(
        description='Run OHLCV pipeline: ingestion → aggregation → features',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Full pipeline (all stages)
  python scripts/run_ohlcv_pipeline.py --task pipeline
  python scripts/run_ohlcv_pipeline.py --task pipeline --backfill
  python scripts/run_ohlcv_pipeline.py --task pipeline --days 30
  
  # Full pipeline with feature backfill (one-time full coverage)
  python scripts/run_ohlcv_pipeline.py --task pipeline --feature-backfill
  
  # Individual stages
  python scripts/run_ohlcv_pipeline.py --task ingestion
  python scripts/run_ohlcv_pipeline.py --task features --days 30
  python scripts/run_ohlcv_pipeline.py --task features --feature-backfill
  
  # Async mode (enqueue to Celery worker)
  python scripts/run_ohlcv_pipeline.py --task pipeline --mode async
        ''',
    )

    parser.add_argument(
        '--task',
        type=str,
        default='pipeline',
        choices=['pipeline', 'ingestion', 'features'],
        help='Task to run (default: pipeline - all stages)',
    )

    parser.add_argument(
        '--mode',
        type=str,
        default='sync',
        choices=['sync', 'async'],
        help='sync: run now in this process | async: enqueue to Celery worker (default: sync)',
    )

    parser.add_argument(
        '--backfill',
        action='store_true',
        help='Force 5-year backfill for OHLCV ingestion (slow, ~15-20 minutes)',
    )

    parser.add_argument(
        '--days',
        type=int,
        default=90,
        help='Lookback days for features (default: 90, ignored if --feature-backfill)',
    )

    parser.add_argument(
        '--feature-backfill',
        action='store_true',
        help='Calculate features for ALL OHLCV records (one-time backfill for complete coverage)',
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON (sync mode only)',
    )

    args = parser.parse_args()

    try:
        if args.task == 'pipeline':
            if args.mode == 'sync':
                _run_pipeline_sync(force_backfill=args.backfill, feature_lookback_days=args.days, feature_backfill=args.feature_backfill)
            else:
                _run_pipeline_async(force_backfill=args.backfill, feature_lookback_days=args.days, feature_backfill=args.feature_backfill)

        elif args.task == 'ingestion':
            if args.mode == 'sync':
                _run_ingestion_sync(force_backfill=args.backfill)
            else:
                print('Ingestion task does not support async mode. Use --mode sync')
                sys.exit(1)

        elif args.task == 'features':
            if args.mode == 'sync':
                _run_features_sync(lookback_days=args.days, backfill=args.feature_backfill)
            else:
                print('Features task does not support async mode. Use --mode sync')
                sys.exit(1)

    except Exception as e:
        print(f'\n{"="*70}')
        print(f'✗ Error: {str(e)}')
        print(f'{"="*70}\n')
        sys.exit(1)


if __name__ == '__main__':
    main()
