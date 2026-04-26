"""OHLCV ingestion and aggregation service."""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from time import sleep
from typing import Any

from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker

from config import settings
from models.ohlcv import Ohlcv
from models.security import Security
from services.brokers.kite import KiteService
from utils.logger import logger


class OhlcvService:
    """Service class for OHLCV upsert and timeframe aggregation."""

    TIMEFRAME_1DAY = '1DAY'
    TIMEFRAME_1WEEK = '1WEEK'
    TIMEFRAME_1MONTH = '1MONTH'

    MAX_BACKFILL_DAYS = 5 * 365
    OVERLAP_DAYS = 7
    AGGREGATION_RECOMPUTE_DAYS = 90
    FETCH_THROTTLE_SECONDS = 0.20

    def __init__(self) -> None:
        self.kite_service = KiteService()
        self._engine = create_engine(settings.DATABASE_URL, echo=settings.DB_ECHO, future=True)
        self._session_factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, future=True)

    def upsert_daily_ohlcv(self, force_backfill: bool = False) -> dict[str, Any]:
        """Ingest 1DAY OHLCV for all active EQ and NFO-FUT instruments."""
        securities = self._get_active_eq_and_nfo_fut_securities()
        if not securities:
            return {'success': True, 'processed': 0, 'inserted_or_updated': 0, 'timeframe': self.TIMEFRAME_1DAY}

        today = date.today()
        default_from_date = today - timedelta(days=self.MAX_BACKFILL_DAYS)
        total_upserted = 0
        processed = 0
        errors: list[str] = []
        invalid_candles_skipped = 0
        duplicate_candles_deduplicated = 0

        for security in securities:
            try:
                last_candle_date = None if force_backfill else self._get_last_candle_date(security.id, self.TIMEFRAME_1DAY)
                from_date = default_from_date
                if last_candle_date is not None:
                    from_date = max(default_from_date, last_candle_date - timedelta(days=self.OVERLAP_DAYS))

                is_future = security.type == 'FUT' and security.exchange == 'NFO'
                candles = self.kite_service.fetch_historical_candles(instrument_token=security.broker_token, from_date=from_date, to_date=today, interval='day', continuous=is_future)

                rows, skipped_count, deduplicated_count = self._build_daily_rows(security.id, candles, is_future)
                invalid_candles_skipped += skipped_count
                duplicate_candles_deduplicated += deduplicated_count

                if rows:
                    total_upserted += self._upsert_ohlcv_rows(rows)

                processed += 1
                sleep(self.FETCH_THROTTLE_SECONDS)
            except Exception as exc:
                logger.error('Failed OHLCV ingestion for {}: {}', security.ticker, exc)
                errors.append(f'{security.ticker}: {exc}')

        return {
            'success': len(errors) == 0,
            'processed': processed,
            'inserted_or_updated': total_upserted,
            'timeframe': self.TIMEFRAME_1DAY,
            'errors_count': len(errors),
            'errors': errors,
            'invalid_candles_skipped': invalid_candles_skipped,
            'duplicate_candles_deduplicated': duplicate_candles_deduplicated,
        }

    def run_daily_pipeline(self, force_backfill: bool = False, feature_lookback_days: int = 90, feature_backfill: bool = False) -> dict[str, Any]:
        """Run daily OHLCV ingestion, aggregation, and feature refresh in sequence.
        
        Args:
            force_backfill: Force 5-year backfill for OHLCV ingestion
            feature_lookback_days: Days to lookback for feature calculation (ignored if feature_backfill=True)
            feature_backfill: If True, calculate features for ALL OHLCV records (one-time backfill)
        """
        from services.feature import FeatureService

        ingestion_result = self.upsert_daily_ohlcv(force_backfill=force_backfill)
        week_aggregation_result = self.aggregate_from_daily(self.TIMEFRAME_1WEEK)
        month_aggregation_result = self.aggregate_from_daily(self.TIMEFRAME_1MONTH)
        feature_result = FeatureService().upsert_features(lookback_days=feature_lookback_days, backfill=feature_backfill)

        return {
            'success': all([
                ingestion_result.get('success', False),
                week_aggregation_result.get('success', False),
                month_aggregation_result.get('success', False),
                feature_result.get('success', False),
            ]),
            'ingestion': ingestion_result,
            'weekly_aggregation': week_aggregation_result,
            'monthly_aggregation': month_aggregation_result,
            'features': feature_result,
        }

    def aggregate_from_daily(self, target_timeframe: str) -> dict[str, Any]:
        """Aggregate 1DAY candles into 1WEEK or 1MONTH timeframe and upsert."""
        if target_timeframe not in {self.TIMEFRAME_1WEEK, self.TIMEFRAME_1MONTH}:
            raise ValueError('target_timeframe must be 1WEEK or 1MONTH')

        start_date = date.today() - timedelta(days=self.AGGREGATION_RECOMPUTE_DAYS)
        with self._session_factory() as session:
            daily_rows = list(session.execute(select(Ohlcv).where(Ohlcv.timeframe == self.TIMEFRAME_1DAY).where(Ohlcv.candle_date >= start_date).order_by(Ohlcv.security_id.asc(), Ohlcv.candle_date.asc())).scalars().all())

        grouped: dict[tuple[int, date], list[Ohlcv]] = defaultdict(list)
        for row in daily_rows:
            bucket_date = self._bucket_date(row.candle_date, target_timeframe)
            grouped[(row.security_id, bucket_date)].append(row)

        aggregate_rows: list[dict[str, Any]] = []
        for (security_id, bucket_date), records in grouped.items():
            sorted_records = sorted(records, key=lambda item: item.candle_date)
            open_price = sorted_records[0].open
            close_price = sorted_records[-1].close
            high_price = max(item.high for item in sorted_records)
            low_price = min(item.low for item in sorted_records)
            volume_sum = sum(int(item.volume) for item in sorted_records)
            is_continuous = any(item.is_continuous for item in sorted_records)

            aggregate_rows.append(
                {
                    'security_id': security_id,
                    'timeframe': target_timeframe,
                    'candle_date': bucket_date,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume_sum,
                    'is_continuous': is_continuous,
                    'source': 'aggregate',
                }
            )

        affected_security_ids = sorted({row['security_id'] for row in aggregate_rows})
        upserted = self._upsert_ohlcv_rows(aggregate_rows) if aggregate_rows else 0

        return {
            'success': True,
            'timeframe': target_timeframe,
            'inserted_or_updated': upserted,
            'groups_aggregated': len(aggregate_rows),
            'affected_security_count': len(affected_security_ids),
            'affected_security_ids': affected_security_ids,
        }

    def _get_active_eq_and_nfo_fut_securities(self) -> list[Security]:
        """Return active EQ and NFO FUT securities eligible for OHLCV ingestion."""
        with self._session_factory() as session:
            return list(session.execute(select(Security).where(Security.is_active.is_(True)).where((Security.type == 'EQ') | ((Security.type == 'FUT') & (Security.exchange == 'NFO'))).order_by(Security.id.asc())).scalars().all())

    def _get_last_candle_date(self, security_id: int, timeframe: str) -> date | None:
        """Get latest candle date for a security/timeframe key."""
        with self._session_factory() as session:
            return session.execute(select(func.max(Ohlcv.candle_date)).where(Ohlcv.security_id == security_id).where(Ohlcv.timeframe == timeframe)).scalar_one_or_none()

    def _upsert_ohlcv_rows(self, rows: list[dict[str, Any]]) -> int:
        """Bulk upsert OHLCV rows using composite uniqueness."""
        if not rows:
            return 0

        statement = insert(Ohlcv).values(rows)
        upsert_statement = statement.on_conflict_do_update(
            constraint='uq_ohlcv_security_timeframe_candle_date',
            set_={
                'open': statement.excluded.open,
                'high': statement.excluded.high,
                'low': statement.excluded.low,
                'close': statement.excluded.close,
                'volume': statement.excluded.volume,
                'is_continuous': statement.excluded.is_continuous,
                'source': statement.excluded.source,
                'updated_at': func.now(),
            },
        )

        with self._session_factory() as session:
            result = session.execute(upsert_statement)
            session.commit()
            return int(result.rowcount or 0)

    def _bucket_date(self, candle_date: date, timeframe: str) -> date:
        """Normalize a daily candle date to its timeframe bucket date."""
        if timeframe == self.TIMEFRAME_1WEEK:
            return candle_date - timedelta(days=candle_date.weekday())

        if timeframe == self.TIMEFRAME_1MONTH:
            return candle_date.replace(day=1)

        return candle_date

    def _as_decimal(self, value: Any, default: Decimal = Decimal('0')) -> Decimal:
        """Safely convert values to Decimal."""
        if value is None:
            return default

        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return default

    def _as_int(self, value: Any, default: int = 0) -> int:
        """Safely convert values to int."""
        try:
            if value is None:
                return default
            return int(value)
        except (TypeError, ValueError):
            return default

    def _build_daily_rows(self, security_id: int, candles: list[dict[str, Any]], is_future: bool) -> tuple[list[dict[str, Any]], int, int]:
        """Build normalized daily rows while skipping invalid candle payloads."""
        rows_by_date: dict[date, dict[str, Any]] = {}
        skipped_count = 0
        deduplicated_count = 0

        for candle in candles:
            normalized = self._normalize_valid_daily_candle(candle)
            if normalized is None:
                skipped_count += 1
                continue

            candle_date = normalized['candle_date']
            if candle_date in rows_by_date:
                deduplicated_count += 1

            rows_by_date[candle_date] = {
                'security_id': security_id,
                'timeframe': self.TIMEFRAME_1DAY,
                'candle_date': candle_date,
                'open': normalized['open'],
                'high': normalized['high'],
                'low': normalized['low'],
                'close': normalized['close'],
                'volume': self._as_int(candle.get('volume', 0)),
                'is_continuous': is_future,
                'source': 'kite',
            }

        rows = [rows_by_date[key] for key in sorted(rows_by_date.keys())]
        return rows, skipped_count, deduplicated_count

    def _normalize_valid_daily_candle(self, candle: dict[str, Any]) -> dict[str, Any] | None:
        """Return normalized candle values when mandatory OHLC fields are valid."""
        candle_date = candle.get('candle_date')
        if candle_date is None:
            return None

        open_price = self._as_decimal(candle.get('open'), default=None)
        high_price = self._as_decimal(candle.get('high'), default=None)
        low_price = self._as_decimal(candle.get('low'), default=None)
        close_price = self._as_decimal(candle.get('close'), default=None)

        if open_price is None or high_price is None or low_price is None or close_price is None:
            return None

        if high_price < low_price:
            return None

        return {
            'candle_date': candle_date,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
        }
