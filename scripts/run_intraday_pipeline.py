"""Manual runner for intraday inference and order execution pipeline."""

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

from jobs.intraday import ml_intraday_execution_pipeline


def _print_json(payload: Any) -> None:
    """Print payload as formatted JSON."""
    print(json.dumps(payload, indent=2, default=str))


def _run_sync(run_date: str | None, execute_orders: bool, send_email: bool) -> dict[str, Any]:
    """Execute intraday pipeline immediately in current process."""
    result = ml_intraday_execution_pipeline.apply(kwargs={'run_date': run_date, 'execute_orders': execute_orders, 'send_email': send_email})
    return {
        'execution': 'sync',
        'state': result.state,
        'result': result.result,
    }


def _run_async(run_date: str | None, execute_orders: bool, send_email: bool) -> dict[str, Any]:
    """Enqueue intraday pipeline to Celery workers."""
    result = ml_intraday_execution_pipeline.delay(run_date=run_date, execute_orders=execute_orders, send_email=send_email)
    return {
        'execution': 'async',
        'task_id': result.id,
        'status': result.status,
    }


def main() -> None:
    """Parse args and run intraday task in sync or async mode."""
    parser = argparse.ArgumentParser(description='Run intraday ML execution pipeline task.')
    parser.add_argument('--mode', choices=['sync', 'async'], default='sync', help='sync runs now, async enqueues to Celery')
    parser.add_argument('--run-date', default=None, help='Optional run date in YYYY-MM-DD format')
    parser.add_argument('--no-orders', action='store_true', help='Skip order execution and only run inference/report path')
    parser.add_argument('--no-email', action='store_true', help='Skip report email send')
    args = parser.parse_args()

    payload = (
        _run_async(args.run_date, execute_orders=not args.no_orders, send_email=not args.no_email)
        if args.mode == 'async'
        else _run_sync(args.run_date, execute_orders=not args.no_orders, send_email=not args.no_email)
    )
    _print_json(payload)


if __name__ == '__main__':
    main()
