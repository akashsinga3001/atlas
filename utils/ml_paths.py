"""Utilities for ML artifact paths and directory creation."""

from datetime import date
from pathlib import Path


def ensure_directory(path: str | Path) -> Path:
    """Create directory recursively and return normalized Path."""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def weekly_run_directory(base_dir: str | Path, run_date: date) -> Path:
    """Return/create directory for one weekly training run."""
    return ensure_directory(Path(base_dir) / run_date.isoformat())
