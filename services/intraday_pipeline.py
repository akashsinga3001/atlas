"""Intraday pipeline to snapshot prices, score signals, and route orders."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from config import settings
from models.security import Security
from services.brokers.kite import KiteService
from services.feature import FeatureService
from services.ml_pipeline import MlPipelineService
from services.ohlcv import OhlcvService
from services.emailer import EmailService
from services.intraday_report import IntradayReportService
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
        self._report_service = IntradayReportService()
        self._email_service = EmailService()
        self._order_router = OrderRoutingService()
        self._kite_service = KiteService()

    def run(self, run_date: date | None = None, execute_orders: bool = True, send_email: bool = True) -> dict[str, Any]:
        """Execute full intraday flow and optionally place orders."""
        effective_date = run_date or date.today()
        logger.info('Intraday pipeline started run_date={} execute_orders={} send_email={}', effective_date, execute_orders, send_email)

        snapshot_result = self._ohlcv_service.upsert_intraday_snapshot_ohlcv(snapshot_date=effective_date)
        feature_result = self._feature_service.upsert_features(lookback_days=90, backfill=False)
        inference_result = self._ml_pipeline.run_daily_inference(report_date=effective_date, send_email=False)

        if not execute_orders:
            result = {
                'success': True,
                'run_date': effective_date.isoformat(),
                'snapshot': snapshot_result,
                'features': feature_result,
                'inference': inference_result,
                'orders': {'executed': False, 'reason': 'execute_orders=false'},
            }
            return self._finalize_run(result, send_email=send_email)

        if not self._order_router.is_configured():
            result = {
                'success': True,
                'run_date': effective_date.isoformat(),
                'snapshot': snapshot_result,
                'features': feature_result,
                'inference': inference_result,
                'orders': {'executed': False, 'reason': 'order_service_not_configured'},
            }
            return self._finalize_run(result, send_email=send_email)

        selected_orders, responses, order_summary = self._build_order_requests(effective_date, inference_result, execute=True)
        result = {
            'success': True,
            'run_date': effective_date.isoformat(),
            'snapshot': snapshot_result,
            'features': feature_result,
            'inference': inference_result,
            'orders': {'executed': True, 'submitted': len(selected_orders), 'responses': responses},
            'order_summary': order_summary,
        }
        return self._finalize_run(result, send_email=send_email)

    def _build_order_requests(self, as_of_date: date, inference_result: dict[str, Any], execute: bool = False) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
        """Select eligible predictions, optionally submitting each immediately.

        Returns (submitted_orders, responses). When execute=False, responses is empty.
        A rejected order skips to the next candidate with no retry.
        """
        top_long = inference_result.get('top_long', []) if isinstance(inference_result, dict) else []
        top_short = inference_result.get('top_short', []) if isinstance(inference_result, dict) else []

        combined = [row for row in (top_long + top_short) if isinstance(row, dict)]
        combined.sort(key=lambda row: float(row.get('confidence', 0.0)), reverse=True)

        min_conf = float(settings.ML_INTRADAY_MIN_CONFIDENCE)
        candidates = [row for row in combined if float(row.get('confidence', 0.0)) >= min_conf]

        open_positions_count = self._kite_open_positions_count()
        available_slots = max(0, int(settings.ML_INTRADAY_MAX_NEW_POSITIONS) - open_positions_count)
        if available_slots == 0:
            return [], [], {
                'signals_generated': len(candidates),
                'attempted_orders': 0,
                'successful_orders': 0,
                'open_positions_count': open_positions_count,
                'available_slots': available_slots,
                'available_funds': None,
                'reserve': None,
                'deployable': None,
                'reject_counts': {},
            }

        available_funds = self._kite_available_funds()
        if available_funds is None:
            logger.warning('Intraday order selection skipped due to missing Kite available funds payload')
            return [], [], {
                'signals_generated': len(candidates),
                'attempted_orders': 0,
                'successful_orders': 0,
                'open_positions_count': open_positions_count,
                'available_slots': available_slots,
                'available_funds': None,
                'reserve': None,
                'deployable': None,
                'reject_counts': {},
            }

        reserve = float(settings.ML_MIN_CASH_RESERVE)
        deployable = max(0.0, float(available_funds) - reserve)
        if deployable <= 0:
            logger.info('Intraday order selection skipped: available_funds={} reserve={}', available_funds, reserve)
            return [], [], {
                'signals_generated': len(candidates),
                'attempted_orders': 0,
                'successful_orders': 0,
                'open_positions_count': open_positions_count,
                'available_slots': available_slots,
                'available_funds': float(available_funds),
                'reserve': reserve,
                'deployable': deployable,
                'reject_counts': {},
            }

        futures_by_underlying = self._active_futures_by_underlying()

        selected: list[dict[str, Any]] = []
        used_underlyings: set[str] = set()
        responses: list[dict[str, Any]] = []
        reject_counts: dict[str, int] = {
            'low_confidence': 0,
            'capacity': 0,
            'duplicate_underlying': 0,
            'no_contract': 0,
            'broker_margin_unavailable': 0,
            'insufficient_funds': 0,
        }

        order_summary: dict[str, Any] = {
            'signals_generated': len(candidates),
            'attempted_orders': 0,
            'successful_orders': 0,
            'open_positions_count': open_positions_count,
            'available_slots': available_slots,
            'available_funds': float(available_funds),
            'reserve': reserve,
            'deployable': deployable,
            'reject_counts': reject_counts,
        }

        for row in candidates:
            if len(selected) >= available_slots:
                reject_counts['capacity'] += 1
                logger.info(
                    'Intraday order filter failed reason=capacity ticker={} confidence={} selected={} available_slots={}',
                    row.get('ticker'),
                    row.get('confidence'),
                    len(selected),
                    available_slots,
                )
                break

            underlying = str(row.get('ticker', '')).strip()
            if not underlying or underlying in used_underlyings:
                reject_counts['duplicate_underlying'] += 1
                logger.info(
                    'Intraday order filter failed reason=duplicate_underlying ticker={} confidence={} underlying={}',
                    row.get('ticker'),
                    row.get('confidence'),
                    underlying,
                )
                continue

            contract = self._resolve_futures_contract_for_date(futures_by_underlying.get(underlying, []), as_of_date)
            if contract is None:
                reject_counts['no_contract'] += 1
                logger.info(
                    'Intraday order filter failed reason=no_contract ticker={} confidence={} date={}',
                    underlying,
                    row.get('confidence'),
                    as_of_date,
                )
                continue

            direction = str(row.get('direction', 'long')).lower()
            side = 'BUY' if direction == 'long' else 'SELL'
            lot_size = int(contract.lot_size or 1)

            limit_price = self._kite_limit_price_for_contract(contract)
            if limit_price is None:
                reject_counts['broker_margin_unavailable'] += 1
                logger.info(
                    'Intraday order filter failed reason=broker_margin_unavailable ticker={} confidence={} contract={} price_reason=missing_quote',
                    underlying,
                    row.get('confidence'),
                    contract.ticker,
                )
                continue

            margin_order = {
                'exchange': str(contract.exchange),
                'tradingsymbol': str(contract.ticker),
                'transaction_type': side,
                'variety': str(settings.ORDER_SERVICE_ORDER_VARIETY),
                'product': 'NRML',
                'order_type': 'LIMIT',
                'quantity': lot_size,
                'price': round(limit_price, 2),
                'trigger_price': 0,
            }
            required_margin = self._kite_service.fetch_order_required_margin(margin_order)
            if required_margin is None:
                reject_counts['broker_margin_unavailable'] += 1
                logger.info(
                    'Intraday order filter failed reason=broker_margin_unavailable ticker={} confidence={} contract={}',
                    underlying,
                    row.get('confidence'),
                    contract.ticker,
                )
                continue

            if deployable - required_margin < 0:
                reject_counts['insufficient_funds'] += 1
                logger.info(
                    'Intraday order filter failed reason=insufficient_funds ticker={} confidence={} contract={} required_margin={} deployable={}',
                    underlying,
                    row.get('confidence'),
                    contract.ticker,
                    round(required_margin, 2),
                    round(deployable, 2),
                )
                continue

            tag = f"ATLAS{as_of_date.strftime('%d%m')}R{int(row.get('rank') or 0)}"
            tag = tag[:20]
            order_entry = {
                'variety': str(settings.ORDER_SERVICE_ORDER_VARIETY),
                'signal_date': as_of_date.isoformat(),
                'underlying': underlying,
                'direction': direction,
                'confidence': float(row.get('confidence', 0.0)),
                'rank': row.get('rank'),
                'required_margin_inr': round(required_margin, 2),
                'order': {
                    'exchange': str(contract.exchange),
                    'tradingsymbol': str(contract.ticker),
                    'transaction_type': side,
                    'quantity': lot_size,
                    'product': 'NRML',
                    'order_type': 'LIMIT',
                    'price': round(limit_price, 2),
                    'validity': 'DAY',
                    'tag': tag,
                },
            }

            if execute:
                success, response = self._order_router.route_single_order(order_entry)
                if not success:
                    logger.warning(
                        'Intraday order rejected by broker ticker={} contract={} reason={}',
                        underlying,
                        contract.ticker,
                        response.get('error', 'unknown'),
                    )
                    responses.append({'request': order_entry, 'response': response, 'success': False})
                    continue
                logger.info(
                    'Intraday order placed ticker={} contract={} order_id={}',
                    underlying,
                    contract.ticker,
                    response.get('order_id'),
                )
                responses.append({'request': order_entry, 'response': response, 'success': True})

            selected.append(order_entry)
            used_underlyings.add(underlying)
            deployable -= required_margin

        if not selected:
            logger.warning(
                'Intraday order selection produced no orders. reasons={} open_positions_count={} available_slots={} available_funds={} reserve={}',
                reject_counts,
                open_positions_count,
                available_slots,
                available_funds,
                reserve,
            )

        order_summary['attempted_orders'] = len(responses)
        order_summary['successful_orders'] = len(selected)
        return selected, responses, order_summary

    def _kite_limit_price_for_contract(self, contract: Security) -> float | None:
        """Return a live limit price for the contract from the broker quote snapshot."""
        quote_key = f'{str(contract.exchange)}:{str(contract.ticker)}'
        payload = self._kite_service.fetch_quotes([quote_key])
        if not isinstance(payload, dict):
            return None

        quote = payload.get(quote_key)
        if not isinstance(quote, dict):
            return None

        for field in ('last_price', 'last_traded_price', 'ltp'):
            value = quote.get(field)
            try:
                if value is None:
                    continue
                price = float(value)
                if price > 0:
                    return price
            except (TypeError, ValueError):
                continue

        return None

    def _finalize_run(self, result: dict[str, Any], send_email: bool) -> dict[str, Any]:
        """Send the intraday execution report email and annotate the result."""
        report_sent = False
        report_subject = f"Atlas Intraday Execution Report - {result.get('run_date', date.today().isoformat())}"

        if send_email:
            try:
                html_body = self._report_service.build_html(result)
                self._email_service.send_html(settings.ML_REPORT_RECIPIENT, report_subject, html_body)
                report_sent = True
            except Exception as exc:
                logger.error('Intraday report email delivery failed error={}', exc)

        result['report'] = {
            'email_sent': report_sent,
            'email_to': settings.ML_REPORT_RECIPIENT,
            'subject': report_subject,
        }
        return result

    def _kite_open_positions_count(self) -> int:
        """Count currently open live positions from Kite positions payload."""
        payload = self._kite_service.fetch_positions()
        if not isinstance(payload, dict):
            return 0

        # Use only net positions for open count. The day section can include
        # intraday activity snapshots that overstate currently open exposure.
        section = payload.get('net')
        rows: list[dict[str, Any]] = section if isinstance(section, list) else []

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

    def _kite_available_funds(self) -> float | None:
        """Extract current available funds from Kite margins payload."""
        payload = self._kite_service.fetch_margins()
        if not isinstance(payload, dict):
            return None

        for segment_key in ('equity', 'commodity'):
            segment = payload.get(segment_key)
            if not isinstance(segment, dict):
                continue

            candidates: list[Any] = [segment.get('net')]
            available = segment.get('available')
            if isinstance(available, dict):
                candidates.append(available.get('live_balance'))

            for value in candidates:
                try:
                    if value is None:
                        continue
                    return float(value)
                except (TypeError, ValueError):
                    continue

        return None

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
