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

    def _build_schedule_map(self) -> dict[str, str]:
        """Build a mapping of task name → display schedule string from the beat schedule."""
        task_parts: dict[str, list[str]] = {}
        for entry in beat_schedule.values():
            display = self._crontab_to_display(entry["schedule"])
            task_parts.setdefault(entry["task"], []).append(display)

        result = {}
        for task_name, parts in task_parts.items():
            non_live = list(dict.fromkeys(p for p in parts if not p.startswith("Live")))
            live = list(dict.fromkeys(p for p in parts if p.startswith("Live")))
            result[task_name] = " + ".join(non_live + live)
        return result

    # ------------------------------------------------------------------ #
    #  Parameter schema helpers                                           #
    # ------------------------------------------------------------------ #

    def _schema_to_fields(self, schema_cls: type) -> list[dict]:
        """Flatten a Pydantic model's JSON schema into a UI-friendly field list."""
        js = schema_cls.model_json_schema()
        properties = js.get("properties", {})
        required = set(js.get("required", []))

        fields = []
        for name, prop in properties.items():
            prop = self._unwrap_optional(prop)
            field_type, options = self._resolve_field_type(prop)
            entry = { "name": name, "type": field_type, "required": name in required, "default": prop.get("default"), "description": prop.get("description", ""), }
            if options is not None:
                entry["options"] = options
            fields.append(entry)
        return fields

    def _unwrap_optional(self, prop: dict) -> dict:
        """Strip the null branch from anyOf so Optional[T] resolves to T's schema."""
        if "anyOf" in prop:
            non_null = [ t for t in prop["anyOf"] if t.get("type") != "null"]
            return { **prop, **non_null[0] } if non_null else prop
        return prop

    def _resolve_field_type(self, prop: dict) -> tuple[str, list | None]:
        """Map a JSON schema property to an Atlas field type and optional enum values."""
        if "enum" in prop:
            return "enum", prop["enum"]
        if prop.get("type") == "array":
            return "array", None
        if prop.get("type") == "integer":
            return "integer", None
        return "string", None

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    def get_jobs(self, db: Session) -> list[dict]:
        """Return all registered job definitions merged with their latest run info."""
        schedule_map = self._build_schedule_map()
        last_runs = self._get_last_runs(db)
        return [{ "name": defn.name, "display_name": defn.display_name, "description": defn.description, "group": defn.group, "schedule": schedule_map.get(defn.task.name, "On-demand"), "parameter_fields": self._schema_to_fields(defn.parameters_schema) if defn.parameters_schema else [], **last_runs.get(defn.name, {}), } for defn in registry.all_jobs()]

    def _get_last_runs(self, db: Session) -> dict[str, dict]:
        """Query the most recent job_run row per job_name and return as a lookup dict."""
        subq = (db.query(JobRun.job_name, JobRun.started_at, JobRun.status, JobRun.duration_seconds, JobRun.error_message).distinct(JobRun.job_name).order_by(JobRun.job_name, JobRun.started_at.desc()).subquery())
        return {row.job_name: { "last_run_at": row.started_at.isoformat() if row.started_at else None, "last_run_status": row.status, "last_run_duration": row.duration_seconds, "last_run_error": row.error_message, } for row in db.query(subq).all()}

    def execute_job(self, request: JobTriggerRequest, db=None) -> APIResponse:
        """Validate the job name, resolve parameters, and dispatch it to Celery."""
        logger.info(f"Executing job: {request.job_name}")
        defn = registry.get(request.job_name)
        if not defn:
            raise ValueError(f"Unknown job: {request.job_name}")

        if defn.parameters_schema:
            params = defn.parameters_schema.model_validate(request.parameters or {}).model_dump(exclude_none=True)
        else:
            params = request.parameters or {}

        defn.task.apply_async(kwargs=params)
