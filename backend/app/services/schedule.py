# backend/app/services/schedule.py

from sqlalchemy.orm import Session

from app.models.schedule import ScheduleEntry
from app.repositories.schedule import ScheduleEntryRepository
from app.schemas.schedule import ScheduleEntryResponse, CreateScheduleEntryRequest, UpdateScheduleEntryRequest
from app.services.schedule_redis_sync import push_to_redis, delete_from_redis
from app.core.exceptions import NotFoundError, ValidationError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ScheduleService:
    """Service for managing DB-backed Celery schedule entries, kept in sync with RedBeat's Redis-backed schedule."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ScheduleEntryRepository(db)

    def list_entries(self) -> list[dict]:
        """Return all schedule entries, grouped for the UI by group then name."""
        return [self._build_response(e) for e in self.repo.get_all_entries()]

    def _build_response(self, entry: ScheduleEntry) -> dict:
        """Serialise a schedule entry to a dict."""
        return ScheduleEntryResponse(
            id=entry.id, name=entry.name, task=entry.task, minute=entry.minute, hour=entry.hour, day_of_week=entry.day_of_week, day_of_month=entry.day_of_month, month_of_year=entry.month_of_year,
            kwargs=entry.kwargs or {}, enabled=entry.enabled, description=entry.description, group=entry.group, created_at=entry.created_at, updated_at=entry.updated_at,
        ).model_dump()

    def create_entry(self, data: CreateScheduleEntryRequest) -> dict:
        """Insert a new schedule entry and push it into RedBeat's Redis-backed schedule."""
        if self.repo.get_by_name(data.name):
            raise ValidationError(message=f"A schedule entry named '{data.name}' already exists")

        entry = self.repo.create(ScheduleEntry(**data.model_dump()))
        self._sync_to_redis(entry)
        return self._build_response(entry)

    def update_entry(self, entry_id: int, data: UpdateScheduleEntryRequest) -> dict:
        """Update a schedule entry's cron fields/kwargs/metadata and re-sync it to RedBeat."""
        entry = self.repo.get_by_id(entry_id)
        if not entry:
            raise NotFoundError(resource="ScheduleEntry", identifier=str(entry_id))

        updates = data.model_dump(exclude_none=True)
        entry = self.repo.update(entry, updates)
        self._sync_to_redis(entry)
        return self._build_response(entry)

    def toggle_enabled(self, entry_id: int, enabled: bool) -> dict:
        """Enable or disable a schedule entry and re-sync it to RedBeat — takes effect within one beat tick."""
        entry = self.repo.get_by_id(entry_id)
        if not entry:
            raise NotFoundError(resource="ScheduleEntry", identifier=str(entry_id))

        entry = self.repo.update(entry, { "enabled": enabled })
        self._sync_to_redis(entry)
        return self._build_response(entry)

    def delete_entry(self, entry_id: int) -> None:
        """Delete a schedule entry from both Postgres and RedBeat's Redis-backed schedule."""
        entry = self.repo.get_by_id(entry_id)
        if not entry:
            raise NotFoundError(resource="ScheduleEntry", identifier=str(entry_id))

        try:
            delete_from_redis(entry.name)
        except Exception:
            logger.error(f"Failed to remove schedule entry '{entry.name}' from Redis before deleting from Postgres.", exc_info=True)
        self.repo.delete(entry)

    def resync_all(self) -> dict:
        """Push every Postgres schedule entry into RedBeat — disaster recovery if Redis is ever flushed."""
        entries = self.repo.get_all_entries()
        synced, failed = 0, []
        for entry in entries:
            try:
                push_to_redis(entry)
                synced += 1
            except Exception:
                logger.error(f"Failed to resync schedule entry '{entry.name}' to Redis.", exc_info=True)
                failed.append(entry.name)
        return { "synced": synced, "failed": failed, "total": len(entries) }

    def _sync_to_redis(self, entry: ScheduleEntry) -> None:
        """Push a single entry to Redis, logging (not raising) on failure — Postgres stays the source of truth."""
        try:
            push_to_redis(entry)
        except Exception:
            logger.error(f"Failed to sync schedule entry '{entry.name}' to Redis — Postgres was updated but Redis may be stale until the next resync.", exc_info=True)
