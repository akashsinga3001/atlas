"""Security service for futures and underlying instrument ingestion."""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import create_engine, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker

from config import settings
from models.security import Security
from services.brokers.kite import KiteService
from utils.logger import logger


class SecurityService:
    """Service class for securities ingestion and upsert workflows."""

    FUT_UNDERLYING_PATTERN = re.compile(r'^(?P<base>[A-Z0-9&\-]+?)(?:\d{1,2}[A-Z]{3}\d{2}|[A-Z]{3}\d{2})FUT$')
    FUT_PREFIX_FALLBACK_PATTERN = re.compile(r'^(?P<base>[A-Z0-9&\-]+?)(?=\d)')
    CASH_EQUITY_SEGMENTS = {'NSE', 'BSE'}
    INDEX_SEGMENT = 'INDICES'
    CASH_EQUITY_TYPE = 'EQ'

    def __init__(self) -> None:
        self.kite_service = KiteService()
        self._engine = create_engine(settings.DATABASE_URL, echo=settings.DB_ECHO, future=True)
        self._session_factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, future=True)

    def upsert_nfo_futures_and_underlyings(self) -> dict[str, Any]:
        """Fetch NFO futures, resolve equity/index underlyings, and upsert both into securities.

        Returns:
            dict[str, Any]: Structured summary with success flag and ingestion counts.
                Keys: success, futures_count, underlyings_count, upserted_count,
                unresolved_underlyings_count, unresolved_underlyings,
                deactivated_futures_count.
        """
        instruments = self.kite_service.fetch_instruments()
        nfo_futures = [item for item in instruments if str(item.get('segment', '')).upper() == 'NFO-FUT']

        if not nfo_futures:
            logger.warning('No NFO-FUT instruments returned from Kite')
            return {'success': True, 'futures_count': 0, 'underlyings_count': 0, 'upserted_count': 0, 'unresolved_underlyings_count': 0, 'unresolved_underlyings': []}

        equity_index_lookup = self._build_equity_index_lookup(instruments)
        rows_by_ticker: dict[str, dict[str, Any]] = {}
        unresolved_underlyings: set[str] = set()
        resolved_underlying_count = 0
        active_future_tickers: set[str] = set()

        for future_instrument in nfo_futures:
            future_row = self._to_security_row(future_instrument)
            rows_by_ticker[future_row['ticker']] = future_row
            active_future_tickers.add(future_row['ticker'])

            underlying_symbol = self._extract_underlying_symbol(str(future_instrument.get('tradingsymbol', '')))
            if not underlying_symbol:
                unresolved_underlyings.add(str(future_instrument.get('tradingsymbol', '')))
                continue

            underlying_instrument = equity_index_lookup.get(underlying_symbol)
            if underlying_instrument is None:
                unresolved_underlyings.add(underlying_symbol)
                continue

            underlying_row = self._to_security_row(underlying_instrument)
            rows_by_ticker[underlying_row['ticker']] = underlying_row
            resolved_underlying_count += 1

        upsert_rows = list(rows_by_ticker.values())
        if upsert_rows:
            self._upsert_rows(upsert_rows)

        deactivated_futures_count = self._deactivate_stale_nfo_futures(active_future_tickers)

        if unresolved_underlyings:
            sample = sorted(unresolved_underlyings)[:20]
            logger.warning('Unable to resolve {} FUT underlyings from instrument universe. Sample={}', len(unresolved_underlyings), sample)

        logger.info(
            'Securities upsert completed. futures={} resolved_underlyings={} upserted={} unresolved={} deactivated_futures={}',
            len(nfo_futures),
            resolved_underlying_count,
            len(upsert_rows),
            len(unresolved_underlyings),
            deactivated_futures_count,
        )

        return {
            'success': True,
            'futures_count': len(nfo_futures),
            'underlyings_count': resolved_underlying_count,
            'upserted_count': len(upsert_rows),
            'unresolved_underlyings_count': len(unresolved_underlyings),
            'unresolved_underlyings': sorted(unresolved_underlyings),
            'deactivated_futures_count': deactivated_futures_count,
        }

    def _build_equity_index_lookup(self, instruments: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Create tradingsymbol lookup for equity/index instruments."""
        lookup: dict[str, dict[str, Any]] = {}

        for instrument in instruments:
            if not self._is_equity_or_index_instrument(instrument):
                continue

            ticker = str(instrument.get('tradingsymbol', '')).strip().upper()
            if not ticker:
                continue
            lookup[ticker] = instrument

        return lookup

    def get_eq_securities_needing_enrichment(self, limit: int | None = None) -> list[Security]:
        """Fetch active EQ securities with any missing enrichment classification fields."""
        missing_enrichment_condition = or_(
            Security.macro_economic_sector.is_(None),
            func.trim(Security.macro_economic_sector) == '',
            Security.sector.is_(None),
            func.trim(Security.sector) == '',
            Security.industry.is_(None),
            func.trim(Security.industry) == '',
            Security.basic_industry.is_(None),
            func.trim(Security.basic_industry) == '',
        )

        statement = (select(Security).where(Security.type == self.CASH_EQUITY_TYPE).where(Security.is_active.is_(True)).where(missing_enrichment_condition).order_by(Security.id.asc()))

        if limit is not None:
            statement = statement.limit(limit)

        with self._session_factory() as session:
            return list(session.execute(statement).scalars().all())

    def update_missing_enrichment_fields(self, security_id: int, enrichment_data: dict[str, str | None]) -> bool:
        """Update only missing enrichment fields for a security; returns True when any field is updated."""
        supported_fields = ('macro_economic_sector', 'sector', 'industry', 'basic_industry')

        with self._session_factory() as session:
            security = session.get(Security, security_id)
            if security is None:
                return False

            updated = False
            for field in supported_fields:
                current_value = getattr(security, field)
                incoming_value = enrichment_data.get(field)

                if incoming_value is None:
                    continue

                normalized_incoming = str(incoming_value).strip()
                if not normalized_incoming:
                    continue

                if current_value is None or not str(current_value).strip():
                    setattr(security, field, normalized_incoming)
                    updated = True

            if updated:
                session.commit()

            return updated

    def _is_equity_or_index_instrument(self, instrument: dict[str, Any]) -> bool:
        """Return True only for equity/index instruments eligible as futures underlyings."""
        segment = str(instrument.get('segment', '')).upper()
        instrument_type = str(instrument.get('instrument_type', '')).upper()

        # Based on observed Kite instrument list values:
        # - Cash equities are represented as segment NSE/BSE with instrument_type EQ.
        # - Index instruments are represented by segment INDICES.
        if segment in self.CASH_EQUITY_SEGMENTS and instrument_type == self.CASH_EQUITY_TYPE:
            return True

        return segment == self.INDEX_SEGMENT

    def _extract_underlying_symbol(self, future_ticker: str) -> str | None:
        """Derive underlying symbol from NFO future ticker using regex-first fallback logic."""
        ticker = future_ticker.strip().upper()
        if not ticker or not ticker.endswith('FUT'):
            return None

        regex_match = self.FUT_UNDERLYING_PATTERN.match(ticker)
        if regex_match:
            base = regex_match.group('base')
            return base or None

        fallback_match = self.FUT_PREFIX_FALLBACK_PATTERN.match(ticker)
        if fallback_match:
            base = fallback_match.group('base')
            return base or None

        # Final fallback keeps behavior deterministic for unusual symbol formats.
        fallback = ticker[:-3].rstrip('0123456789')
        return fallback or None

    def _to_security_row(self, instrument: dict[str, Any]) -> dict[str, Any]:
        """Transform raw instrument payload into securities table row shape."""
        ticker = str(instrument.get('tradingsymbol', '')).strip().upper()
        if not ticker:
            raise ValueError('Instrument payload missing tradingsymbol')

        display_name = str(instrument.get('name', '')).strip() or ticker
        instrument_type = str(instrument.get('instrument_type', '')).strip() or str(instrument.get('segment', '')).strip() or 'UNKNOWN'

        return {
            'ticker': ticker,
            'display_name': display_name,
            'exchange': str(instrument.get('exchange', '')).strip() or 'UNKNOWN',
            'broker_token': self._as_string(instrument.get('instrument_token')),
            'exchange_token': self._as_string(instrument.get('exchange_token')),
            'type': instrument_type,
            'is_active': True,
            'macro_economic_sector': None,
            'sector': None,
            'industry': None,
            'basic_industry': None,
            'lot_size': self._as_int(instrument.get('lot_size'), default=1),
            'tick_size': self._as_decimal(instrument.get('tick_size'), default=Decimal('0.000000')),
            'expiry_date': self._as_date(instrument.get('expiry'))
        }

    def _as_decimal(self, value: Any, default: Decimal) -> Decimal:
        """Convert numeric value to Decimal with safe fallback."""
        if value is None:
            return default

        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return default

    def _as_int(self, value: Any, default: int) -> int:
        """Convert value to int with safe fallback."""
        try:
            if value is None:
                return default
            return int(value)
        except (ValueError, TypeError):
            return default

    def _as_date(self, value: Any) -> date | None:
        """Normalize date/datetime/ISO-date values to date or None."""
        if value is None:
            return None

        if isinstance(value, date) and not isinstance(value, datetime):
            return value

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None
            try:
                return date.fromisoformat(raw)
            except ValueError:
                return None

        return None

    def _as_string(self, value: Any, default: str = '') -> str:
        """Convert value to a trimmed string while keeping None as default."""
        if value is None:
            return default

        normalized = str(value).strip()
        return normalized if normalized else default

    def _upsert_rows(self, rows: list[dict[str, Any]]) -> None:
        """Bulk upsert rows by ticker while preserving selected existing metadata."""
        statement = insert(Security).values(rows)

        with self._session_factory() as session:
            upsert_statement = statement.on_conflict_do_update(
                index_elements=[Security.ticker],
                set_={
                    'display_name': func.coalesce(Security.display_name, statement.excluded.display_name),
                    'exchange': statement.excluded.exchange,
                    'broker_token': statement.excluded.broker_token,
                    'exchange_token': statement.excluded.exchange_token,
                    'type': statement.excluded.type,
                    'is_active': statement.excluded.is_active,
                    'macro_economic_sector': func.coalesce(Security.macro_economic_sector, statement.excluded.macro_economic_sector),
                    'sector': func.coalesce(Security.sector, statement.excluded.sector),
                    'industry': func.coalesce(Security.industry, statement.excluded.industry),
                    'basic_industry': func.coalesce(Security.basic_industry, statement.excluded.basic_industry),
                    'lot_size': statement.excluded.lot_size,
                    'tick_size': statement.excluded.tick_size,
                    'expiry_date': statement.excluded.expiry_date,
                },
            )
            session.execute(upsert_statement)
            session.commit()

    def _deactivate_stale_nfo_futures(self, active_future_tickers: set[str]) -> int:
        """Mark expired or missing NFO FUT rows inactive after each successful upsert run."""
        stale_condition = Security.expiry_date < date.today()
        if active_future_tickers:
            stale_condition = or_(stale_condition, ~Security.ticker.in_(active_future_tickers))

        statement = (update(Security).where(Security.exchange == 'NFO').where(Security.type == 'FUT').where(Security.is_active.is_(True)).where(stale_condition).values(is_active=False))

        with self._session_factory() as session:
            result = session.execute(statement)
            session.commit()
            return int(result.rowcount or 0)
