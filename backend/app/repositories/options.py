# backend/app/repositories/options.py

from typing import Optional
from sqlalchemy.orm import Session

from app.enums.options import OptionsPositionStatus
from app.models.options import OptionsPosition, OptionsLeg
from app.repositories.base import BaseRepository


class OptionsPositionRepository(BaseRepository[OptionsPosition]):
    """Repository class for managing OptionsPosition data in the database."""

    def __init__(self, db: Session):
        super().__init__(OptionsPosition, db)

    def get_active_for_strategy_version(self, strategy_version_id: int) -> Optional[OptionsPosition]:
        """Fetch the single non-terminal (PENDING/OPEN/CLOSING) position for a strategy version, if any."""
        return (
            self.db_session.query(OptionsPosition)
            .filter(
                OptionsPosition.strategy_version_id == strategy_version_id,
                OptionsPosition.status.in_([OptionsPositionStatus.PENDING, OptionsPositionStatus.OPEN, OptionsPositionStatus.CLOSING]),
            )
            .first()
        )

    def get_open_for_strategy_version(self, strategy_version_id: int) -> list[OptionsPosition]:
        """Fetch all OPEN positions for a strategy version (exit evaluation reads from this)."""
        return (
            self.db_session.query(OptionsPosition)
            .filter(OptionsPosition.strategy_version_id == strategy_version_id, OptionsPosition.status == OptionsPositionStatus.OPEN)
            .all()
        )

    def get_open_and_closing_for_strategy_version(self, strategy_version_id: int) -> list[OptionsPosition]:
        """Fetch OPEN + CLOSING positions — exit evaluation must retry CLOSING (partially-exited) positions too."""
        return (
            self.db_session.query(OptionsPosition)
            .filter(
                OptionsPosition.strategy_version_id == strategy_version_id,
                OptionsPosition.status.in_([OptionsPositionStatus.OPEN, OptionsPositionStatus.CLOSING]),
            )
            .all()
        )

    def get_by_signal_id(self, strategy_signal_id: int) -> Optional[OptionsPosition]:
        """Fetch the position (if any) already created from a given strategy signal."""
        return self.db_session.query(OptionsPosition).filter(OptionsPosition.strategy_signal_id == strategy_signal_id).first()

    def get_all_for_strategy_version(self, strategy_version_id: int) -> list[OptionsPosition]:
        """Fetch all positions for a strategy version, most recent first."""
        return (
            self.db_session.query(OptionsPosition)
            .filter(OptionsPosition.strategy_version_id == strategy_version_id)
            .order_by(OptionsPosition.entry_date.desc())
            .all()
        )

    def get_all_positions(self, status: Optional[OptionsPositionStatus] = None) -> list[OptionsPosition]:
        """Fetch all positions across every strategy version, optionally filtered by status, most recent first."""
        query = self.db_session.query(OptionsPosition)
        if status:
            query = query.filter(OptionsPosition.status == status)
        return query.order_by(OptionsPosition.entry_date.desc()).all()


class OptionsLegRepository(BaseRepository[OptionsLeg]):
    """Repository class for managing OptionsLeg data in the database."""

    def __init__(self, db: Session):
        super().__init__(OptionsLeg, db)

    def get_for_position(self, options_position_id: int) -> list[OptionsLeg]:
        """Fetch all legs belonging to a position."""
        return self.db_session.query(OptionsLeg).filter(OptionsLeg.options_position_id == options_position_id).all()
