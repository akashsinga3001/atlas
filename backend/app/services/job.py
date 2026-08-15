# backend/app/services/job.py

import uuid
from datetime import datetime

from celery.schedules import crontab
from sqlalchemy.orm import Session

from app.schemas.base import APIResponse
from app.schemas.job import JobTriggerRequest
from app.models.job import JobRun
from app.repositories.schedule import ScheduleEntryRepository
from app.services.schedule_redis_sync import entry_to_crontab
from app.utils.pydantic_forms import schema_to_fields
import app.jobs  # noqa: F401 — ensures all register() calls run
from app.jobs import registry

from app.utils.logger import get_logger

logger = get_logger(__name__)


class JobService:

    # ------------------------------------------------------------------ #
    #  Schedule helpers                                                   #
    # ------------------------------------------------------------------ #

    def _crontab_to_display(self, c: crontab) -> str:
        """Convert a crontab expression to a human-readable schedule string."""
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

    def _build_schedule_map(self, db: Session) -> dict[str, str]:
        """Build a mapping of task name → display schedule string from enabled ScheduleEntry rows."""
        task_parts: dict[str, list[str]] = {}
        for task_name, entries in ScheduleEntryRepository(db).get_enabled_by_task().items():
            for entry in entries:
                display = self._crontab_to_display(entry_to_crontab(entry))
                task_parts.setdefault(task_name, []).append(display)

        result = {}
        for task_name, parts in task_parts.items():
            non_live = list(dict.fromkeys(p for p in parts if not p.startswith("Live")))
            live = list(dict.fromkeys(p for p in parts if p.startswith("Live")))
            result[task_name] = " + ".join(non_live + live)
        return result

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    def get_jobs(self, db: Session) -> list[dict]:
        """Return all registered job definitions merged with their latest run info."""
        schedule_map = self._build_schedule_map(db)
        last_runs = self._get_last_runs(db)
        return [{ "name": defn.name, "display_name": defn.display_name, "description": defn.description, "group": defn.group, "schedule": schedule_map.get(defn.task.name, "On-demand"), "parameter_fields": schema_to_fields(defn.parameters_schema) if defn.parameters_schema else [], **last_runs.get(defn.name, {}), } for defn in registry.all_jobs()]

    def _get_last_runs(self, db: Session) -> dict[str, dict]:
        """Query the most recent job_run row per job_name and return as a lookup dict."""
        subq = (db.query(JobRun.job_name, JobRun.started_at, JobRun.status, JobRun.duration_seconds, JobRun.error_message).distinct(JobRun.job_name).order_by(JobRun.job_name, JobRun.started_at.desc()).subquery())
        return {row.job_name: { "last_run_at": row.started_at.isoformat() if row.started_at else None, "last_run_status": row.status, "last_run_duration": row.duration_seconds, "last_run_error": row.error_message, } for row in db.query(subq).all()}

    def execute_job(self, request: JobTriggerRequest, db: Session) -> None:
        """Validate the job name, dispatch it to Celery, and write a queued row immediately."""
        logger.info(f"Executing job: {request.job_name}")
        defn = registry.get(request.job_name)
        if not defn:
            raise ValueError(f"Unknown job: {request.job_name}")

        if defn.parameters_schema:
            params = defn.parameters_schema.model_validate(request.parameters or {}).model_dump(exclude_none=True)
        else:
            params = request.parameters or {}

        task_id = str(uuid.uuid4())
        self._write_queued(job_name=request.job_name, task_id=task_id, db=db)
        defn.task.apply_async(kwargs=params, task_id=task_id)

    def _write_queued(self, job_name: str, task_id: str, db: Session) -> None:
        """Insert a queued JobRun row before dispatching so before_start always finds it."""
        run = JobRun(job_name=job_name, task_id=task_id, status="queued", started_at=datetime.now())
        db.add(run)
        db.commit()
