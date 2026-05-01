"""Manual runner for ML training and daily signal report pipeline."""

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

from jobs.ml import daily_ml_signal_report, on_demand_ml_signal_report, weekly_ml_train


def _print_json(payload: Any) -> None:
    """Print structured payload as readable JSON."""
    print(json.dumps(payload, indent=2, default=str))


def _run_sync(task: str, send_email: bool, reason: str) -> dict[str, Any]:
    """Execute selected ML task in current process."""
    if task == 'train':
        result = weekly_ml_train.apply(kwargs={})
        return {'task': task, 'execution': 'sync', 'state': result.state, 'result': result.result}

    if task == 'report':
        result = on_demand_ml_signal_report.apply(kwargs={'reason': reason, 'send_email': send_email})
        return {'task': task, 'execution': 'sync', 'state': result.state, 'result': result.result}

    train_result = weekly_ml_train.apply(kwargs={})
    report_result = on_demand_ml_signal_report.apply(kwargs={'reason': reason, 'send_email': send_email})
    return {
        'task': task,
        'execution': 'sync',
        'train': {'state': train_result.state, 'result': train_result.result},
        'report': {'state': report_result.state, 'result': report_result.result},
    }


def _run_async(task: str, send_email: bool, reason: str) -> dict[str, Any]:
    """Enqueue selected ML task to Celery workers."""
    if task == 'train':
        async_result = weekly_ml_train.delay()
        return {'task': task, 'execution': 'async', 'task_id': async_result.id, 'status': async_result.status}

    if task == 'report':
        async_result = daily_ml_signal_report.delay(send_email=send_email)
        return {'task': task, 'execution': 'async', 'task_id': async_result.id, 'status': async_result.status}

    return {
        'task': task,
        'execution': 'async',
        'error': 'full async is not supported, use --mode sync for full pipeline',
    }


def main() -> None:
    """Parse CLI args and run/enqueue ML pipeline tasks."""
    parser = argparse.ArgumentParser(description='Run ML training and daily signal report tasks.')
    parser.add_argument('--task', choices=['train', 'report', 'full'], default='report', help='Task to run (default: report).')
    parser.add_argument('--mode', choices=['sync', 'async'], default='sync', help='sync runs now, async enqueues to Celery.')
    parser.add_argument('--reason', default='manual_terminal_trigger', help='Reason for on-demand report run.')
    parser.add_argument('--no-email', action='store_true', help='Generate report but skip SMTP send.')
    args = parser.parse_args()

    send_email = not args.no_email
    payload = _run_async(args.task, send_email, args.reason) if args.mode == 'async' else _run_sync(args.task, send_email, args.reason)
    _print_json(payload)


if __name__ == '__main__':
    main()
