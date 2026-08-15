# backend/app/repositories/schedule.py

from typing import Optional
from sqlalchemy.orm import Session

from app.models.schedule import ScheduleEntry
from app.repositories.base import BaseRepository


class ScheduleEntryRepository(BaseRepository[ScheduleEntry]):
    """Repository class for managing ScheduleEntry data in the database."""

    def __init__(self, db: Session):
        super().__init__(ScheduleEntry, db)

    def get_all_entries(self) -> list[ScheduleEntry]:
        """Fetch all schedule entries, grouped for display by group then name."""
        return self.db_session.query(ScheduleEntry).order_by(ScheduleEntry.group.asc(), ScheduleEntry.name.asc()).all()

    def get_by_name(self, name: str) -> Optional[ScheduleEntry]:
        """Fetch a schedule entry by its unique name."""
        return self.db_session.query(ScheduleEntry).filter(ScheduleEntry.name == name).first()

    def get_enabled_by_task(self) -> dict[str, list[ScheduleEntry]]:
        """Fetch all enabled entries grouped by task name, for building schedule-display strings."""
        entries = self.db_session.query(ScheduleEntry).filter(ScheduleEntry.enabled.is_(True)).all()
        result: dict[str, list[ScheduleEntry]] = {}
        for entry in entries:
            result.setdefault(entry.task, []).append(entry)
        return result
