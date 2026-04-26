"""Manual terminal runner for features Celery tasks."""

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

from jobs.features import daily_features_upsert, on_demand_features_upsert


def _positive_int(value: str) -> int:
    """Parse a positive integer for CLI arguments."""
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError('lookback-days must be >= 1')
    return parsed


def _print_json(payload: Any) -> None:
    """Print structured output in readable JSON format."""
    print(json.dumps(payload, indent=2, default=str))


def _run_now(task_name: str, reason: str, lookback_days: int) -> dict[str, Any]:
    """Execute the selected feature task synchronously in the current process."""
    if task_name == 'daily':
        result = daily_features_upsert.apply(kwargs={'lookback_days': lookback_days})
    else:
        result = on_demand_features_upsert.apply(kwargs={'reason': reason, 'lookback_days': lookback_days})

    return {'task': task_name, 'execution': 'sync', 'state': result.state, 'result': result.result}


def _enqueue(task_name: str, reason: str, lookback_days: int) -> dict[str, Any]:
    """Enqueue the selected feature task to be processed by a Celery worker."""
    if task_name == 'daily':
        async_result = daily_features_upsert.delay(lookback_days=lookback_days)
    else:
        async_result = on_demand_features_upsert.delay(reason=reason, lookback_days=lookback_days)

    return {'task': task_name, 'execution': 'async', 'task_id': async_result.id, 'status': async_result.status}


def main() -> None:
    """Parse CLI arguments and run the requested feature task."""
    parser = argparse.ArgumentParser(description='Run or enqueue feature upsert tasks.')
    parser.add_argument('--task', choices=['on_demand', 'daily'], default='on_demand', help='Which feature task to trigger (default: on_demand).')
    parser.add_argument('--mode', choices=['sync', 'async'], default='sync', help='sync runs now in this process; async enqueues for Celery worker.')
    parser.add_argument('--reason', default='manual_terminal_trigger', help='Reason passed to on-demand feature task.')
    parser.add_argument('--lookback-days', type=_positive_int, default=90, help='Lookback window for recalculating features (default: 90).')
    args = parser.parse_args()

    task_name = 'daily' if args.task == 'daily' else 'on_demand'
    payload = _enqueue(task_name, args.reason, args.lookback_days) if args.mode == 'async' else _run_now(task_name, args.reason, args.lookback_days)
    _print_json(payload)


if __name__ == '__main__':
    main()
