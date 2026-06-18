# backend/app/integrations/discord/templates.py

from datetime import datetime
from typing import Any


def _timestamp() -> str:
    """Returns the current timestamp in ISO 8601 format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def build_job_started_message(job_name: str) -> str:
    """Builds a message for when a job starts."""
    return (f"🔄 {job_name}\n\n"
            f"Status: Started\n"
            f"Time: {_timestamp()}")


def build_job_success_message(job_name: str, duration_seconds: float, details: dict[str, Any]) -> str:
    """Builds a message for when a job succeeds."""
    lines = [ f"✅ {job_name}", "", "Status: Completed", f"Duration: {duration_seconds:.2f}s", f"Time: {_timestamp()}", ]

    if details:
        lines.append("")
        lines.append("Details:")

        for key, value in details.items():
            lines.append(f"- {key}: {value}")

    return "\n".join(lines)


def build_job_failure_message(job_name: str, error: str) -> str:
    return (f"❌ {job_name}\n\n"
            f"Status: Failed\n"
            f"Error: {error}\n"
            f"Time: {_timestamp()}")


def build_error_message(component: str, error: str) -> str:
    return (f"🚨 Atlas Error\n\n"
            f"Component: {component}\n"
            f"Error: {error}\n"
            f"Time: {_timestamp()}")
