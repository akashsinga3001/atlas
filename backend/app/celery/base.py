# backend/app/celery/base.py

import time
from datetime import datetime
from enum import Enum as PythonEnum

from celery import Task

from app.core.config import settings
from app.integrations.discord.client import DiscordClient
from app.integrations.discord.service import DiscordNotificationService
from app.utils.logger import get_logger
from app.schemas.notification import NotificationPayload, NotificationMetric

logger = get_logger(__name__)


class NotificationPolicy(PythonEnum):
    ALWAYS = "always"
    NONE = "none"
    ON_FAILURE = "on_failure"
    ON_SUCCESS = "on_success"
    ON_SUCCESS_OR_FAILURE = "on_success_or_failure"
    ON_SUCCESS_AND_FAILURE = "on_success_and_failure"


_discord_service: DiscordNotificationService | None = None


def get_discord_service() -> DiscordNotificationService | None:
    global _discord_service

    if not settings.DISCORD_ENABLED:
        return None

    if not settings.DISCORD_WEBHOOK_URL:
        logger.warning("Discord webhook URL is not set. Discord notifications will be disabled.")
        return None

    if _discord_service is None:
        _discord_service = DiscordNotificationService(DiscordClient(settings.DISCORD_WEBHOOK_URL))

    return _discord_service


def _write_job_run(job_name: str | None, task_id: str, status: str, started_at: datetime | None = None, finished_at: datetime | None = None, duration_seconds: float | None = None, error_message: str | None = None) -> None:
    if not job_name:
        return
    try:
        from app.core.database import SessionLocal
        from app.models.job import JobRun
        db = SessionLocal()
        try:
            if status == "running":
                # Mark any previously stuck "running" rows for this job as stale
                stale = db.query(JobRun).filter(JobRun.job_name == job_name, JobRun.status == "running").all()
                for s in stale:
                    s.status = "stale"

                run = JobRun(job_name=job_name, task_id=task_id, status="running", started_at=started_at or datetime.now())
                db.add(run)
            else:
                run = db.query(JobRun).filter(JobRun.task_id == task_id).first()
                if run:
                    run.status = status
                    run.finished_at = finished_at
                    run.duration_seconds = duration_seconds
                    run.error_message = error_message
                else:
                    # on_success/on_failure fired but before_start row is missing — create it now
                    run = JobRun(job_name=job_name, task_id=task_id, status=status, started_at=finished_at, finished_at=finished_at, duration_seconds=duration_seconds, error_message=error_message)
                    db.add(run)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Failed to write JobRun for {job_name}: {e}")


class AtlasTask(Task):
    abstract = True
    display_name: str | None = None
    job_name: str | None = None

    def get_display_name(self, kwargs: dict) -> str:
        return self.display_name or self.name

    def get_notification_policy(self, args: tuple, kwargs: dict) -> NotificationPolicy:
        return NotificationPolicy.ON_SUCCESS_AND_FAILURE

    def before_start(self, task_id, args, kwargs):
        self.request.atlas_started_at = time.time()
        _write_job_run(job_name=self.job_name, task_id=task_id, status="running", started_at=datetime.now())

    def on_success(self, retval, task_id, args, kwargs):
        """Write success status to DB unconditionally, then send Discord notification if policy allows."""
        duration = self._get_duration()
        _write_job_run(job_name=self.job_name, task_id=task_id, status="success", finished_at=datetime.now(), duration_seconds=duration)

        policy = self.get_notification_policy(args, kwargs)
        if policy not in [NotificationPolicy.ALWAYS, NotificationPolicy.ON_SUCCESS, NotificationPolicy.ON_SUCCESS_OR_FAILURE, NotificationPolicy.ON_SUCCESS_AND_FAILURE]:
            return

        discord_service = get_discord_service()
        if not discord_service:
            logger.warning("Discord service is not available. Skipping success notification.")
            return

        payload = self.build_success_notification(duration_seconds=duration, result=retval, args=args, kwargs=kwargs)
        discord_service.send_notification(payload)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Write failure status to DB unconditionally, then send Discord notification if policy allows."""
        duration = self._get_duration()
        _write_job_run(job_name=self.job_name, task_id=task_id, status="failure", finished_at=datetime.now(), duration_seconds=duration, error_message=str(exc))

        policy = self.get_notification_policy(args, kwargs)
        if policy not in [NotificationPolicy.ALWAYS, NotificationPolicy.ON_FAILURE, NotificationPolicy.ON_SUCCESS_OR_FAILURE, NotificationPolicy.ON_SUCCESS_AND_FAILURE]:
            return

        discord_service = get_discord_service()
        if not discord_service:
            logger.warning("Discord service is not available. Skipping failure notification.")
            return

        payload = self.build_failure_notification(duration_seconds=duration, exception=exc, args=args, kwargs=kwargs)
        discord_service.send_notification(payload)

    def _get_duration(self) -> float:
        started_at = getattr(self.request, "atlas_started_at", time.time())
        return round(time.time() - started_at, 2)

    @staticmethod
    def _format_metric_label(key: str) -> str:
        return " ".join(word.capitalize() for word in key.split("_"))

    def _discover_metrics(self, data: dict) -> list[NotificationMetric]:
        metrics = []
        for key, value in data.items():
            if value is None:
                continue
            if isinstance(value, (list, tuple, set)):
                if not value:
                    continue
                value = len(value)
            elif isinstance(value, dict):
                if not value:
                    continue
                value = len(value)
            metrics.append(NotificationMetric(label=self._format_metric_label(key), value=str(value)))
        return metrics

    def build_success_notification(self, duration_seconds: float, result: dict, args, kwargs) -> NotificationPayload:
        data = (result or {}).get("data", {})
        return NotificationPayload(operation=self.get_display_name(kwargs), status="success", duration_seconds=duration_seconds, summary=(result or {}).get("message", "Operation completed successfully."), results=self._discover_metrics(data))

    def build_failure_notification(self, duration_seconds: float, exception: Exception, args, kwargs) -> NotificationPayload:
        return NotificationPayload(operation=self.get_display_name(kwargs), status="failed", duration_seconds=duration_seconds, summary=str(exception), action_required=["Review logs for additional details."])
