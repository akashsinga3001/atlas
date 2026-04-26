"""Manual terminal runner for OHLCV Celery tasks."""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jobs.ohlcv import (daily_ohlcv_aggregate_month, daily_ohlcv_aggregate_week, daily_ohlcv_upsert, on_demand_ohlcv_upsert)


def _print_json(payload: Any) -> None:
    """Print structured output in readable JSON format."""
    print(json.dumps(payload, indent=2, default=str))


def _run_now(task_name: str, reason: str, force_backfill: bool) -> dict[str, Any]:
    """Execute the selected OHLCV task synchronously in the current process."""
    if task_name == 'daily_upsert':
        result = daily_ohlcv_upsert.apply(kwargs={'force_backfill': force_backfill})
    elif task_name == 'weekly_aggregate':
        result = daily_ohlcv_aggregate_week.apply()
    elif task_name == 'monthly_aggregate':
        result = daily_ohlcv_aggregate_month.apply()
    else:
        result = on_demand_ohlcv_upsert.apply(kwargs={'reason': reason, 'force_backfill': force_backfill})

    return {'task': task_name, 'execution': 'sync', 'state': result.state, 'result': result.result}


def _enqueue(task_name: str, reason: str, force_backfill: bool) -> dict[str, Any]:
    """Enqueue the selected OHLCV task to be processed by a Celery worker."""
    if task_name == 'daily_upsert':
        async_result = daily_ohlcv_upsert.delay(force_backfill=force_backfill)
    elif task_name == 'weekly_aggregate':
        async_result = daily_ohlcv_aggregate_week.delay()
    elif task_name == 'monthly_aggregate':
        async_result = daily_ohlcv_aggregate_month.delay()
    else:
        async_result = on_demand_ohlcv_upsert.delay(reason=reason, force_backfill=force_backfill)

    return {'task': task_name, 'execution': 'async', 'task_id': async_result.id, 'status': async_result.status}


def main() -> None:
    """Parse CLI arguments and run the requested OHLCV task."""
    parser = argparse.ArgumentParser(description='Run or enqueue OHLCV tasks.')
    parser.add_argument('--task', choices=['on_demand', 'daily_upsert', 'weekly_aggregate', 'monthly_aggregate'], default='on_demand', help='Which OHLCV task to trigger (default: on_demand).')
    parser.add_argument('--mode', choices=['sync', 'async'], default='sync', help='sync runs now in this process; async enqueues for Celery worker.')
    parser.add_argument('--reason', default='manual_terminal_trigger', help='Reason passed to on-demand OHLCV upsert task.')
    parser.add_argument('--force-backfill', action='store_true', help='Force 5-year backfill window for OHLCV upsert tasks.')
    args = parser.parse_args()

    payload = _enqueue(args.task, args.reason, args.force_backfill) if args.mode == 'async' else _run_now(args.task, args.reason, args.force_backfill)
    _print_json(payload)


if __name__ == '__main__':
    main()
