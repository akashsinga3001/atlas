"""Manual terminal runner for securities upsert Celery tasks."""

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

from jobs.securities import kite_daily_securities_upsert, kite_on_demand_securities_upsert


def _print_json(payload: Any) -> None:
    """Print structured output in readable JSON format."""
    print(json.dumps(payload, indent=2, default=str))


def _run_now(task_name: str, reason: str) -> dict[str, Any]:
    """Execute the selected task synchronously in the current process."""
    if task_name == 'daily':
        result = kite_daily_securities_upsert.apply()
    else:
        result = kite_on_demand_securities_upsert.apply(kwargs={'reason': reason})

    return {'task': task_name, 'execution': 'sync', 'state': result.state, 'result': result.result}


def _enqueue(task_name: str, reason: str) -> dict[str, Any]:
    """Enqueue the selected task to be processed by a Celery worker."""
    if task_name == 'daily':
        async_result = kite_daily_securities_upsert.delay()
    else:
        async_result = kite_on_demand_securities_upsert.delay(reason=reason)

    return {'task': task_name, 'execution': 'async', 'task_id': async_result.id, 'status': async_result.status}


def main() -> None:
    """Parse CLI arguments and run the requested securities upsert task."""
    parser = argparse.ArgumentParser(description='Run or enqueue securities upsert tasks.')
    parser.add_argument('--task', choices=['on_demand', 'daily'], default='on_demand', help='Which upsert task to trigger (default: on_demand).')
    parser.add_argument('--mode', choices=['sync', 'async'], default='sync', help='sync runs now in this process; async enqueues for Celery worker.')
    parser.add_argument('--reason', default='manual_terminal_trigger', help='Reason passed to on-demand upsert task.')
    args = parser.parse_args()

    task_name = 'daily' if args.task == 'daily' else 'on_demand'
    payload = _enqueue(task_name, args.reason) if args.mode == 'async' else _run_now(task_name, args.reason)
    _print_json(payload)


if __name__ == '__main__':
    main()
