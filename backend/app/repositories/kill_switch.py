# backend/app/repositories/kill_switch.py

from sqlalchemy.orm import Session

from app.models.kill_switch import KillSwitch
from app.repositories.base import BaseRepository


class KillSwitchRepository(BaseRepository[KillSwitch]):
    """Repository class for managing the singleton KillSwitch row."""

    def __init__(self, db: Session):
        super().__init__(KillSwitch, db)

    def get_singleton(self) -> KillSwitch:
        """Fetch the single canonical kill-switch row (id=1, seeded by migration)."""
        return self.db_session.query(KillSwitch).filter(KillSwitch.id == 1).one()
