# backend/app/services/schedule_redis_sync.py

from celery.schedules import crontab
from redbeat import RedBeatSchedulerEntry

from app.celery_app import celery_app
from app.models.schedule import ScheduleEntry
from app.utils.logger import get_logger

logger = get_logger(__name__)


def entry_to_crontab(entry: ScheduleEntry) -> crontab:
    """Build a celery crontab schedule from a ScheduleEntry's cron fields."""
    return crontab(minute=entry.minute, hour=entry.hour, day_of_week=entry.day_of_week, day_of_month=entry.day_of_month, month_of_year=entry.month_of_year)


def push_to_redis(entry: ScheduleEntry) -> None:
    """Write (or overwrite) a ScheduleEntry into RedBeat's Redis-backed schedule — live within one beat tick."""
    redbeat_entry = RedBeatSchedulerEntry(name=entry.name, task=entry.task, schedule=entry_to_crontab(entry), kwargs=entry.kwargs or {}, enabled=entry.enabled, app=celery_app)
    redbeat_entry.save()
    logger.info(f"Synced schedule entry '{entry.name}' to Redis (enabled={entry.enabled}).")


def delete_from_redis(name: str) -> None:
    """Remove a schedule entry from RedBeat's Redis-backed schedule by name."""
    RedBeatSchedulerEntry(name=name, app=celery_app).delete()
    logger.info(f"Removed schedule entry '{name}' from Redis.")
