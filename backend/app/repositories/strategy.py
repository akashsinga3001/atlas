# backend/app/repositories/strategy.py

from typing import Optional
from sqlalchemy.orm import Session, joinedload

from app.models.strategy import Strategy, StrategyRun, StrategyVersion
from app.repositories.base import BaseRepository


class StrategyRepository(BaseRepository[Strategy]):
    """Repository class for managing Strategy data in the database."""

    def __init__(self, db: Session):
        super().__init__(Strategy, db)

    def get_by_code(self, code: str) -> Optional[Strategy]:
        """Fetch a strategy by its unique code."""
        return self.db_session.query(Strategy).filter(Strategy.code == code).first()

    def get_all_with_versions(self) -> list[Strategy]:
        """Fetch all strategies ordered by name, for the list view."""
        return self.db_session.query(Strategy).order_by(Strategy.name.asc()).all()

    def lock_for_update(self, strategy_id: int) -> Optional[Strategy]:
        """Row-lock a strategy for the duration of the transaction, serializing concurrent version activations."""
        return self.db_session.query(Strategy).filter(Strategy.id == strategy_id).with_for_update().first()


class StrategyVersionRepository(BaseRepository[StrategyVersion]):
    """Repository class for managing StrategyVersion data in the database."""

    def __init__(self, db: Session):
        super().__init__(StrategyVersion, db)

    def get_all_for_strategy(self, strategy_id: int) -> list[StrategyVersion]:
        """Fetch all versions for a strategy, newest version first."""
        return self.db_session.query(StrategyVersion).filter(StrategyVersion.strategy_id == strategy_id).order_by(StrategyVersion.version.desc()).all()

    def get_active_for_strategy(self, strategy_id: int) -> Optional[StrategyVersion]:
        """Fetch the currently active version for a strategy, if any."""
        return self.db_session.query(StrategyVersion).filter(StrategyVersion.strategy_id == strategy_id, StrategyVersion.is_active.is_(True)).first()

    def get_max_version(self, strategy_id: int) -> int:
        """Return the highest existing version number for a strategy, or 0 if none exist."""
        result = self.db_session.query(StrategyVersion.version).filter(StrategyVersion.strategy_id == strategy_id).order_by(StrategyVersion.version.desc()).first()
        return result[0] if result else 0

    def deactivate_all_except(self, strategy_id: int, version_id: int) -> None:
        """Bulk-deactivate every version of a strategy other than the given one."""
        self.db_session.query(StrategyVersion).filter(StrategyVersion.strategy_id == strategy_id, StrategyVersion.id != version_id).update({ "is_active": False }, synchronize_session=False)

    def get_recent_runs_for_strategy(self, strategy_id: int, limit: int = 20) -> list[StrategyRun]:
        """Fetch the most recent strategy runs across every version of a strategy, newest first."""
        return (
            self.db_session.query(StrategyRun)
            .join(StrategyVersion, StrategyRun.strategy_version_id == StrategyVersion.id)
            .options(joinedload(StrategyRun.strategy_version))
            .filter(StrategyVersion.strategy_id == strategy_id)
            .order_by(StrategyRun.id.desc())
            .limit(limit)
            .all()
        )

    def get_last_run_for_strategy(self, strategy_id: int) -> Optional[StrategyRun]:
        """Fetch the single most recent strategy run across every version of a strategy."""
        return (
            self.db_session.query(StrategyRun)
            .join(StrategyVersion, StrategyRun.strategy_version_id == StrategyVersion.id)
            .filter(StrategyVersion.strategy_id == strategy_id)
            .order_by(StrategyRun.id.desc())
            .first()
        )
