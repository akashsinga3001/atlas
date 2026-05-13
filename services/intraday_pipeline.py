"""Intraday pipeline to snapshot prices, score signals, and route orders."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from config import settings
from models.ohlcv import Ohlcv
from models.security import Security
from services.brokers.kite import KiteService
from services.feature import FeatureService
from services.ml_pipeline import MlPipelineService
from services.ohlcv import OhlcvService
from services.order_router import OrderRoutingService
from utils.logger import logger


class IntradayPipelineService:
    """Runs intraday snapshot ingestion, inference, and external order routing."""

    def __init__(self) -> None:
        self._engine = create_engine(settings.DATABASE_URL, echo=settings.DB_ECHO, future=True)
        self._session_factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, future=True)
        self._ohlcv_service = OhlcvService()
        self._feature_service = FeatureService()
        self._ml_pipeline = MlPipelineService()
        self._order_router = OrderRoutingService()
        self._kite_service = KiteService()

    def run(self, run_date: date | None = None, execute_orders: bool = True) -> dict[str, Any]:
        """Execute full intraday flow and optionally place orders."""
        effective_date = run_date or date.today()
        logger.info('Intraday pipeline started run_date={} execute_orders={}', effective_date, execute_orders)

        snapshot_result = self._ohlcv_service.upsert_intraday_snapshot_ohlcv(snapshot_date=effective_date)
        feature_result = self._feature_service.upsert_features(lookback_days=90, backfill=False)
        inference_result = self._ml_pipeline.run_daily_inference(report_date=effective_date, send_email=False)

        if not execute_orders:
            return {
                'success': True,
                'run_date': effective_date.isoformat(),
                'snapshot': snapshot_result,
                'features': feature_result,
                'inference': inference_result,
                'orders': {'executed': False, 'reason': 'execute_orders=false'},
            }

        if not self._order_router.is_configured():
            return {
                'success': True,
                'run_date': effective_date.isoformat(),
                'snapshot': snapshot_result,
                'features': feature_result,
                'inference': inference_result,
                'orders': {'executed': False, 'reason': 'order_service_not_configured'},
            }

        selected_orders = self._build_order_requests(effective_date, inference_result)
        if not selected_orders:
            return {
                'success': True,
                'run_date': effective_date.isoformat(),
                'snapshot': snapshot_result,
                'features': feature_result,
                'inference': inference_result,
                'orders': {'executed': True, 'submitted': 0, 'responses': []},
            }

        responses = self._order_router.route_orders(selected_orders)
        return {
            'success': True,
            'run_date': effective_date.isoformat(),
            'snapshot': snapshot_result,
            'features': feature_result,
            'inference': inference_result,
            'orders': {'executed': True, 'submitted': len(selected_orders), 'responses': responses},
        }

    def _build_order_requests(self, as_of_date: date, inference_result: dict[str, Any]) -> list[dict[str, Any]]:
        """Select eligible predictions and convert them into order payloads."""
        top_long = inference_result.get('top_long', []) if isinstance(inference_result, dict) else []
        top_short = inference_result.get('top_short', []) if isinstance(inference_result, dict) else []

        combined = [row for row in (top_long + top_short) if isinstance(row, dict)]
        combined.sort(key=lambda row: float(row.get('confidence', 0.0)), reverse=True)

        min_conf = float(settings.ML_INTRADAY_MIN_CONFIDENCE)
        candidates = [row for row in combined if float(row.get('confidence', 0.0)) >= min_conf]

        open_positions_count = self._kite_open_positions_count()
        available_slots = max(0, int(settings.ML_INTRADAY_MAX_NEW_POSITIONS) - open_positions_count)
        if available_slots == 0:
            return []

        available_margin = self._kite_available_margin()
        if available_margin is None:
            logger.warning('Intraday order selection skipped due to missing Kite margin payload')
            return []

        reserve = float(settings.ML_MIN_CASH_RESERVE)
        deployable = max(0.0, float(available_margin) - reserve)
        if deployable <= 0:
            logger.info('Intraday order selection skipped: available_margin={} reserve={}', available_margin, reserve)
            return []

        futures_by_underlying = self._active_futures_by_underlying()
        futures_prices = self._futures_prices_on_date(as_of_date)

        selected: list[dict[str, Any]] = []
        used_underlyings: set[str] = set()

        for row in candidates:
            if len(selected) >= available_slots:
                break

            underlying = str(row.get('ticker', '')).strip()
            if not underlying or underlying in used_underlyings:
                continue

            contract = self._resolve_futures_contract_for_date(futures_by_underlying.get(underlying, []), as_of_date)
            if contract is None:
                continue

            fut_price = futures_prices.get(int(contract.id), 0.0)
            if fut_price <= 0:
                continue

            lot_size = int(contract.lot_size or 1)
            estimated_notional = fut_price * lot_size
            if deployable - estimated_notional < 0:
                continue

            direction = str(row.get('direction', 'long')).lower()
            side = 'BUY' if direction == 'long' else 'SELL'
            tag = f"ATLAS{as_of_date.strftime('%d%m')}R{int(row.get('rank') or 0)}"
            tag = tag[:20]
            selected.append(
                {
                    'variety': str(settings.ORDER_SERVICE_ORDER_VARIETY),
                    'signal_date': as_of_date.isoformat(),
                    'underlying': underlying,
                    'direction': direction,
                    'confidence': float(row.get('confidence', 0.0)),
                    'rank': row.get('rank'),
                    'estimated_notional_inr': round(estimated_notional, 2),
                    'order': {
                        'exchange': str(contract.exchange),
                        'tradingsymbol': str(contract.ticker),
                        'transaction_type': side,
                        'quantity': lot_size,
                        'product': 'NRML',
                        'order_type': 'MARKET',
                        'validity': 'DAY',
                        'tag': tag,
                    },
                }
            )
            used_underlyings.add(underlying)
            deployable -= estimated_notional

        return selected

    def _kite_open_positions_count(self) -> int:
        """Count currently open live positions from Kite positions payload."""
        payload = self._kite_service.fetch_positions()
        if not isinstance(payload, dict):
            return 0

        rows: list[dict[str, Any]] = []
        for key in ('net', 'day'):
            section = payload.get(key)
            if isinstance(section, list):
                rows.extend(item for item in section if isinstance(item, dict))

        seen_symbols: set[str] = set()
        open_count = 0
        for row in rows:
            quantity = row.get('quantity')
            try:
                qty = float(quantity)
            except (TypeError, ValueError):
                qty = 0.0
            if qty == 0:
                continue

            symbol = str(row.get('tradingsymbol', '')).strip().upper()
            if symbol and symbol in seen_symbols:
                continue
            if symbol:
                seen_symbols.add(symbol)
            open_count += 1

        return open_count

    def _kite_available_margin(self) -> float | None:
        """Extract available margin from Kite margins payload."""
        payload = self._kite_service.fetch_margins()
        if not isinstance(payload, dict):
            return None

        candidates: list[Any] = []
        for segment_key in ('equity', 'commodity'):
            segment = payload.get(segment_key)
            if not isinstance(segment, dict):
                continue
            available = segment.get('available')
            if isinstance(available, dict):
                candidates.extend(
                    [
                        available.get('cash'),
                        available.get('live_balance'),
                        available.get('opening_balance'),
                        available.get('adhoc_margin'),
                        available.get('collateral'),
                    ]
                )

        for value in candidates:
            try:
                if value is None:
                    continue
                return float(value)
            except (TypeError, ValueError):
                continue

        return None

    def _futures_prices_on_date(self, target_date: date) -> dict[int, float]:
        """Return closing price map for all futures on the selected date."""
        with self._session_factory() as session:
            rows = session.execute(
                select(Ohlcv.security_id, Ohlcv.close)
                .where(Ohlcv.timeframe == '1DAY')
                .where(Ohlcv.candle_date == target_date)
            ).all()

        return {int(row.security_id): float(row.close) for row in rows}

    def _active_futures_by_underlying(self) -> dict[str, list[Security]]:
        """Load active futures grouped by underlying ticker."""
        with self._session_factory() as session:
            futures = list(
                session.execute(
                    select(Security)
                    .where(Security.type == 'FUT')
                    .where(Security.is_active.is_(True))
                    .where(Security.expiry_date.is_not(None))
                    .order_by(Security.display_name.asc(), Security.expiry_date.asc())
                ).scalars().all()
            )

        grouped: dict[str, list[Security]] = {}
        for future in futures:
            underlying = str(future.display_name)
            grouped.setdefault(underlying, []).append(future)
        return grouped

    def _resolve_futures_contract_for_date(self, contracts: list[Security], as_of_date: date) -> Security | None:
        """Select futures contract by date rule: <=15 current month, >15 next month."""
        if not contracts:
            return None

        target_year = as_of_date.year
        target_month = as_of_date.month
        if as_of_date.day > 15:
            if target_month == 12:
                target_month = 1
                target_year += 1
            else:
                target_month += 1

        month_matches = [
            contract
            for contract in contracts
            if contract.expiry_date is not None
            and contract.expiry_date.year == target_year
            and contract.expiry_date.month == target_month
            and contract.expiry_date >= as_of_date
        ]
        if month_matches:
            return min(month_matches, key=lambda item: item.expiry_date or date.max)

        valid_future = [contract for contract in contracts if contract.expiry_date is not None and contract.expiry_date >= as_of_date]
        if valid_future:
            return min(valid_future, key=lambda item: item.expiry_date or date.max)

        return None
