# backend/app/services/options_trade.py

import time
from datetime import date, timedelta
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
from app.utils.options_pricing import estimate_delta
from app.execution_engines.options_iron_condor import logic
from app.utils.trading_calendar import is_nse_trading_day, next_nse_trading_day
from app.utils.logger import get_logger

logger = get_logger(__name__)

KITE_EXCHANGE = "NFO"
KITE_UNDERLYING_EXCHANGE = "NSE"
KITE_PRODUCT = "NRML"

# Marketable-limit buffers, mirroring TradeService's ORDER_BUY_BUFFER/ORDER_SELL_BUFFER
# convention but wider — weekly index option spreads run noticeably wider than the
# liquid NSE equities the 0.2% equity buffer was tuned for.
ORDER_BUFFERS = { "BUY": 1.02, "SELL": 0.98 }

LONG_ROLES = [OptionsLegRole.LONG_CALL, OptionsLegRole.LONG_PUT]
SHORT_ROLES = [OptionsLegRole.SHORT_CALL, OptionsLegRole.SHORT_PUT]
ALL_ROLES = [OptionsLegRole.SHORT_CALL, OptionsLegRole.SHORT_PUT, OptionsLegRole.LONG_CALL, OptionsLegRole.LONG_PUT]

# Entry: BUY the protective wings first, then SELL the short strikes — at every
# intermediate step exposure is long-only (bounded risk), never short-naked.
ENTRY_TRANSACTION = {OptionsLegRole.LONG_CALL: "BUY", OptionsLegRole.LONG_PUT: "BUY", OptionsLegRole.SHORT_CALL: "SELL", OptionsLegRole.SHORT_PUT: "SELL", }
# Exit: buy back the shorts first (removes the uncapped side), then sell the longs —
# mirrors entry ordering for the same reason.
CLOSE_TRANSACTION = {OptionsLegRole.LONG_CALL: "SELL", OptionsLegRole.LONG_PUT: "SELL", OptionsLegRole.SHORT_CALL: "BUY", OptionsLegRole.SHORT_PUT: "BUY", }


class OptionsTradeService:
    """Delta-targeted, VIX-gated 4-leg NIFTY iron condor engine.

    Built fresh rather than routed through TradeService.open_trade() — that engine assumes
    a single BUY-to-open leg with a GTT stop, which doesn't fit simultaneous multi-leg entry,
    short-leg semantics, or a defined-risk-by-construction exit. Follows the same layering
    conventions (service -> repository -> model, same error handling/logging style) instead.

    PAPER TRADING: every strategy_version.config carries live_trading_enabled (default False).
    While False, _place_leg_order still fetches a real live quote to price the fill (never a
    stale price) but simulates the fill locally instead of calling KiteService.place_order —
    no real order ever reaches the broker. Flip live_trading_enabled only via a deliberate,
    reviewed config change.
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
            id=position.id, strategy_id=position.strategy_version.strategy.id, strategy_code=position.strategy_version.strategy.code, strategy_name=position.strategy_version.strategy.name, status=position.status, signal_date=position.signal_date, entry_date=position.entry_date, spot_at_signal=float(position.spot_at_signal), expiry_date=position.expiry_date, call_short_strike=float(position.call_short_strike) if position.call_short_strike is not None else None, put_short_strike=float(position.put_short_strike) if position.put_short_strike is not None else None,
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

    def get_unrealized_pnl(self) -> float:
        """Sum mark-to-market P&L across every OPEN leg of every OPEN position using live LTP quotes."""
        open_positions = self.position_repo.get_all_positions(status=OptionsPositionStatus.OPEN)
        open_legs = [ leg for p in open_positions for leg in self.leg_repo.get_for_position(p.id) if leg.status == OptionsLegStatus.OPEN and leg.entry_fill_price is not None and leg.entry_fill_quantity ]
        if not open_legs:
            return 0.0

        tickers = [ f"{KITE_EXCHANGE}:{leg.security.ticker}" for leg in open_legs ]
        quotes = self.kite_service.get_quotes(tickers)

        unrealized = 0.0
        for leg in open_legs:
            quote = quotes.get(f"{KITE_EXCHANGE}:{leg.security.ticker}")
            if not quote:
                continue
            ltp, entry, qty = quote["last_price"], float(leg.entry_fill_price), leg.entry_fill_quantity
            unrealized += (entry - ltp) * qty if leg.role in SHORT_ROLES else (ltp - entry) * qty
        return unrealized

    def get_closed_positions_pnl(self) -> list[dict]:
        """Return {exit_date, pnl} for every CLOSED position across all strategy versions, for a portfolio-wide P&L walk."""
        positions = self.position_repo.get_all_positions(status=OptionsPositionStatus.CLOSED)
        results = []
        for position in positions:
            pnl = self._compute_realized_pnl(self.leg_repo.get_for_position(position.id))
            if pnl is not None and position.exit_date:
                results.append({ "exit_date": position.exit_date, "pnl": pnl })
        return results

    def get_closed_positions_for_stats(self) -> list[dict]:
        """Return {entry_date, exit_date, pnl, pnl_pct} for every CLOSED position, for portfolio-wide trade-level
        stats (win rate, Sharpe, profit factor, best/worst trade) alongside equity trades.

        pnl_pct is return on capital at risk (margin_per_lot * lots), not on an entry price — an iron
        condor is a credit spread with no price paid, so equity's (exit-entry)/entry basis doesn't apply.
        margin_per_lot holds the real broker margin committed per lot (see _size_position), matching
        how PortfolioService._deployed_amount_for_strategy already treats options capital.
        """
        positions = self.position_repo.get_all_positions(status=OptionsPositionStatus.CLOSED)
        results = []
        for position in positions:
            if not position.exit_date or not position.entry_date:
                continue
            if position.margin_per_lot is None or not position.lots:
                continue
            pnl = self._compute_realized_pnl(self.leg_repo.get_for_position(position.id))
            if pnl is None:
                continue
            capital_base = float(position.margin_per_lot) * position.lots
            if capital_base <= 0:
                continue
            results.append({ "entry_date": position.entry_date, "exit_date": position.exit_date, "pnl": pnl, "pnl_pct": round(pnl / capital_base * 100, 4) })
        return results

    # ------------------------------------------------------------------ #
    #  Entry                                                              #
    # ------------------------------------------------------------------ #

    def run_entry(self, strategy_version: StrategyVersion, as_of_date: date) -> APIResponse:
        """Enter today's iron condor if today is the entry day for a not-yet-consumed signal that passed the VIX gate."""
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

            if self.portfolio_service.get_capital_allocation()["overallocated"]:
                return APIResponse(success=True, message="OVERALLOCATED", data={})

            signal = self._find_entry_signal(strategy_version, as_of_date)
            if not signal:
                return APIResponse(success=True, message="NO_SIGNAL_FOR_TODAY", data={})

            if self.position_repo.get_by_signal_id(signal.id):
                return APIResponse(success=True, message="SIGNAL_ALREADY_CONSUMED", data={})

            if not signal.payload.get("vix_gate_pass"):
                spot = float(signal.payload.get("spot_close") or 0)
                return self._skip(signal, strategy_version, as_of_date, spot, f"VIX gate failed — percentile={signal.payload.get('vix_percentile')} (avoid band is strictly between the configured low/high)")

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
        """Resolve delta-targeted strikes/contracts/pricing/sizing for the condor from LIVE market data, persist it, and place entry orders.

        Deliberately re-fetches spot and every leg's LTP live rather than reusing the signal's
        decision-time payload — a signal generated at yesterday's close must never fill at
        yesterday's price.
        """
        config = strategy_version.config
        fallback_spot = float(signal.payload.get("spot_close") or 0)

        live_spot = self._get_live_price(config.get("underlying_ticker", "NIFTY 50"), KITE_UNDERLYING_EXCHANGE)
        if not live_spot:
            return self._skip(signal, strategy_version, as_of_date, fallback_spot, "failed to fetch live spot at entry time")

        option_name = config.get("option_name", "NIFTY")
        expiries = self.security_repo.get_option_expiries(option_name, as_of_date)
        expiry = logic.select_nearest_dte_expiry(expiries, as_of_date, config["entry_dte_target"])
        if not expiry:
            return self._skip(signal, strategy_version, as_of_date, live_spot, "no expiry available in the option chain")

        dte_years = (expiry - as_of_date).days / 365.0

        strikes, reason = self._select_delta_strikes(config, expiry, live_spot, dte_years)
        if not strikes:
            return self._skip(signal, strategy_version, as_of_date, live_spot, reason)

        contracts, reason = self._resolve_wing_contracts(config, expiry, strikes)
        if not contracts:
            return self._skip(signal, strategy_version, as_of_date, live_spot, reason)
        lot_size = next(iter(contracts.values())).lot_size

        ltps, reason = self._price_legs(contracts)
        if not ltps:
            return self._skip(signal, strategy_version, as_of_date, live_spot, reason)

        net_credit_per_lot = logic.compute_spread_value(ltps[OptionsLegRole.SHORT_CALL], ltps[OptionsLegRole.SHORT_PUT], ltps[OptionsLegRole.LONG_CALL], ltps[OptionsLegRole.LONG_PUT])
        if net_credit_per_lot <= 0:
            return self._skip(signal, strategy_version, as_of_date, live_spot, f"net credit not positive ({net_credit_per_lot:.2f}) — data anomaly, refusing entry")

        lots, margin_per_lot, reason = self._size_position(strategy_version, config, contracts, net_credit_per_lot, lot_size)
        if lots is None:
            return self._skip(signal, strategy_version, as_of_date, live_spot, reason)

        position = self._persist_position(signal, strategy_version, as_of_date, live_spot, expiry, strikes, lots, lot_size, margin_per_lot, net_credit_per_lot, contracts, config)
        return self._place_entry_orders(position)

    def _select_delta_strikes(self, config: dict, expiry: date, spot: float, dte_years: float) -> tuple[Optional[dict[OptionsLegRole, tuple[float, str]]], Optional[str]]:
        """Find the short call/put nearest the target delta (within tolerance) among the live-quoted local
        chain, then derive each protective long strike wing_width_points beyond its short strike."""
        option_name = config.get("option_name", "NIFTY")
        target, tolerance = config["short_delta_target"], config["delta_tolerance"]

        call_candidates = self.security_repo.get_option_contracts_for_expiry(option_name, expiry, "CE")
        put_candidates = self.security_repo.get_option_contracts_for_expiry(option_name, expiry, "PE")
        if not call_candidates or not put_candidates:
            return None, f"no listed contracts for expiry {expiry}"

        try:
            quotes = self.kite_service.get_quotes([f"{KITE_EXCHANGE}:{sec.ticker}" for sec in (*call_candidates, *put_candidates)])
        except Exception:
            logger.error("Failed to fetch option-chain quotes for delta selection.", exc_info=True)
            return None, "failed to fetch option-chain quotes for delta selection"

        call_short_strike = self._nearest_delta_strike(call_candidates, quotes, "CE", spot, dte_years, config["risk_free_rate"], target, tolerance)
        put_short_strike = self._nearest_delta_strike(put_candidates, quotes, "PE", spot, dte_years, config["risk_free_rate"], target, tolerance)
        if call_short_strike is None or put_short_strike is None:
            return None, f"no strike within delta tolerance on {'both sides' if call_short_strike is None and put_short_strike is None else ('call side' if call_short_strike is None else 'put side')}"

        wing_width = config["wing_width_points"]
        call_long_strike = logic.compute_wing_strike(call_short_strike, wing_width, "CE")
        put_long_strike = logic.compute_wing_strike(put_short_strike, wing_width, "PE")

        return {
            OptionsLegRole.SHORT_CALL: (call_short_strike, "CE"), OptionsLegRole.SHORT_PUT: (put_short_strike, "PE"),
            OptionsLegRole.LONG_CALL: (call_long_strike, "CE"), OptionsLegRole.LONG_PUT: (put_long_strike, "PE"),
        }, None

    def _nearest_delta_strike(self, candidates: list[Security], quotes: dict, right: str, spot: float, dte_years: float, rate: float, target: float, tolerance: float) -> Optional[float]:
        """Score every listed contract's |delta| via IV-solve-then-BS-delta from its live LTP, and pick
        the strike nearest target within tolerance. Contracts with no usable quote or unsolvable IV
        are simply excluded from scoring, not treated as a hard failure."""
        scored: list[tuple[float, float]] = []
        for sec in candidates:
            quote = quotes.get(f"{KITE_EXCHANGE}:{sec.ticker}")
            ltp = quote["last_price"] if quote else None
            if not ltp or ltp <= 0:
                continue
            delta = estimate_delta(ltp, spot, float(sec.strike), dte_years, rate, right)
            if delta is None:
                continue
            scored.append((float(sec.strike), abs(delta)))
        return logic.select_delta_target_strike(scored, target, tolerance)

    def _resolve_wing_contracts(self, config: dict, expiry: date, strikes: dict[OptionsLegRole, tuple[float, str]]) -> tuple[Optional[dict[OptionsLegRole, Security]], Optional[str]]:
        """Look up the Security row for each leg's strike/right; returns (contracts, None) or (None, skip reason)."""
        option_name = config.get("option_name", "NIFTY")
        contracts: dict[OptionsLegRole, Security] = {}
        for role, (strike, right) in strikes.items():
            sec = self.security_repo.get_option_contract(option_name, expiry, strike, right)
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

    def _size_position(self, strategy_version: StrategyVersion, config: dict, contracts: dict[OptionsLegRole, Security], net_credit_per_lot: float, lot_size: int) -> tuple[Optional[int], Optional[float], Optional[str]]:
        """Size by real broker margin: lots that fit inside CURRENT isolated equity given the real
        SPAN+exposure margin Kite would require for one lot of this exact 4-leg basket (hedge
        benefit applied), floored and hard-capped at max_lots. No risk-fraction cap — capital and
        real margin are the only inputs."""
        max_loss_per_lot = logic.compute_max_loss_per_lot(config["wing_width_points"], net_credit_per_lot, lot_size)

        margin_per_lot = self._get_basket_margin_per_lot(contracts, lot_size)
        if margin_per_lot is None:
            return None, None, "failed to fetch real broker margin for the basket"
        if margin_per_lot <= 0:
            return None, None, f"non-positive broker margin per lot ({margin_per_lot:.2f}) — refusing to size"

        capital = self.portfolio_service.get_isolated_account_size(strategy_version)
        lots = logic.compute_position_size(capital, margin_per_lot, config["max_lots"])

        if lots < 1:
            return None, None, f"position size rounds to 0 lots (capital={capital:.2f}, margin_per_lot={margin_per_lot:.2f})"

        logger.info(f"Entry sizing: capital={capital:.2f}, real_margin_per_lot={margin_per_lot:.2f}, max_loss_per_lot(informational)={max_loss_per_lot:.2f}, lots={lots}")
        return lots, margin_per_lot, None

    def _get_basket_margin_per_lot(self, contracts: dict[OptionsLegRole, Security], lot_size: int) -> Optional[float]:
        """Real SPAN+exposure margin for one lot of the 4-leg basket together, hedge benefit applied."""
        orders = [{
            "exchange": KITE_EXCHANGE, "tradingsymbol": sec.ticker, "transaction_type": ENTRY_TRANSACTION[role],
            "variety": "regular", "product": KITE_PRODUCT, "order_type": "MARKET", "quantity": lot_size,
        } for role, sec in contracts.items()]

        try:
            return self.kite_service.get_basket_order_margins(orders)
        except Exception:
            logger.error("Failed to fetch basket order margins for sizing.", exc_info=True)
            return None

    def _persist_position(self, signal: StrategySignal, strategy_version: StrategyVersion, as_of_date: date, live_spot: float, expiry: date, strikes: dict[OptionsLegRole, tuple[float, str]], lots: int, lot_size: int, margin_per_lot: float, net_credit_per_lot: float, contracts: dict[OptionsLegRole, Security], config: dict) -> OptionsPosition:
        """Persist the PENDING position and its 4 legs in a single transaction (flush for the FK, one commit).

        spot_at_signal is recorded as the LIVE spot fetched at entry time, not the signal's stale
        decision-time value — strikes/sizing were computed against this same live price.
        margin_per_lot now holds the REAL broker (Kite basket) margin per lot used for sizing —
        no longer a self-defined max-loss figure, see _size_position/_get_basket_margin_per_lot.
        planned_exit_date is informational only (expiry minus time_exit_dte) — the actual exit
        decision is re-evaluated daily in priority order, see run_exit_evaluation.
        """
        call_short, put_short = strikes[OptionsLegRole.SHORT_CALL][0], strikes[OptionsLegRole.SHORT_PUT][0]
        call_long, put_long = strikes[OptionsLegRole.LONG_CALL][0], strikes[OptionsLegRole.LONG_PUT][0]
        planned_exit_date = expiry - timedelta(days=config["time_exit_dte"])

        position = OptionsPosition(strategy_signal_id=signal.id, strategy_version_id=strategy_version.id, signal_date=signal.observed_at.date(), entry_date=as_of_date, spot_at_signal=live_spot, expiry_date=expiry, call_short_strike=call_short, put_short_strike=put_short, call_long_strike=call_long, put_long_strike=put_long, lots=lots, lot_size=lot_size, margin_per_lot=margin_per_lot, net_credit_per_lot=net_credit_per_lot, status=OptionsPositionStatus.PENDING, planned_exit_date=planned_exit_date, )
        self.db.add(position)
        self.db.flush()  # assigns position.id for the legs' FK, without committing yet

        for role, sec in contracts.items():
            self.db.add(OptionsLeg(options_position_id=position.id, security_id=sec.id, role=role, status=OptionsLegStatus.PENDING))
        self.db.commit()
        self.db.refresh(position)

        logger.info(f"Created PENDING options position {position.id}: {lots} lots, expiry={expiry}, "
                    f"short C{call_short}/P{put_short}, long C{call_long}/P{put_long}, net_credit/lot={net_credit_per_lot:.2f}, margin/lot={margin_per_lot:.2f}")
        return position

    def _skip(self, signal: StrategySignal, strategy_version: StrategyVersion, as_of_date: date, spot: float, reason: str) -> APIResponse:
        """Record a SKIPPED position (no legs) so this signal is never retried, and return the reason."""
        logger.warning(f"Skipping iron condor entry for signal {signal.id}: {reason}")
        position = OptionsPosition(strategy_signal_id=signal.id, strategy_version_id=strategy_version.id, signal_date=signal.observed_at.date(), entry_date=as_of_date, spot_at_signal=spot, status=OptionsPositionStatus.SKIPPED, skip_reason=reason, )
        self.db.add(position)
        self.db.commit()
        return APIResponse(success=True, message="ENTRY_SKIPPED", data={ "reason": reason })

    def _get_live_price(self, ticker: str, exchange: str) -> Optional[float]:
        """Fetch a single live LTP via Kite; returns None (never raises) so callers can skip cleanly."""
        try:
            quote = self.kite_service.get_quotes([f"{exchange}:{ticker}"])
            data = quote.get(f"{exchange}:{ticker}")
            return float(data["last_price"]) if data and data.get("last_price") else None
        except Exception:
            logger.error(f"Failed to fetch live price for {exchange}:{ticker}.", exc_info=True)
            return None

    def _place_entry_orders(self, position: OptionsPosition) -> APIResponse:
        """Fill protective long legs first, then short legs; marks OPEN only once all 4 legs are filled."""
        legs = {leg.role: leg for leg in self.leg_repo.get_for_position(position.id)}

        missing = [role.value for role in ALL_ROLES if role not in legs]
        if missing:
            self.position_repo.update(position, { "status": OptionsPositionStatus.FAILED })
            logger.error(f"Options position {position.id} FAILED — missing leg roles at persistence: {missing}.")
            return APIResponse(success=False, message="ENTRY_FAILED_MISSING_LEGS", data={ "options_position_id": position.id, "missing_roles": missing })

        live_trading_enabled = bool(position.strategy_version.config.get("live_trading_enabled", False))

        longs_ok = self._fill_legs([legs[r] for r in LONG_ROLES], ENTRY_TRANSACTION, position.lots * position.lot_size, live_trading_enabled)
        if not longs_ok:
            self.position_repo.update(position, { "status": OptionsPositionStatus.FAILED })
            logger.error(f"Options position {position.id} FAILED — could not establish protective long legs.")
            return APIResponse(success=False, message="ENTRY_FAILED_LONG_LEGS", data={ "options_position_id": position.id })

        shorts_ok = self._fill_legs([legs[r] for r in SHORT_ROLES], ENTRY_TRANSACTION, position.lots * position.lot_size, live_trading_enabled)
        if not shorts_ok:
            logger.warning(f"Options position {position.id}: long legs filled, short legs still pending — will retry next entry-job tick.")
            return APIResponse(success=True, message="ENTRY_PARTIAL_LONGS_ONLY", data={ "options_position_id": position.id })

        self.position_repo.update(position, { "status": OptionsPositionStatus.OPEN })
        logger.info(f"Options position {position.id} fully OPEN ({'PAPER' if not live_trading_enabled else 'LIVE'}).")
        return APIResponse(success=True, message="ENTRY_COMPLETED", data=self._position_summary(position))

    # ------------------------------------------------------------------ #
    #  Exit                                                               #
    # ------------------------------------------------------------------ #

    def run_exit_evaluation(self, strategy_version: StrategyVersion, as_of_date: date) -> APIResponse:
        """Evaluate the exit priority chain for every OPEN position, and retry closing for any
        already-CLOSING position, then unwind leftover exposure from FAILED entries."""
        try:
            unwound = self._unwind_failed_positions(strategy_version, as_of_date)

            open_positions = self.position_repo.get_open_and_closing_for_strategy_version(strategy_version.id)
            exited, still_open = [], []

            for position in open_positions:
                if position.status == OptionsPositionStatus.CLOSING:
                    # Already committed to closing on an earlier tick (reason persisted then) — retry
                    # the leg mechanics, don't re-derive whether to close.
                    reason = position.exit_reason
                else:
                    reason = self._evaluate_exit(position, as_of_date)
                    if reason is None:
                        still_open.append(position.id)
                        continue

                if self._close_position(position, as_of_date, reason):
                    exited.append({ "options_position_id": position.id, "exit_reason": position.exit_reason.value })
                else:
                    still_open.append(position.id)

            return APIResponse(success=True, message="OPTIONS_EXIT_COMPLETED", data={ "positions_evaluated": len(open_positions), "exited": exited, "still_open": still_open, "unwound_failed": unwound })
        except Exception as exc:
            logger.error(f"Options exit evaluation failed for strategy version {strategy_version.id}: {exc}", exc_info=True)
            return APIResponse(success=False, message=str(exc))

    def _evaluate_exit(self, position: OptionsPosition, as_of_date: date) -> Optional[OptionsExitReason]:
        """Run the required exit priority chain for one OPEN position for one day. See
        execution_engines/options_iron_condor/logic.py:evaluate_exit_reason for the exact order —
        expiry safety, time exit, credit-reconciliation guard (real fills, never a decision-time
        quote), profit target, stop loss, else hold."""
        config = position.strategy_version.config
        days_to_expiry = (position.expiry_date - as_of_date).days

        real_entry_credit = self._compute_real_entry_credit(position)
        cost_to_close = self._compute_cost_to_close(position) if real_entry_credit is not None and real_entry_credit > 0 else None

        return logic.evaluate_exit_reason(days_to_expiry, real_entry_credit, cost_to_close, config["time_exit_dte"], config["profit_target_pct"], config["stop_loss_multiple"])

    def _compute_real_entry_credit(self, position: OptionsPosition) -> Optional[float]:
        """Real entry credit from ACTUAL fill prices — never the decision-time net_credit_per_lot
        quote, per the spec's explicit anti-stale-comparison requirement. None if any leg hasn't
        recorded a fill yet (shouldn't happen for an OPEN position, but defensive)."""
        legs = {leg.role: leg for leg in self.leg_repo.get_for_position(position.id)}
        fills: dict[OptionsLegRole, float] = {}
        for role in ALL_ROLES:
            leg = legs.get(role)
            if not leg or leg.entry_fill_price is None:
                return None
            fills[role] = float(leg.entry_fill_price)
        return logic.compute_spread_value(fills[OptionsLegRole.SHORT_CALL], fills[OptionsLegRole.SHORT_PUT], fills[OptionsLegRole.LONG_CALL], fills[OptionsLegRole.LONG_PUT])

    def _compute_cost_to_close(self, position: OptionsPosition) -> Optional[float]:
        """What it would cost right now to close the spread, from live LTPs. None if any quote is unusable."""
        legs = {leg.role: leg for leg in self.leg_repo.get_for_position(position.id)}
        if any(role not in legs for role in ALL_ROLES):
            return None

        try:
            quotes = self.kite_service.get_quotes([f"{KITE_EXCHANGE}:{legs[role].security.ticker}" for role in ALL_ROLES])
        except Exception:
            logger.error(f"Failed to fetch live quotes for cost-to-close on position {position.id}.", exc_info=True)
            return None

        ltps: dict[OptionsLegRole, float] = {}
        for role in ALL_ROLES:
            quote = quotes.get(f"{KITE_EXCHANGE}:{legs[role].security.ticker}")
            ltp = quote["last_price"] if quote else None
            if not ltp or ltp <= 0:
                return None
            ltps[role] = float(ltp)

        return logic.compute_spread_value(ltps[OptionsLegRole.SHORT_CALL], ltps[OptionsLegRole.SHORT_PUT], ltps[OptionsLegRole.LONG_CALL], ltps[OptionsLegRole.LONG_PUT])

    def _close_position(self, position: OptionsPosition, as_of_date: date, reason: OptionsExitReason) -> bool:
        """Close short legs first, then long legs; marks CLOSED only once all legs are confirmed closed.
        Persists exit_reason on first transition to CLOSING so a multi-tick retry keeps the reason
        that actually triggered the exit, rather than re-deriving a possibly different one later."""
        if position.status != OptionsPositionStatus.CLOSING:
            self.position_repo.update(position, { "status": OptionsPositionStatus.CLOSING, "exit_reason": reason })

        live_trading_enabled = bool(position.strategy_version.config.get("live_trading_enabled", False))
        legs = {leg.role: leg for leg in self.leg_repo.get_for_position(position.id)}

        shorts_closed = self._close_legs([legs[r] for r in SHORT_ROLES if r in legs], as_of_date, live_trading_enabled)
        if not shorts_closed:
            logger.warning(f"Options position {position.id}: could not close short legs — will retry next exit-job tick.")
            return False

        longs_closed = self._close_legs([legs[r] for r in LONG_ROLES if r in legs], as_of_date, live_trading_enabled)
        if not longs_closed:
            logger.warning(f"Options position {position.id}: shorts closed, long legs still open — will retry next exit-job tick.")
            return False

        self.position_repo.update(position, { "status": OptionsPositionStatus.CLOSED, "exit_date": as_of_date })
        logger.info(f"Options position {position.id} CLOSED — reason={reason.value}")
        return True

    def _unwind_failed_positions(self, strategy_version: StrategyVersion, as_of_date: date) -> list[int]:
        """Flatten any leftover filled legs from FAILED entries — those were never meant to carry real exposure."""
        failed_positions = (self.db.query(OptionsPosition).filter(OptionsPosition.strategy_version_id == strategy_version.id, OptionsPosition.status == OptionsPositionStatus.FAILED).all())

        live_trading_enabled = bool(strategy_version.config.get("live_trading_enabled", False))
        unwound = []
        for position in failed_positions:
            legs = self.leg_repo.get_for_position(position.id)
            if not any(leg.status == OptionsLegStatus.OPEN for leg in legs):
                continue

            if self._close_legs(legs, as_of_date, live_trading_enabled):
                self.position_repo.update(position, { "status": OptionsPositionStatus.CLOSED, "exit_date": as_of_date, "skip_reason": f"{position.skip_reason or ''} | unwound after failed entry".strip(" |") })
                unwound.append(position.id)
                logger.warning(f"Unwound leftover exposure from FAILED options position {position.id}.")
            else:
                logger.warning(f"Options position {position.id} (FAILED) still has unclosed legs — will retry unwind next exit-job tick.")

        return unwound

    # ------------------------------------------------------------------ #
    #  Reconciliation                                                     #
    # ------------------------------------------------------------------ #

    def run_reconciliation(self, as_of_date: date) -> APIResponse:
        """Poll every leg with an outstanding, unconfirmed order against the broker and record any fill
        found. Runs far more often than the once-daily entry/exit jobs so a fill that lands between
        scheduled ticks doesn't strand a position in PENDING/CLOSING until the next one. Poll/record
        only — never places a fresh order; (re)placement stays owned by the entry/exit jobs.

        Paper-mode legs never carry a kite_*_order_id (fills are recorded synchronously at placement
        time), so they never show up here — nothing to reconcile for a simulated fill."""
        try:
            legs = self.leg_repo.get_legs_with_outstanding_orders()
            resolved = 0

            for leg in legs:
                try:
                    if leg.status == OptionsLegStatus.PENDING:
                        side, target_status = "entry", OptionsLegStatus.OPEN
                    else:
                        side, target_status = "exit", OptionsLegStatus.CLOSED

                    self._reconcile_stale_order(leg, side=side, target_status=target_status, fill_date=as_of_date)
                    if leg.status == target_status:
                        resolved += 1
                except Exception as exc:
                    logger.error(f"Options reconciliation failed for leg {leg.id}: {exc}", exc_info=True)

            return APIResponse(success=True, message="OPTIONS_RECONCILIATION_COMPLETED", data={ "resolved": resolved })
        except Exception as exc:
            logger.error(f"Options reconciliation failed: {exc}", exc_info=True)
            return APIResponse(success=False, message=str(exc))

    # ------------------------------------------------------------------ #
    #  Order placement / fill polling (shared entry + exit machinery)     #
    # ------------------------------------------------------------------ #

    def _fill_legs(self, legs: list[OptionsLeg], transaction_map: dict, quantity: int, live_trading_enabled: bool) -> bool:
        """Place and confirm entry fills for a set of legs; returns True iff all end up OPEN."""
        for leg in legs:
            if leg.status != OptionsLegStatus.OPEN:
                self._place_and_confirm(leg, side="entry", target_status=OptionsLegStatus.OPEN, fill_date=date.today(), place=lambda l: self._place_leg_order(l, "entry", transaction_map[l.role], quantity, OptionsLegStatus.OPEN, date.today(), live_trading_enabled))
        return all(leg.status == OptionsLegStatus.OPEN for leg in legs)

    def _close_legs(self, legs: list[OptionsLeg], as_of_date: date, live_trading_enabled: bool) -> bool:
        """Place and confirm closing fills for a set of legs; returns True iff all end up CLOSED.

        A long leg whose contract expired before as_of_date can no longer be traded — the exchange
        already settled it (OTM = worthless, no fill ever needed). Settling it locally at zero cost
        instead of placing/polling an order avoids retrying forever against a dead instrument, which
        would otherwise strand the position in CLOSING permanently and block every future entry for
        this strategy version (get_active_for_strategy_version treats CLOSING as active). A short leg
        still open past expiry does NOT get the same zero-cost treatment, live or paper — unlike a
        long wing, "still open here" could mean a genuine unrecorded fill, so it goes through
        reconciliation/manual-review instead (see _handle_stale_short_leg_past_expiry) rather than
        ever fabricating a fill. On the expiry day itself the contract is still tradable, so the
        normal place/poll path runs for every leg there regardless of role.
        """
        # Legs never filled at entry (status != OPEN) have nothing to close and are left alone.
        for leg in legs:
            if leg.status != OptionsLegStatus.OPEN:
                continue
            if as_of_date > leg.security.expiry_date.date():
                if leg.role in LONG_ROLES:
                    self._settle_expired_leg(leg, as_of_date)
                else:
                    self._handle_stale_short_leg_past_expiry(leg, as_of_date)
                continue
            self._place_and_confirm(leg, side="exit", target_status=OptionsLegStatus.CLOSED, fill_date=as_of_date, place=lambda l: self._place_leg_order(l, "exit", CLOSE_TRANSACTION[l.role], l.entry_fill_quantity, OptionsLegStatus.CLOSED, as_of_date, live_trading_enabled))
        return all(leg.status != OptionsLegStatus.OPEN for leg in legs)

    def _settle_expired_leg(self, leg: OptionsLeg, as_of_date: date) -> None:
        """Mark a leg CLOSED at zero cost — its contract already expired OTM, nothing left to trade."""
        self.leg_repo.update(leg, { "status": OptionsLegStatus.CLOSED, "exit_fill_price": 0.0, "exit_fill_quantity": leg.entry_fill_quantity, "exit_date": as_of_date })
        logger.info(f"Leg {leg.id} ({leg.role.value}, {leg.security.ticker}) settled at expiry ({leg.security.expiry_date}) — marked CLOSED at zero cost.")

    def _handle_stale_short_leg_past_expiry(self, leg: OptionsLeg, as_of_date: date) -> None:
        """A short leg still OPEN after its contract's expiry needs a real reconciled price, never a
        fabricated zero. Reconcile against the broker if an order id is on record — that catches a
        fill or cancellation the earlier poll missed. If it's still unresolved, this needs a human to
        check what actually happened at settlement, so leave it OPEN and alert rather than guessing."""
        if leg.kite_exit_order_id:
            self._reconcile_stale_order(leg, side="exit", target_status=OptionsLegStatus.CLOSED, fill_date=as_of_date)
            if leg.status == OptionsLegStatus.CLOSED:
                return

        logger.error(f"Leg {leg.id} ({leg.role.value}, {leg.security.ticker}) is a short leg still OPEN after expiry with no confirmed fill — needs manual review.")
        self._send_stale_short_leg_alert(leg)

    def _send_stale_short_leg_alert(self, leg: OptionsLeg) -> None:
        """Send a Discord notification when a short leg can't be confirmed closed past its expiry."""
        try:
            from app.celery.base import get_discord_service
            from app.schemas.notification import NotificationPayload, NotificationMetric
            discord = get_discord_service()
            if not discord:
                return
            payload = NotificationPayload(
                operation="Options Leg Needs Manual Review", status="warning", duration_seconds=0,
                summary=f"{leg.security.ticker} ({leg.role.value}) is still open past expiry with no confirmed exit fill.",
                results=[NotificationMetric(label="Leg", value=str(leg.id)), NotificationMetric(label="Ticker", value=leg.security.ticker), NotificationMetric(label="Expiry", value=str(leg.security.expiry_date))],
                action_required=["Check Kite (or the paper-trading log, if this is a paper position) for the actual settlement/exercise price and reconcile this leg manually."],
            )
            discord.send_notification(payload)
        except Exception as exc:
            logger.warning(f"Failed to send stale short leg alert for leg {leg.id}: {exc}")

    def _place_and_confirm(self, leg: OptionsLeg, side: str, target_status: OptionsLegStatus, fill_date: date, place: Callable[[OptionsLeg], None]) -> None:
        """Shared place -> poll -> reprice-and-retry-once cascade for a single entry or exit leg fill."""
        # Idempotent: a leg with an order id already recorded is only polled, never re-ordered. If the
        # poll below determines that order is actually dead (cancelled/rejected — NSE cancels regular-day
        # LIMIT orders at end of day, so a leg revisited on a later tick could otherwise poll a dead order
        # forever), it clears the order id, and this reprices and places a fresh order once more within
        # the same tick rather than waiting for the next one. A leg still unfilled after that stays as-is
        # for the next job tick to pick up — never a second order while one is still genuinely live.
        # A paper-mode fill (see _place_leg_order) writes status == target_status directly with no
        # order id ever set, so every branch below is a no-op for it after the first `place(leg)`.
        order_id_field = f"kite_{side}_order_id"

        if not getattr(leg, order_id_field):
            place(leg)
        if getattr(leg, order_id_field) and leg.status != target_status:
            self._poll_and_record_fill(leg, side, target_status, fill_date)
        if not getattr(leg, order_id_field) and leg.status != target_status:
            place(leg)
            if getattr(leg, order_id_field) and leg.status != target_status:
                self._poll_and_record_fill(leg, side, target_status, fill_date)

    def _place_leg_order(self, leg: OptionsLeg, side: str, transaction_type: str, quantity: int, target_status: OptionsLegStatus, fill_date: date, live_trading_enabled: bool) -> None:
        """Fetch a live quote, price a marketable limit order, and either place it for real (live_trading_enabled)
        or simulate the fill immediately (paper trading, the default) — never a stale price either way."""
        security = leg.security
        try:
            quote = self.kite_service.get_quotes([f"{KITE_EXCHANGE}:{security.ticker}"])
            ltp = quote[f"{KITE_EXCHANGE}:{security.ticker}"]["last_price"]
        except Exception:
            logger.error(f"Could not fetch LTP for {security.ticker} before placing {side} {transaction_type} order (leg {leg.id}) — leaving as-is for retry.", exc_info=True)
            return

        price = self._round_to_tick(ltp * ORDER_BUFFERS[transaction_type], security.tick_size)

        if not live_trading_enabled:
            price_field, qty_field, date_field = f"{side}_fill_price", f"{side}_fill_quantity", f"{side}_date"
            self.leg_repo.update(leg, { "status": target_status, price_field: price, qty_field: quantity, date_field: fill_date })
            logger.info(f"[PAPER] Simulated {side} {transaction_type} fill for {security.ticker} qty={quantity} price={price} (leg {leg.id}, role={leg.role.value}) — live_trading_enabled=False, no real order placed.")
            return

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
