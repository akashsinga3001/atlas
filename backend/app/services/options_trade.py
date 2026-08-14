# backend/app/services/options_trade.py

import time
from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional

from app.enums.options import OptionsPositionStatus, OptionsLegRole, OptionsLegStatus, OptionsExitReason
from app.enums.strategy import StrategyRunStatus
from app.models.security import Security
from app.models.strategy import StrategyRun, StrategySignal, StrategyVersion
from app.models.options import OptionsPosition, OptionsLeg
from app.repositories.options import OptionsPositionRepository, OptionsLegRepository
from app.repositories.security import SecurityRepository
from app.schemas.base import APIResponse
from app.services.brokers.kite import KiteService
from app.services.portfolio import PortfolioService
from app.utils.trading_calendar import is_nse_trading_day, next_nse_trading_day, add_nse_trading_days
from app.utils.logger import get_logger

logger = get_logger(__name__)

KITE_EXCHANGE = "NFO"
KITE_PRODUCT = "NRML"

# Marketable-limit buffers, mirroring TradeService's ORDER_BUY_BUFFER/ORDER_SELL_BUFFER
# convention but wider — weekly index option spreads run noticeably wider than the
# liquid NSE equities the 0.2% equity buffer was tuned for.
ORDER_BUFFERS = {"BUY": 1.02, "SELL": 0.98}

LONG_ROLES = [OptionsLegRole.LONG_CALL, OptionsLegRole.LONG_PUT]
SHORT_ROLES = [OptionsLegRole.SHORT_CALL, OptionsLegRole.SHORT_PUT]

# Entry: BUY the protective wings first, then SELL the short strikes — at every
# intermediate step exposure is long-only (bounded risk), never short-naked.
ENTRY_TRANSACTION = {
    OptionsLegRole.LONG_CALL: "BUY", OptionsLegRole.LONG_PUT: "BUY",
    OptionsLegRole.SHORT_CALL: "SELL", OptionsLegRole.SHORT_PUT: "SELL",
}
# Exit: buy back the shorts first (removes the uncapped side), then sell the longs —
# mirrors entry ordering for the same reason.
CLOSE_TRANSACTION = {
    OptionsLegRole.LONG_CALL: "SELL", OptionsLegRole.LONG_PUT: "SELL",
    OptionsLegRole.SHORT_CALL: "BUY", OptionsLegRole.SHORT_PUT: "BUY",
}


class OptionsTradeService:
    """Parallel-to-TradeService engine for the 4-leg NIFTY iron condor.

    Built fresh rather than routed through TradeService.open_trade() — that engine assumes
    a single BUY-to-open leg with a GTT stop, which doesn't fit simultaneous multi-leg entry,
    short-leg semantics, or a defined-risk-by-construction exit. Follows the same layering
    conventions (service -> repository -> model, same error handling/logging style) instead.
    """

    def __init__(self, db: Session, kite_service: KiteService = None):
        self.db = db
        self.kite_service = kite_service
        self.position_repo = OptionsPositionRepository(db)
        self.leg_repo = OptionsLegRepository(db)
        self.security_repo = SecurityRepository(db)
        if kite_service:
            self.portfolio_service = PortfolioService(db, kite_service)

    # ------------------------------------------------------------------ #
    #  Entry                                                              #
    # ------------------------------------------------------------------ #

    def run_entry(self, strategy_version: StrategyVersion, as_of_date: date) -> APIResponse:
        """Enter the week's iron condor if today is the entry day for a not-yet-consumed signal."""
        try:
            if not is_nse_trading_day(as_of_date):
                return APIResponse(success=True, message="NOT_A_TRADING_DAY", data={})

            active = self.position_repo.get_active_for_strategy_version(strategy_version.id)

            if active and active.status == OptionsPositionStatus.PENDING:
                logger.info(f"Resuming PENDING options position {active.id}.")
                return self._place_entry_orders(active)

            if active:
                return APIResponse(success=True, message="POSITION_ALREADY_OPEN", data={ "options_position_id": active.id })

            signal = self._find_entry_signal(strategy_version, as_of_date)
            if not signal:
                return APIResponse(success=True, message="NO_SIGNAL_FOR_TODAY", data={})

            if self.position_repo.get_by_signal_id(signal.id):
                return APIResponse(success=True, message="SIGNAL_ALREADY_CONSUMED", data={})

            return self._enter_from_signal(signal, strategy_version, as_of_date)
        except Exception as exc:
            logger.error(f"Options entry failed for strategy version {strategy_version.id}: {exc}", exc_info=True)
            return APIResponse(success=False, message=str(exc))

    def _find_entry_signal(self, strategy_version: StrategyVersion, as_of_date: date) -> Optional[StrategySignal]:
        """Return the most recent COMPLETED run's signal iff as_of_date is the NSE trading day right after it."""
        latest_run = (
            self.db.query(StrategyRun)
            .filter(StrategyRun.strategy_version_id == strategy_version.id, StrategyRun.status == StrategyRunStatus.COMPLETED)
            .order_by(StrategyRun.id.desc())
            .first()
        )
        if not latest_run or not latest_run.signals:
            return None

        signal = latest_run.signals[0]
        signal_date = signal.observed_at.date()

        if next_nse_trading_day(signal_date) != as_of_date:
            return None
        return signal

    def _enter_from_signal(self, signal: StrategySignal, strategy_version: StrategyVersion, as_of_date: date) -> APIResponse:
        config = strategy_version.config
        spot = float(signal.payload["spot_close"])
        step = config["strike_step"]

        def round_to_step(x: float) -> float:
            return round(x / step) * step

        call_short = round_to_step(spot * (1 + config["short_otm_pct"]))
        put_short = round_to_step(spot * (1 - config["short_otm_pct"]))
        call_long = round_to_step(spot * (1 + config["long_otm_pct"]))
        put_long = round_to_step(spot * (1 - config["long_otm_pct"]))

        expiry = self._resolve_expiry(config, as_of_date)
        if not expiry:
            return self._skip(signal, strategy_version, as_of_date, spot, "no expiry available in the option chain")

        strikes = {
            OptionsLegRole.SHORT_CALL: (call_short, "CE"), OptionsLegRole.SHORT_PUT: (put_short, "PE"),
            OptionsLegRole.LONG_CALL: (call_long, "CE"), OptionsLegRole.LONG_PUT: (put_long, "PE"),
        }

        contracts: dict[OptionsLegRole, Security] = {}
        for role, (strike, right) in strikes.items():
            sec = self._find_contract(config, expiry, strike, right)
            if not sec:
                return self._skip(signal, strategy_version, as_of_date, spot, f"contract not found: {role.value} strike={strike} {right} expiry={expiry}")
            contracts[role] = sec

        lot_sizes = { sec.lot_size for sec in contracts.values() }
        if len(lot_sizes) != 1 or None in lot_sizes:
            return self._skip(signal, strategy_version, as_of_date, spot, f"inconsistent/missing lot size across legs: {lot_sizes}")
        lot_size = lot_sizes.pop()

        try:
            quotes = self.kite_service.get_quotes([f"{KITE_EXCHANGE}:{sec.ticker}" for sec in contracts.values()])
        except Exception:
            logger.error("Failed to fetch entry-leg quotes.", exc_info=True)
            return self._skip(signal, strategy_version, as_of_date, spot, "failed to fetch leg quotes")

        ltps: dict[OptionsLegRole, float] = {}
        for role, sec in contracts.items():
            quote = quotes.get(f"{KITE_EXCHANGE}:{sec.ticker}")
            ltp = quote["last_price"] if quote else 0
            if not ltp or ltp <= 0:
                return self._skip(signal, strategy_version, as_of_date, spot, f"leg not tradable: {sec.ticker}")
            ltps[role] = float(ltp)

        net_credit_per_lot = (ltps[OptionsLegRole.SHORT_CALL] + ltps[OptionsLegRole.SHORT_PUT]) - (ltps[OptionsLegRole.LONG_CALL] + ltps[OptionsLegRole.LONG_PUT])
        call_wing_width = call_long - call_short
        put_wing_width = put_short - put_long
        max_wing_width = max(call_wing_width, put_wing_width)
        margin_per_lot = max_wing_width * lot_size - net_credit_per_lot * lot_size

        if margin_per_lot <= 0:
            return self._skip(signal, strategy_version, as_of_date, spot, f"non-positive margin_per_lot ({margin_per_lot}) — refusing to size")

        capital = self.portfolio_service.get_account_size()
        lots = min(int(capital * config["capital_pct"] // margin_per_lot), config["max_lots"])

        if lots < 1:
            return self._skip(signal, strategy_version, as_of_date, spot, f"position size rounds to 0 lots (capital={capital:.2f}, margin_per_lot={margin_per_lot:.2f})")

        planned_exit_date = min(add_nse_trading_days(as_of_date, config["hold_days"]), expiry)

        position = OptionsPosition(
            strategy_signal_id=signal.id, strategy_version_id=strategy_version.id, signal_date=signal.observed_at.date(), entry_date=as_of_date, spot_at_signal=spot,
            expiry_date=expiry, call_short_strike=call_short, put_short_strike=put_short, call_long_strike=call_long, put_long_strike=put_long,
            lots=lots, lot_size=lot_size, margin_per_lot=margin_per_lot, net_credit_per_lot=net_credit_per_lot,
            status=OptionsPositionStatus.PENDING, planned_exit_date=planned_exit_date,
        )
        self.db.add(position)
        self.db.commit()
        self.db.refresh(position)

        for role, sec in contracts.items():
            self.db.add(OptionsLeg(options_position_id=position.id, security_id=sec.id, role=role, status=OptionsLegStatus.PENDING))
        self.db.commit()

        logger.info(f"Created PENDING options position {position.id}: {lots} lots, expiry={expiry}, "
                    f"short C{call_short}/P{put_short}, long C{call_long}/P{put_long}, margin/lot={margin_per_lot:.2f}")

        return self._place_entry_orders(position)

    def _skip(self, signal: StrategySignal, strategy_version: StrategyVersion, as_of_date: date, spot: float, reason: str) -> APIResponse:
        logger.warning(f"Skipping iron condor entry for signal {signal.id}: {reason}")
        position = OptionsPosition(
            strategy_signal_id=signal.id, strategy_version_id=strategy_version.id, signal_date=signal.observed_at.date(), entry_date=as_of_date, spot_at_signal=spot,
            status=OptionsPositionStatus.SKIPPED, skip_reason=reason,
        )
        self.db.add(position)
        self.db.commit()
        return APIResponse(success=True, message="ENTRY_SKIPPED", data={ "reason": reason })

    def _resolve_expiry(self, config: dict, as_of_date: date) -> Optional[date]:
        """Nearest expiry strictly after as_of_date among expiries actually listed in the local option chain."""
        option_name = config.get("option_name", "NIFTY")
        row = (
            self.db.query(func.date(Security.expiry_date))
            .filter(Security.type == "OPTION", Security.display_name == option_name, Security.is_active == True, func.date(Security.expiry_date) > as_of_date)
            .distinct()
            .order_by(func.date(Security.expiry_date).asc())
            .first()
        )
        return row[0] if row else None

    def _find_contract(self, config: dict, expiry: date, strike: float, right: str) -> Optional[Security]:
        option_name = config.get("option_name", "NIFTY")
        return (
            self.db.query(Security)
            .filter(
                Security.type == "OPTION", Security.display_name == option_name, Security.is_active == True,
                Security.option_type == right, Security.strike == strike, func.date(Security.expiry_date) == expiry,
            )
            .first()
        )

    def _place_entry_orders(self, position: OptionsPosition) -> APIResponse:
        legs = { leg.role: leg for leg in self.leg_repo.get_for_position(position.id) }

        longs_ok = self._fill_legs([legs[r] for r in LONG_ROLES if r in legs], ENTRY_TRANSACTION, position.lots * position.lot_size, is_entry=True)
        if not longs_ok:
            self.position_repo.update(position, { "status": OptionsPositionStatus.FAILED })
            logger.error(f"Options position {position.id} FAILED — could not establish protective long legs.")
            return APIResponse(success=False, message="ENTRY_FAILED_LONG_LEGS", data={ "options_position_id": position.id })

        shorts_ok = self._fill_legs([legs[r] for r in SHORT_ROLES if r in legs], ENTRY_TRANSACTION, position.lots * position.lot_size, is_entry=True)
        if not shorts_ok:
            logger.warning(f"Options position {position.id}: long legs filled, short legs still pending — will retry next entry-job tick.")
            return APIResponse(success=True, message="ENTRY_PARTIAL_LONGS_ONLY", data={ "options_position_id": position.id })

        self.position_repo.update(position, { "status": OptionsPositionStatus.OPEN })
        logger.info(f"Options position {position.id} fully OPEN.")
        return APIResponse(success=True, message="ENTRY_COMPLETED", data=self._position_summary(position))

    # ------------------------------------------------------------------ #
    #  Exit                                                               #
    # ------------------------------------------------------------------ #

    def run_exit_evaluation(self, strategy_version: StrategyVersion, as_of_date: date) -> APIResponse:
        """Close any OPEN position past its planned_exit_date, and unwind leftover exposure from FAILED entries."""
        try:
            unwound = self._unwind_failed_positions(strategy_version, as_of_date)

            open_positions = self.position_repo.get_open_and_closing_for_strategy_version(strategy_version.id)
            exited, still_open = [], []

            for position in open_positions:
                if as_of_date < position.planned_exit_date:
                    still_open.append(position.id)
                    continue
                if self._close_position(position, as_of_date):
                    exited.append({ "options_position_id": position.id, "exit_reason": position.exit_reason.value })
                else:
                    still_open.append(position.id)

            return APIResponse(success=True, message="OPTIONS_EXIT_COMPLETED", data={ "positions_evaluated": len(open_positions), "exited": exited, "still_open": still_open, "unwound_failed": unwound })
        except Exception as exc:
            logger.error(f"Options exit evaluation failed for strategy version {strategy_version.id}: {exc}", exc_info=True)
            return APIResponse(success=False, message=str(exc))

    def _close_position(self, position: OptionsPosition, as_of_date: date) -> bool:
        if position.status != OptionsPositionStatus.CLOSING:
            self.position_repo.update(position, { "status": OptionsPositionStatus.CLOSING })

        legs = { leg.role: leg for leg in self.leg_repo.get_for_position(position.id) }

        shorts_closed = self._close_legs([legs[r] for r in SHORT_ROLES if r in legs], as_of_date)
        if not shorts_closed:
            logger.warning(f"Options position {position.id}: could not close short legs — will retry next exit-job tick.")
            return False

        longs_closed = self._close_legs([legs[r] for r in LONG_ROLES if r in legs], as_of_date)
        if not longs_closed:
            logger.warning(f"Options position {position.id}: shorts closed, long legs still open — will retry next exit-job tick.")
            return False

        exit_reason = OptionsExitReason.TIME_EXIT if position.planned_exit_date < position.expiry_date else OptionsExitReason.EXPIRY_EXIT
        self.position_repo.update(position, { "status": OptionsPositionStatus.CLOSED, "exit_date": as_of_date, "exit_reason": exit_reason })
        logger.info(f"Options position {position.id} CLOSED — reason={exit_reason.value}")
        return True

    def _unwind_failed_positions(self, strategy_version: StrategyVersion, as_of_date: date) -> list[int]:
        """Flatten any leftover filled legs from FAILED entries — those were never meant to carry real exposure."""
        failed_positions = (
            self.db.query(OptionsPosition)
            .filter(OptionsPosition.strategy_version_id == strategy_version.id, OptionsPosition.status == OptionsPositionStatus.FAILED)
            .all()
        )

        unwound = []
        for position in failed_positions:
            legs = self.leg_repo.get_for_position(position.id)
            if not any(leg.status == OptionsLegStatus.OPEN for leg in legs):
                continue

            if self._close_legs(legs, as_of_date):
                self.position_repo.update(position, { "status": OptionsPositionStatus.CLOSED, "exit_date": as_of_date, "skip_reason": f"{position.skip_reason or ''} | unwound after failed entry".strip(" |") })
                unwound.append(position.id)
                logger.warning(f"Unwound leftover exposure from FAILED options position {position.id}.")
            else:
                logger.warning(f"Options position {position.id} (FAILED) still has unclosed legs — will retry unwind next exit-job tick.")

        return unwound

    # ------------------------------------------------------------------ #
    #  Order placement / fill polling (shared entry + exit machinery)     #
    # ------------------------------------------------------------------ #

    def _fill_legs(self, legs: list[OptionsLeg], transaction_map: dict, quantity: int, is_entry: bool) -> bool:
        """Place (if needed) and confirm fills for a set of legs. Returns True iff all are OPEN afterward.

        Idempotent: a leg with an order id already recorded is only polled, never re-ordered. A leg
        that still isn't filled after the in-line retry loop stays PENDING with its order id recorded —
        the next entry-job tick (idempotent by the same check) picks up polling where this left off,
        rather than placing a second order.
        """
        all_filled = True
        for leg in legs:
            if leg.status == OptionsLegStatus.OPEN:
                continue
            if not leg.kite_entry_order_id:
                self._place_leg_order(leg, transaction_map[leg.role], quantity)
            if leg.kite_entry_order_id and leg.status != OptionsLegStatus.OPEN:
                self._poll_and_record_entry_fill(leg)
            if leg.status != OptionsLegStatus.OPEN:
                all_filled = False
        return all_filled

    def _place_leg_order(self, leg: OptionsLeg, transaction_type: str, quantity: int) -> None:
        security = leg.security
        try:
            quote = self.kite_service.get_quotes([f"{KITE_EXCHANGE}:{security.ticker}"])
            ltp = quote[f"{KITE_EXCHANGE}:{security.ticker}"]["last_price"]
        except Exception:
            logger.error(f"Could not fetch LTP for {security.ticker} before placing {transaction_type} order (leg {leg.id}) — leaving PENDING.", exc_info=True)
            return

        price = self._round_to_tick(ltp * ORDER_BUFFERS[transaction_type], security.tick_size)

        try:
            order_id = self.kite_service.place_order(variety="regular", exchange=KITE_EXCHANGE, tradingsymbol=security.ticker, transaction_type=transaction_type, quantity=quantity, product=KITE_PRODUCT, order_type="LIMIT", price=price)
        except Exception:
            logger.error(f"Failed to place {transaction_type} order for {security.ticker} (leg {leg.id}) — leaving PENDING for retry.", exc_info=True)
            return

        self.leg_repo.update(leg, { "kite_entry_order_id": str(order_id) })
        logger.info(f"Placed {transaction_type} order for {security.ticker} qty={quantity} price={price} order_id={order_id} (leg {leg.id}, role={leg.role.value})")

    def _poll_and_record_entry_fill(self, leg: OptionsLeg, attempts: int = 6, delay_seconds: int = 5) -> None:
        """Poll for fill confirmation with a short in-line retry loop (marketable limit orders on a
        liquid weekly chain should fill within seconds); a leg still unfilled after this stays PENDING
        for the next job tick to pick up, rather than blocking the whole entry indefinitely.
        """
        for attempt in range(attempts):
            time.sleep(delay_seconds)
            try:
                trades = self.kite_service.get_order_trades(leg.kite_entry_order_id)
            except Exception:
                logger.error(f"Error polling entry fill for leg {leg.id} order {leg.kite_entry_order_id} (attempt {attempt + 1}).", exc_info=True)
                continue
            if not trades:
                continue

            fill_quantity = sum(t["quantity"] for t in trades)
            fill_price = round(sum(t["average_price"] * t["quantity"] for t in trades) / fill_quantity, 4)
            self.leg_repo.update(leg, { "status": OptionsLegStatus.OPEN, "entry_fill_price": fill_price, "entry_fill_quantity": fill_quantity, "entry_date": date.today() })
            logger.info(f"Leg {leg.id} entry filled: price={fill_price}, qty={fill_quantity}")
            return

        logger.warning(f"Entry fill not confirmed for leg {leg.id} order {leg.kite_entry_order_id} after {attempts} attempts — leaving PENDING for next job tick.")

    def _close_legs(self, legs: list[OptionsLeg], as_of_date: date) -> bool:
        """Place (if needed) and poll closing fills for a set of legs. Returns True iff all are CLOSED afterward.

        Legs never filled at entry (status != OPEN) have nothing to close and are skipped.
        """
        all_closed = True
        for leg in legs:
            if leg.status != OptionsLegStatus.OPEN:
                continue
            if not leg.kite_exit_order_id:
                self._place_leg_close_order(leg)
            if leg.kite_exit_order_id and leg.status != OptionsLegStatus.CLOSED:
                self._poll_and_record_close_fill(leg, as_of_date)
            if leg.status != OptionsLegStatus.CLOSED:
                all_closed = False
        return all_closed

    def _place_leg_close_order(self, leg: OptionsLeg) -> None:
        security = leg.security
        transaction_type = CLOSE_TRANSACTION[leg.role]
        quantity = leg.entry_fill_quantity

        try:
            quote = self.kite_service.get_quotes([f"{KITE_EXCHANGE}:{security.ticker}"])
            ltp = quote[f"{KITE_EXCHANGE}:{security.ticker}"]["last_price"]
        except Exception:
            logger.error(f"Could not fetch LTP for {security.ticker} before closing leg {leg.id} — leaving OPEN for retry.", exc_info=True)
            return

        price = self._round_to_tick(ltp * ORDER_BUFFERS[transaction_type], security.tick_size)

        try:
            order_id = self.kite_service.place_order(variety="regular", exchange=KITE_EXCHANGE, tradingsymbol=security.ticker, transaction_type=transaction_type, quantity=quantity, product=KITE_PRODUCT, order_type="LIMIT", price=price)
        except Exception:
            logger.error(f"Failed to place closing {transaction_type} order for {security.ticker} (leg {leg.id}) — leaving OPEN for retry.", exc_info=True)
            return

        self.leg_repo.update(leg, { "kite_exit_order_id": str(order_id) })
        logger.info(f"Placed closing {transaction_type} order for {security.ticker} qty={quantity} price={price} order_id={order_id} (leg {leg.id})")

    def _poll_and_record_close_fill(self, leg: OptionsLeg, as_of_date: date, attempts: int = 6, delay_seconds: int = 5) -> None:
        for attempt in range(attempts):
            time.sleep(delay_seconds)
            try:
                trades = self.kite_service.get_order_trades(leg.kite_exit_order_id)
            except Exception:
                logger.error(f"Error polling close fill for leg {leg.id} order {leg.kite_exit_order_id} (attempt {attempt + 1}).", exc_info=True)
                continue
            if not trades:
                continue

            fill_quantity = sum(t["quantity"] for t in trades)
            fill_price = round(sum(t["average_price"] * t["quantity"] for t in trades) / fill_quantity, 4)
            self.leg_repo.update(leg, { "status": OptionsLegStatus.CLOSED, "exit_fill_price": fill_price, "exit_fill_quantity": fill_quantity, "exit_date": as_of_date })
            logger.info(f"Leg {leg.id} exit filled: price={fill_price}, qty={fill_quantity}")
            return

        logger.warning(f"Exit fill not confirmed for leg {leg.id} order {leg.kite_exit_order_id} after {attempts} attempts — leaving OPEN for next job tick.")

    # ------------------------------------------------------------------ #
    #  Helpers                                                            #
    # ------------------------------------------------------------------ #

    def _round_to_tick(self, price: float, tick_size) -> float:
        if not tick_size:
            return round(price, 2)
        ticks = round(price / float(tick_size))
        return round(ticks * float(tick_size), 2)

    def _position_summary(self, position: OptionsPosition) -> dict:
        legs = self.leg_repo.get_for_position(position.id)
        return {
            "options_position_id": position.id,
            "lots": position.lots,
            "lot_size": position.lot_size,
            "expiry_date": str(position.expiry_date),
            "strikes": { "call_short": float(position.call_short_strike), "put_short": float(position.put_short_strike), "call_long": float(position.call_long_strike), "put_long": float(position.put_long_strike) },
            "net_credit_per_lot": float(position.net_credit_per_lot) if position.net_credit_per_lot is not None else None,
            "margin_per_lot": float(position.margin_per_lot) if position.margin_per_lot is not None else None,
            "planned_exit_date": str(position.planned_exit_date),
            "legs": [{ "role": leg.role.value, "ticker": leg.security.ticker, "fill_price": float(leg.entry_fill_price) if leg.entry_fill_price else None, "status": leg.status.value } for leg in legs],
        }
