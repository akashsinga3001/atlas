# backend/app/seeders/schedule_seeder.py

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.schedule import ScheduleEntry
from app.utils.logger import get_logger

logger = get_logger(__name__)

SCHEDULE_ENTRIES = [{
    "name": "trade-entry-15:15-retry",
    "task": "app.jobs.trade_entry.run_trade_entry",
    "minute": "15",
    "hour": "15",
    "day_of_week": "1-5",
    "day_of_month": "*",
    "month_of_year": "*",
    "kwargs": {"strategy_ids": [3]},
    "enabled": True,
    "description": "Same-day re-entry retry after the 15:10 exit tick. A position closing exactly on its planned_exit_date frees the slot too late for the 09:20-14:50 entry window, letting that week's signal expire unconsumed.",
    "group": "trading",
}]


def seed_schedule_entry(db: Session, *, name: str, **fields) -> None:
    entry = db.query(ScheduleEntry).filter(ScheduleEntry.name == name).first()

    if entry is None:
        db.add(ScheduleEntry(name=name, **fields))
        db.commit()


def seed() -> None:
    """Seed schedule entries into the database.

    Only inserts into Postgres — Celery beat reads from RedBeat's Redis-backed schedule,
    which this does not touch. After running this against a fresh database, call
    POST /schedule/resync once to push every entry into Redis.
    """
    db = SessionLocal()
    try:
        for entry in SCHEDULE_ENTRIES:
            seed_schedule_entry(db, **entry)
        logger.info("Seeded schedule entries into the database.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
