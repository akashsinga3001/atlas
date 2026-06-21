# backend/app/repositories/features.py

import time

from sqlalchemy import delete
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from app.models.features import SecurityFeature, SectorFeature, MarketFeature
from app.repositories.base import BaseRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _bulk_upsert(db: Session, model, constraint_name: str, records: list[dict]) -> int:
    """Perform a bulk upsert (insert or update) operation on the given model."""
    if not records:
        return 0

    try:
        stmt = insert(model).values(records)
        update_columns = {column.name: getattr(stmt.excluded, column.name) for column in model.__table__.columns if column.name not in [ 'id', 'created_at']}
        stmt = stmt.on_conflict_do_update(constraint=constraint_name, set_=update_columns)
        result = db.execute(stmt)
        return result.rowcount or len(records)
    except SQLAlchemyError as exc:
        logger.error(f"Error during bulk upsert for {model.__tablename__}: {exc}", exc_info=True)
        db.rollback()
        return 0


class SecurityFeatureRepository(BaseRepository):
    """Repository for managing SecurityFeature records."""

    def __init__(self, db: Session):
        self.db = db
        super().__init__(SecurityFeature, db)

    def bulk_upsert(self, records: list[dict]) -> int:
        """Perform a bulk upsert operation for SecurityFeature records."""
        return _bulk_upsert(self.db, SecurityFeature, "uix_security_feature_ohlcv", records)

    def replace_for_security(self, records: list[dict], batch_size: int = 1000) -> int:
        """Delete existing records for the given ohlcv_ids and insert new records."""
        if not records:
            return 0

        try:
            ohlcv_ids = [r["ohlcv_id"] for r in records]
            self.db.execute(delete(SecurityFeature).where(SecurityFeature.ohlcv_id.in_(ohlcv_ids)))

            total_inserted = 0
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                stmt = insert(SecurityFeature).values(batch)
                result = self.db.execute(stmt)
                total_inserted += (result.rowcount if result.rowcount is not None else len(batch))

            self.db.commit()
            return total_inserted
        except SQLAlchemyError as exc:
            logger.error(f"Error during replace for ohlcv_ids: {exc}", exc_info=True)
            self.db.rollback()
            return 0


class SectorFeatureRepository(BaseRepository):
    """Repository for managing SectorFeature records."""

    def __init__(self, db: Session):
        self.db = db
        super().__init__(SectorFeature, db)

    def bulk_upsert(self, records: list[dict]) -> int:
        """Perform a bulk upsert operation for SectorFeature records."""
        return _bulk_upsert(self.db, SectorFeature, "uix_sector_feature", records)


class MarketFeatureRepository(BaseRepository):
    """Repository for managing MarketFeature records."""

    def __init__(self, db: Session):
        self.db = db
        super().__init__(MarketFeature, db)

    def bulk_upsert(self, records: list[dict]) -> int:
        """Perform a bulk upsert operation for MarketFeature records."""
        return _bulk_upsert(self.db, MarketFeature, "uix_market_feature", records)
