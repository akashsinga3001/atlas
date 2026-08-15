# backend/app/services/options_trade.py

import time
from datetime import date
from sqlalchemy.orm import Session
from typing import Callable, Optional

from app.enums.options import OptionsPositionStatus, OptionsLegRole, OptionsLegStatus, OptionsExitReason
from app.enums.strategy import StrategyRunStatus
from app.models.security import Security
from app.models.strategy import StrategyRun, StrategySignal, StrategyVersion
from app.models.options import OptionsPosition, OptionsLeg
from app.repositories.options import OptionsPositionRepository, OptionsLegRepository
from app.repositories.security import SecurityRepository
from app.repositories.kill_switch import KillSwitchRepository
from app.schemas.base import APIResponse
from app.schemas.options import OptionsLegResponse, OptionsPositionResponse
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
ORDER_BUFFERS = { "BUY": 1.02, "SELL": 0.98 }

LONG_ROLES = [OptionsLegRole.LONG_CALL, OptionsLegRole.LONG_PUT]
SHORT_ROLES = [OptionsLegRole.SHORT_CALL, OptionsLegRole.SHORT_PUT]

# Entry: BUY the protective wings first, then SELL the short strikes — at every
# intermediate step exposure is long-only (bounded risk), never short-naked.
ENTRY_TRANSACTION = {OptionsLegRole.LONG_CALL: "BUY", OptionsLegRole.LONG_PUT: "BUY", OptionsLegRole.SHORT_CALL: "SELL", OptionsLegRole.SHORT_PUT: "SELL", }
# Exit: buy back the shorts first (removes the uncapped side), then sell the longs —
# mirrors entry ordering for the same reason.
CLOSE_TRANSACTION = {OptionsLegRole.LONG_CALL: "SELL", OptionsLegRole.LONG_PUT: "SELL", OptionsLegRole.SHORT_CALL: "BUY", OptionsLegRole.SHORT_PUT: "BUY", }


class OptionsTradeService:
    """Parallel-to-TradeService engine for the 4-leg NIFTY iron condor.

    Built fresh rather than routed through TradeService.open_trade() — that engine assumes
    a single BUY-to-open leg with a GTT stop, which doesn't fit simultaneous multi-leg entry,
    short-leg semantics, or a defined-risk-by-construction exit. Follows the same layering
    conventions (service -> repository -> model, same error handling/logging style) instead.
    """

    def __init__(self, db: Session, kite_service: KiteService = None):
        """Initialise repositories and sub-services; kite_service is optional for read-only use."""
        self.db = db
        self.kite_service = kite_service
        self.position_repo = OptionsPositionRepository(db)
        self.leg_repo = OptionsLegRepository(db)
        self.security_repo = SecurityRepository(db)
        if kite_service:
            self.portfolio_service = PortfolioService(db, kite_service)

    # ------------------------------------------------------------------ #
    #  Position Listing                                                   #
    # ------------------------------------------------------------------ #

    def get_positions(self, status: Optional[OptionsPositionStatus] = None) -> list[dict]:
        """Return all options positions, optionally filtered by status, as serialisable dicts."""
        positions = self.position_repo.get_all_positions(status=status)
        return [self._build_position_response(p) for p in positions]

    def _build_position_response(self, position: OptionsPosition) -> dict:
        """Serialise a position and its legs, including realized P&L once closed, to a dict."""
        legs = self.leg_repo.get_for_position(position.id)
        margin_total = float(position.margin_per_lot) * position.lots if position.margin_per_lot is not None and position.lots else None
        net_credit_total = float(position.net_credit_per_lot) * position.lots * position.lot_size if position.net_credit_per_lot is not None and position.lots and position.lot_size else None
        realized_pnl = self._compute_realized_pnl(legs) if position.status == OptionsPositionStatus.CLOSED else None

        return OptionsPositionResponse(
            id=position.id, status=position.status, signal_date=position.signal_date, entry_date=position.entry_date, spot_at_signal=float(position.spot_at_signal), expiry_date=position.expiry_date, call_short_strike=float(position.call_short_strike) if position.call_short_strike is not None else None, put_short_strike=float(position.put_short_strike) if position.put_short_strike is not None else None,
            call_long_strike=float(position.call_long_strike) if position.call_long_strike is not None else None, put_long_strike=float(position.put_long_strike) if position.put_long_strike is not None else None, lots=position.lots, lot_size=position.lot_size, margin_per_lot=float(position.margin_per_lot) if position.margin_per_lot is not None else None, net_credit_per_lot=float(position.net_credit_per_lot) if position.net_credit_per_lot is not None else None, margin_total=margin_total,
            net_credit_total=net_credit_total, planned_exit_date=position.planned_exit_date, exit_date=position.exit_date, exit_reason=position.exit_reason, skip_reason=position.skip_reason, realized_pnl=realized_pnl, legs=[self._build_leg_response(leg) for leg in legs],
        ).model_dump()

    def _build_leg_response(self, leg: OptionsLeg) -> OptionsLegResponse:
        """Serialise a single leg, including its contract's strike/right, to a response model."""
        return OptionsLegResponse(id=leg.id, role=leg.role, status=leg.status, ticker=leg.security.ticker, strike=float(leg.security.strike) if leg.security.strike is not None else None, option_type=leg.security.option_type, entry_fill_price=float(leg.entry_fill_price) if leg.entry_fill_price is not None else None, entry_fill_quantity=leg.entry_fill_quantity, exit_fill_price=float(leg.exit_fill_price) if leg.exit_fill_price is not None else None, exit_fill_quantity=leg.exit_fill_quantity, )

    def _compute_realized_pnl(self, legs: list[OptionsLeg]) -> Optional[float]:
        """Sum each leg's realized P&L — short legs profit when bought back cheaper, long legs when sold dearer."""
        total = 0.0
        for leg in legs:
            if leg.entry_fill_price is None or leg.exit_fill_price is None or not leg.entry_fill_quantity:
                return None
            entry, exit_price, qty = float(leg.entry_fill_price), float(leg.exit_fill_price), leg.entry_fill_quantity
            total += (entry - exit_price) * qty if leg.role in SHORT_ROLES else (exit_price - entry) * qty
        return round(total, 2)

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

            if KillSwitchRepository(self.db).get_singleton().enabled:
                return APIResponse(success=True, message="KILL_SWITCH_ACTIVE", data={})

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
        latest_run = (self.db.query(StrategyRun).filter(StrategyRun.strategy_version_id == strategy_version.id, StrategyRun.status == StrategyRunStatus.COMPLETED).order_by(StrategyRun.id.desc()).first())
        if not latest_run or not latest_run.signals:
            return None

        signal = latest_run.signals[0]
        signal_date = signal.observed_at.date()

        if next_nse_trading_day(signal_date) != as_of_date:
            return None
        return signal

    def _enter_from_signal(self, signal: StrategySignal, strategy_version: StrategyVersion, as_of_date: date) -> APIResponse:
        """Resolve strikes/contracts/pricing/sizing for the week's condor, persist it, and place entry orders."""
        config = strategy_version.config
        spot = float(signal.payload["spot_close"])

        expiry = self._resolve_expiry(config, as_of_date)
        if not expiry:
            return self._skip(signal, strategy_version, as_of_date, spot, "no expiry available in the option chain")

        strikes = self._compute_strikes(spot, config)

        contracts, reason = self._resolve_contracts(config, expiry, strikes)
        if not contracts:
            return self._skip(signal, strategy_version, as_of_date, spot, reason)
        lot_size = next(iter(contracts.values())).lot_size

        ltps, reason = self._price_legs(contracts)
        if not ltps:
            return self._skip(signal, strategy_version, as_of_date, spot, reason)

        lots, margin_per_lot, net_credit_per_lot, reason = self._size_position(strategy_version, config, ltps, strikes, lot_size)
        if lots is None:
            return self._skip(signal, strategy_version, as_of_date, spot, reason)

        position = self._persist_position(signal, strategy_version, as_of_date, spot, expiry, strikes, lots, lot_size, margin_per_lot, net_credit_per_lot, contracts)
        return self._place_entry_orders(position)

    def _compute_strikes(self, spot: float, config: dict) -> dict[OptionsLegRole, tuple[float, str]]:
        """Compute each leg's strike (rounded to the configured step) and option right from spot."""
        step = config["strike_step"]
        call_short = self._round_to_step(spot * (1 + config["short_otm_pct"]), step)
        put_short = self._round_to_step(spot * (1 - config["short_otm_pct"]), step)
        call_long = self._round_to_step(spot * (1 + config["long_otm_pct"]), step)
        put_long = self._round_to_step(spot * (1 - config["long_otm_pct"]), step)

        return {OptionsLegRole.SHORT_CALL: (call_short, "CE"), OptionsLegRole.SHORT_PUT: (put_short, "PE"), OptionsLegRole.LONG_CALL: (call_long, "CE"), OptionsLegRole.LONG_PUT: (put_long, "PE"), }

    def _resolve_contracts(self, config: dict, expiry: date, strikes: dict[OptionsLegRole, tuple[float, str]]) -> tuple[Optional[dict[OptionsLegRole, Security]], Optional[str]]:
        """Look up the Security row for each leg's strike/right; returns (contracts, None) or (None, skip reason)."""
        contracts: dict[OptionsLegRole, Security] = {}
        for role, (strike, right) in strikes.items():
            sec = self._find_contract(config, expiry, strike, right)
            if not sec:
                return None, f"contract not found: {role.value} strike={strike} {right} expiry={expiry}"
            contracts[role] = sec

        lot_sizes = {sec.lot_size for sec in contracts.values()}
        if len(lot_sizes) != 1 or None in lot_sizes:
            return None, f"inconsistent/missing lot size across legs: {lot_sizes}"

        return contracts, None

    def _price_legs(self, contracts: dict[OptionsLegRole, Security]) -> tuple[Optional[dict[OptionsLegRole, float]], Optional[str]]:
        """Fetch live quotes for each leg; returns (ltps, None) or (None, skip reason)."""
        try:
            quotes = self.kite_service.get_quotes([ f"{KITE_EXCHANGE}:{sec.ticker}" for sec in contracts.values() ])
        except Exception:
            logger.error("Failed to fetch entry-leg quotes.", exc_info=True)
            return None, "failed to fetch leg quotes"

        ltps: dict[OptionsLegRole, float] = {}
        for role, sec in contracts.items():
            quote = quotes.get(f"{KITE_EXCHANGE}:{sec.ticker}")
            ltp = quote["last_price"] if quote else 0
            if not ltp or ltp <= 0:
                return None, f"leg not tradable: {sec.ticker}"
            ltps[role] = float(ltp)

        return ltps, None

    def _size_position(self, strategy_version: StrategyVersion, config: dict, ltps: dict[OptionsLegRole, float], strikes: dict[OptionsLegRole, tuple[float, str]], lot_size: int) -> tuple[Optional[int], float, float, Optional[str]]:
        """Compute margin/lot and net credit/lot from live leg prices, then size lots to isolated capital."""
        call_short, put_short = strikes[OptionsLegRole.SHORT_CALL][0], strikes[OptionsLegRole.SHORT_PUT][0]
        call_long, put_long = strikes[OptionsLegRole.LONG_CALL][0], strikes[OptionsLegRole.LONG_PUT][0]

        net_credit_per_lot = (ltps[OptionsLegRole.SHORT_CALL] + ltps[OptionsLegRole.SHORT_PUT]) - (ltps[OptionsLegRole.LONG_CALL] + ltps[OptionsLegRole.LONG_PUT])
        max_wing_width = max(call_long - call_short, put_short - put_long)
        margin_per_lot = max_wing_width * lot_size - net_credit_per_lot * lot_size

        if margin_per_lot <= 0:
            return None, margin_per_lot, net_credit_per_lot, f"non-positive margin_per_lot ({margin_per_lot}) — refusing to size"

        capital = self.portfolio_service.get_isolated_account_size(strategy_version)
        lots = min(int(capital * config["capital_pct"] // margin_per_lot), config["max_lots"])

        if lots < 1:
            return None, margin_per_lot, net_credit_per_lot, f"position size rounds to 0 lots (capital={capital:.2f}, margin_per_lot={margin_per_lot:.2f})"

        return lots, margin_per_lot, net_credit_per_lot, None

    def _persist_position(self, signal: StrategySignal, strategy_version: StrategyVersion, as_of_date: date, spot: float, expiry: date, strikes: dict[OptionsLegRole, tuple[float, str]], lots: int, lot_size: int, margin_per_lot: float, net_credit_per_lot: float, contracts: dict[OptionsLegRole, Security]) -> OptionsPosition:
        """Persist the PENDING position and its 4 legs in a single transaction (flush for the FK, one commit)."""
        call_short, put_short = strikes[OptionsLegRole.SHORT_CALL][0], strikes[OptionsLegRole.SHORT_PUT][0]
        call_long, put_long = strikes[OptionsLegRole.LONG_CALL][0], strikes[OptionsLegRole.LONG_PUT][0]
        planned_exit_date = min(add_nse_trading_days(as_of_date, strategy_version.config["hold_days"]), expiry)

        position = OptionsPosition(strategy_signal_id=signal.id, strategy_version_id=strategy_version.id, signal_date=signal.observed_at.date(), entry_date=as_of_date, spot_at_signal=spot, expiry_date=expiry, call_short_strike=call_short, put_short_strike=put_short, call_long_strike=call_long, put_long_strike=put_long, lots=lots, lot_size=lot_size, margin_per_lot=margin_per_lot, net_credit_per_lot=net_credit_per_lot, status=OptionsPositionStatus.PENDING, planned_exit_date=planned_exit_date, )
        self.db.add(position)
        self.db.flush()  # assigns position.id for the legs' FK, without committing yet

        for role, sec in contracts.items():
            self.db.add(OptionsLeg(options_position_id=position.id, security_id=sec.id, role=role, status=OptionsLegStatus.PENDING))
        self.db.commit()
        self.db.refresh(position)

        logger.info(f"Created PENDING options position {position.id}: {lots} lots, expiry={expiry}, "
                    f"short C{call_short}/P{put_short}, long C{call_long}/P{put_long}, margin/lot={margin_per_lot:.2f}")
        return position

    def _skip(self, signal: StrategySignal, strategy_version: StrategyVersion, as_of_date: date, spot: float, reason: str) -> APIResponse:
        """Record a SKIPPED position (no legs) so this signal is never retried, and return the reason."""
        logger.warning(f"Skipping iron condor entry for signal {signal.id}: {reason}")
        position = OptionsPosition(strategy_signal_id=signal.id, strategy_version_id=strategy_version.id, signal_date=signal.observed_at.date(), entry_date=as_of_date, spot_at_signal=spot, status=OptionsPositionStatus.SKIPPED, skip_reason=reason, )
        self.db.add(position)
        self.db.commit()
        return APIResponse(success=True, message="ENTRY_SKIPPED", data={ "reason": reason })

    def _resolve_expiry(self, config: dict, as_of_date: date) -> Optional[date]:
        """Nearest expiry strictly after as_of_date among expiries actually listed in the local option chain."""
        option_name = config.get("option_name", "NIFTY")
        return self.security_repo.get_nearest_option_expiry(option_name, as_of_date)

    def _find_contract(self, config: dict, expiry: date, strike: float, right: str) -> Optional[Security]:
        """Look up a single option contract Security row by underlying, expiry, strike, and right."""
        option_name = config.get("option_name", "NIFTY")
        return self.security_repo.get_option_contract(option_name, expiry, strike, right)

    def _place_entry_orders(self, position: OptionsPosition) -> APIResponse:
        """Fill protective long legs first, then short legs; marks OPEN only once all 4 legs are filled."""
        legs = {leg.role: leg for leg in self.leg_repo.get_for_position(position.id)}

        missing = [role.value for role in (*LONG_ROLES, *SHORT_ROLES) if role not in legs]
        if missing:
            self.position_repo.update(position, { "status": OptionsPositionStatus.FAILED })
            logger.error(f"Options position {position.id} FAILED — missing leg roles at persistence: {missing}.")
            return APIResponse(success=False, message="ENTRY_FAILED_MISSING_LEGS", data={ "options_position_id": position.id, "missing_roles": missing })

        longs_ok = self._fill_legs([legs[r] for r in LONG_ROLES], ENTRY_TRANSACTION, position.lots * position.lot_size)
        if not longs_ok:
            self.position_repo.update(position, { "status": OptionsPositionStatus.FAILED })
            logger.error(f"Options position {position.id} FAILED — could not establish protective long legs.")
            return APIResponse(success=False, message="ENTRY_FAILED_LONG_LEGS", data={ "options_position_id": position.id })

        shorts_ok = self._fill_legs([legs[r] for r in SHORT_ROLES], ENTRY_TRANSACTION, position.lots * position.lot_size)
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
        """Close short legs first, then long legs; marks CLOSED only once all legs are confirmed closed."""
        if position.status != OptionsPositionStatus.CLOSING:
            self.position_repo.update(position, { "status": OptionsPositionStatus.CLOSING })

        legs = {leg.role: leg for leg in self.leg_repo.get_for_position(position.id)}

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
        failed_positions = (self.db.query(OptionsPosition).filter(OptionsPosition.strategy_version_id == strategy_version.id, OptionsPosition.status == OptionsPositionStatus.FAILED).all())

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

    def _fill_legs(self, legs: list[OptionsLeg], transaction_map: dict, quantity: int) -> bool:
        """Place and confirm entry fills for a set of legs; returns True iff all end up OPEN."""
        for leg in legs:
            if leg.status != OptionsLegStatus.OPEN:
                self._place_and_confirm(leg, side="entry", target_status=OptionsLegStatus.OPEN, fill_date=date.today(), place=lambda l: self._place_leg_order(l, "entry", transaction_map[l.role], quantity))
        return all(leg.status == OptionsLegStatus.OPEN for leg in legs)

    def _close_legs(self, legs: list[OptionsLeg], as_of_date: date) -> bool:
        """Place and confirm closing fills for a set of legs; returns True iff all end up CLOSED."""
        # Legs never filled at entry (status != OPEN) have nothing to close and are left alone.
        for leg in legs:
            if leg.status == OptionsLegStatus.OPEN:
                self._place_and_confirm(leg, side="exit", target_status=OptionsLegStatus.CLOSED, fill_date=as_of_date, place=lambda l: self._place_leg_order(l, "exit", CLOSE_TRANSACTION[l.role], l.entry_fill_quantity))
        return all(leg.status != OptionsLegStatus.OPEN for leg in legs)

    def _place_and_confirm(self, leg: OptionsLeg, side: str, target_status: OptionsLegStatus, fill_date: date, place: Callable[[OptionsLeg], None]) -> None:
        """Shared place -> poll -> reprice-and-retry-once cascade for a single entry or exit leg fill."""
        # Idempotent: a leg with an order id already recorded is only polled, never re-ordered. If the
        # poll below determines that order is actually dead (cancelled/rejected — NSE cancels regular-day
        # LIMIT orders at end of day, so a leg revisited on a later tick could otherwise poll a dead order
        # forever), it clears the order id, and this reprices and places a fresh order once more within
        # the same tick rather than waiting for the next one. A leg still unfilled after that stays as-is
        # for the next job tick to pick up — never a second order while one is still genuinely live.
        order_id_field = f"kite_{side}_order_id"

        if not getattr(leg, order_id_field):
            place(leg)
        if getattr(leg, order_id_field) and leg.status != target_status:
            self._poll_and_record_fill(leg, side, target_status, fill_date)
        if not getattr(leg, order_id_field) and leg.status != target_status:
            place(leg)
            if getattr(leg, order_id_field) and leg.status != target_status:
                self._poll_and_record_fill(leg, side, target_status, fill_date)

    def _place_leg_order(self, leg: OptionsLeg, side: str, transaction_type: str, quantity: int) -> None:
        """Fetch a live quote, price a marketable limit order, and place it for either entry or exit."""
        security = leg.security
        try:
            quote = self.kite_service.get_quotes([f"{KITE_EXCHANGE}:{security.ticker}"])
            ltp = quote[f"{KITE_EXCHANGE}:{security.ticker}"]["last_price"]
        except Exception:
            logger.error(f"Could not fetch LTP for {security.ticker} before placing {side} {transaction_type} order (leg {leg.id}) — leaving as-is for retry.", exc_info=True)
            return

        price = self._round_to_tick(ltp * ORDER_BUFFERS[transaction_type], security.tick_size)

        try:
            order_id = self.kite_service.place_order(variety="regular", exchange=KITE_EXCHANGE, tradingsymbol=security.ticker, transaction_type=transaction_type, quantity=quantity, product=KITE_PRODUCT, order_type="LIMIT", price=price)
        except Exception:
            logger.error(f"Failed to place {side} {transaction_type} order for {security.ticker} (leg {leg.id}) — leaving as-is for retry.", exc_info=True)
            return

        self.leg_repo.update(leg, { f"kite_{side}_order_id": str(order_id) })
        logger.info(f"Placed {side} {transaction_type} order for {security.ticker} qty={quantity} price={price} order_id={order_id} (leg {leg.id}, role={leg.role.value})")

    def _poll_and_record_fill(self, leg: OptionsLeg, side: str, target_status: OptionsLegStatus, fill_date: date, attempts: int = 6, delay_seconds: int = 5) -> None:
        """Poll for fill confirmation via a short in-line retry loop, shared by entry and exit legs."""
        # Marketable limit orders on a liquid weekly chain should fill within seconds; a leg still
        # unfilled after this window stays as-is for the next job tick to pick up, rather than
        # blocking the whole entry/exit indefinitely.
        order_id = getattr(leg, f"kite_{side}_order_id")
        price_field, qty_field, date_field = f"{side}_fill_price", f"{side}_fill_quantity", f"{side}_date"

        for attempt in range(attempts):
            time.sleep(delay_seconds)
            try:
                trades = self.kite_service.get_order_trades(order_id)
            except Exception:
                logger.error(f"Error polling {side} fill for leg {leg.id} order {order_id} (attempt {attempt + 1}).", exc_info=True)
                continue
            if not trades:
                continue

            fill_quantity = sum(t["quantity"] for t in trades)
            fill_price = round(sum(t["average_price"] * t["quantity"] for t in trades) / fill_quantity, 4)
            self.leg_repo.update(leg, { "status": target_status, price_field: fill_price, qty_field: fill_quantity, date_field: fill_date })
            logger.info(f"Leg {leg.id} {side} filled: price={fill_price}, qty={fill_quantity}")
            return

        logger.warning(f"{side.capitalize()} fill not confirmed for leg {leg.id} order {order_id} after {attempts} attempts — checking order status.")
        self._reconcile_stale_order(leg, side, target_status, fill_date)

    def _reconcile_stale_order(self, leg: OptionsLeg, side: str, target_status: OptionsLegStatus, fill_date: date) -> None:
        """Check an order's actual exchange status when the fill-trades poll comes up empty, shared by entry and exit legs."""
        # NSE cancels regular-day LIMIT orders at end of day, so a dead order id must not be polled
        # forever, and an order that's actually COMPLETE but missed by the trades poll (a race) must
        # not trigger a duplicate order:
        #  - COMPLETE but missed by the trades poll -> record the fill directly from the order.
        #  - CANCELLED / REJECTED / not found -> clear the order id so the caller reprices and places
        #    a fresh order, instead of polling a dead order id forever.
        #  - still genuinely OPEN on the exchange -> leave it alone, poll again next tick.
        order_id_field = f"kite_{side}_order_id"
        order_id = getattr(leg, order_id_field)
        price_field, qty_field, date_field = f"{side}_fill_price", f"{side}_fill_quantity", f"{side}_date"

        try:
            order = self.kite_service.get_order(order_id)
        except Exception:
            logger.error(f"Could not check status of {side} order {order_id} for leg {leg.id}.", exc_info=True)
            return

        if order is None:
            logger.warning(f"{side.capitalize()} order {order_id} for leg {leg.id} not found by broker — clearing for a fresh attempt.")
            self.leg_repo.update(leg, { order_id_field: None })
            return

        status = (order.get("status") or "").upper()

        if status == "COMPLETE":
            filled_qty = order.get("filled_quantity") or order.get("quantity")
            avg_price = order.get("average_price")
            if filled_qty and avg_price:
                self.leg_repo.update(leg, { "status": target_status, price_field: round(float(avg_price), 4), qty_field: int(filled_qty), date_field: fill_date })
                logger.info(f"Leg {leg.id} {side} order {order_id} was COMPLETE on the broker but missed by the trades poll — recorded directly.")
            else:
                logger.warning(f"{side.capitalize()} order {order_id} for leg {leg.id} shows COMPLETE but has no fill data — leaving for manual review.")
            return

        if status in ("CANCELLED", "REJECTED"):
            logger.warning(f"{side.capitalize()} order {order_id} for leg {leg.id} is {status} — clearing for a fresh attempt at the current price.")
            self.leg_repo.update(leg, { order_id_field: None })
            return

        logger.info(f"{side.capitalize()} order {order_id} for leg {leg.id} is still {status or 'live'} on the exchange — leaving it, will poll again next tick.")

    # ------------------------------------------------------------------ #
    #  Helpers                                                            #
    # ------------------------------------------------------------------ #

    def _round_to_step(self, value: float, step: float) -> float:
        """Round a price to the nearest multiple of the given strike step."""
        return round(value / step) * step

    def _round_to_tick(self, price: float, tick_size) -> float:
        """Round a price to the nearest valid tick size for the instrument."""
        if not tick_size:
            return round(price, 2)
        ticks = round(price / float(tick_size))
        return round(ticks * float(tick_size), 2)

    def _position_summary(self, position: OptionsPosition) -> dict:
        """Serialise a position and its legs into a plain dict for notifications and API responses."""
        legs = self.leg_repo.get_for_position(position.id)
        return {
            "options_position_id": position.id,
            "lots": position.lots,
            "lot_size": position.lot_size,
            "expiry_date": str(position.expiry_date),
            "strikes": {
                "call_short": float(position.call_short_strike),
                "put_short": float(position.put_short_strike),
                "call_long": float(position.call_long_strike),
                "put_long": float(position.put_long_strike)
            },
            "net_credit_per_lot": float(position.net_credit_per_lot) if position.net_credit_per_lot is not None else None,
            "margin_per_lot": float(position.margin_per_lot) if position.margin_per_lot is not None else None,
            "planned_exit_date": str(position.planned_exit_date),
            "legs": [{
                "role": leg.role.value,
                "ticker": leg.security.ticker,
                "fill_price": float(leg.entry_fill_price) if leg.entry_fill_price else None,
                "status": leg.status.value
            } for leg in legs],
        }
