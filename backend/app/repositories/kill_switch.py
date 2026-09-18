# backend/app/repositories/kill_switch.py

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import DatabaseError
from app.models.kill_switch import KillSwitch
from app.repositories.base import BaseRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class KillSwitchRepository(BaseRepository[KillSwitch]):
    """Repository class for managing the singleton KillSwitch row."""

    def __init__(self, db: Session):
        super().__init__(KillSwitch, db)

    def get_singleton(self) -> KillSwitch:
        """Fetch the single canonical kill-switch row (id=1, seeded by migration).

        Wraps SQLAlchemy's raw NoResultFound/MultipleResultsFound into the same DatabaseError
        every other repository method raises — this is called uncaught from run_entry() and the
        capital-allocation check, so an unwrapped SQLAlchemy exception here would crash trade
        entry with an exception type nothing else in the app expects.
        """
        try:
            return self.db_session.query(KillSwitch).filter(KillSwitch.id == 1).one()
        except SQLAlchemyError as exc:
            logger.exception("Database error fetching the kill switch singleton row.")
            raise DatabaseError(operation="get_kill_switch_singleton", message="Failed to retrieve kill switch state") from exc
