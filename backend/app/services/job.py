# backend/app/services/job.py

from celery.schedules import crontab
from sqlalchemy.orm import Session

from app.schemas.base import APIResponse
from app.schemas.job import JobTriggerRequest
from app.models.job import JobRun
from app.core.celery_schedule import beat_schedule
import app.jobs  # noqa: F401 — ensures all register() calls run
from app.jobs import registry

from app.utils.logger import get_logger

logger = get_logger(__name__)


def _crontab_to_display(c: crontab) -> str:
    minute = str(c._orig_minute)
    hour = str(c._orig_hour)
    dow = str(c._orig_day_of_week)
    dom = str(c._orig_day_of_month)

    if "/" in minute:
        interval = minute.split("/")[-1]
        return f"Live every {interval}m"

    h = int(hour) if hour.isdigit() else 0
    m = int(minute) if minute.isdigit() else 0
    time_str = f"{h:02d}:{m:02d}"

    if dom != "*":
        return f"Monthly {time_str}"
    if dow == "1-5":
        return f"Weekdays {time_str}"
    return f"Daily {time_str}"


def _build_schedule_map() -> dict[str, str]:
    task_parts: dict[str, list[str]] = {}
    for entry in beat_schedule.values():
        display = _crontab_to_display(entry["schedule"])
        task_parts.setdefault(entry["task"], []).append(display)

    result = {}
    for task_name, parts in task_parts.items():
        non_live = list(dict.fromkeys(p for p in parts if not p.startswith("Live")))
        live = list(dict.fromkeys(p for p in parts if p.startswith("Live")))
        result[task_name] = " + ".join(non_live + live)
    return result


_SCHEDULE_MAP = _build_schedule_map()


class JobService:

    def _get_last_runs(self, db: Session) -> dict[str, dict]:
        subq = (db.query(JobRun.job_name, JobRun.started_at, JobRun.status, JobRun.duration_seconds, JobRun.error_message).distinct(JobRun.job_name).order_by(JobRun.job_name, JobRun.started_at.desc()).subquery())
        return {row.job_name: { "last_run_at": row.started_at.isoformat() if row.started_at else None, "last_run_status": row.status, "last_run_duration": row.duration_seconds, "last_run_error": row.error_message } for row in db.query(subq).all()}

    def get_jobs(self, db: Session) -> list[dict]:
        last_runs = self._get_last_runs(db)
        return [{ "name": defn.name, "display_name": defn.display_name, "description": defn.description, "group": defn.group, "schedule": _SCHEDULE_MAP.get(defn.task.name, "On-demand"), **last_runs.get(defn.name, {}), } for defn in registry.all_jobs()]

    def execute_job(self, request: JobTriggerRequest, db=None) -> APIResponse:
        logger.info(f"Executing job: {request.job_name}")
        defn = registry.get(request.job_name)
        if not defn:
            raise ValueError(f"Unknown job: {request.job_name}")

        if defn.parameters_schema:
            params = defn.parameters_schema.model_validate(request.parameters or {}).model_dump(exclude_none=True)
        else:
            params = request.parameters or {}

        defn.task.apply_async(kwargs=params)
