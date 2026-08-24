# backend/app/services/portfolio.py

import math
from typing import Optional

from sqlalchemy.orm import Session

from app.enums.fund import FlowType
from app.models.fund import AccountSnapshot, CashFlow
from app.models.strategy import StrategyVersion
from app.repositories.trade import TradeRepository
from app.repositories.options import OptionsPositionRepository
from app.repositories.strategy import StrategyRepository, StrategyVersionRepository
from app.services.brokers.kite import KiteService
from app.services.fund import FundService
from app.utils.logger import get_logger

logger = get_logger(__name__)

EQUITY_KITE_EXCHANGE = "NSE"


class PortfolioService:

    def __init__(self, db: Session, kite_service: KiteService = None):
        """Initialise with a DB session and an optional Kite client for live account data."""
        self.db = db
        self.kite_service = kite_service
        self.trade_repo = TradeRepository(db)
        self.options_position_repo = OptionsPositionRepository(db)
        self.strategy_repo = StrategyRepository(db)
        self.strategy_version_repo = StrategyVersionRepository(db)

    def get_account_size(self) -> float:
        """Return total account size as cash balance plus book value of all held positions."""
        margins = self.kite_service.get_margins()
        cash = margins["equity"]["available"]["live_balance"]
        holdings = self.kite_service.get_holdings()
        # Include t1_quantity (pending T+1 settlement) so same-day CNC buys count toward account size.
        holdings_value = sum(h["average_price"] * ((h.get("quantity") or 0) + (h.get("t1_quantity") or 0)) for h in holdings)
        account_size = cash + holdings_value
        logger.info(f"Account Size: cash={cash}, holdings_value={holdings_value}, total_account_size={account_size}")
        return account_size

    def get_isolated_account_size(self, strategy_version: StrategyVersion) -> float:
        """Return this strategy's own slice of total account capital.

        Scales get_account_size() by the strategy's account_capital_pct config (default 1.0 —
        the whole account, identical to calling get_account_size() directly, so any strategy
        that doesn't set this key behaves exactly as before). Additive on top of the shared
        get_account_size() figure rather than a separate capital-tracking mechanism, so multiple
        live strategies stop implicitly assuming they each own 100% of the same capital —
        each one's config now says explicitly how much of the account it's allowed to size
        against, adjustable per strategy without touching this method or any other strategy.
        """
        pct = strategy_version.config.get("account_capital_pct", 1.0)
        account_size = self.get_account_size()
        isolated_size = account_size * pct
        logger.info(f"Isolated Account Size: strategy_version_id={strategy_version.id}, account_capital_pct={pct}, account_size={account_size}, isolated_size={isolated_size}")
        return isolated_size

    def get_position_size(self, strategy_version: StrategyVersion) -> float:
        """Calculate capital to deploy per trade as this strategy's isolated account size divided by max positions."""
        max_positions = strategy_version.config["selection"]["max_signals"]
        account_size = self.get_isolated_account_size(strategy_version)
        position_size = account_size / max_positions
        logger.info(f"Position Size: account_size={account_size}, max_positions={max_positions}, position_size={position_size}")
        return position_size

    def get_available_slots(self, strategy_version: StrategyVersion) -> int:
        """Return how many new trade slots remain under the strategy's max_positions limit."""
        max_positions = strategy_version.config["selection"]["max_signals"]
        open_trades = self.trade_repo.get_open_trades_for_strategy_version(strategy_version.id)
        available = max_positions - len(open_trades)
        logger.info(f"Available Slots: max_positions={max_positions}, open_trades={len(open_trades)}, available_slots={available}")
        return max(available, 0)

    # ------------------------------------------------------------------ #
    #  Capital Allocation                                                 #
    # ------------------------------------------------------------------ #

    def get_capital_allocation(self) -> dict:
        """Return account size (from the latest daily snapshot) and how it's split across active strategies.

        Deliberately reads the latest AccountSnapshot rather than calling get_account_size() —
        that requires a KiteService, and KiteService.__init__ unconditionally launches a headless
        browser via SeleniumService() regardless of whether a cached token exists. Capital
        allocation is a slow-moving planning view, not a live trading one; accurate to within a
        day (same tradeoff get_nav_curve() already makes) is the right cost/value call here.
        """
        snapshot = self.db.query(AccountSnapshot).order_by(AccountSnapshot.snapshot_date.desc()).first()
        if not snapshot:
            return { "account_size": None, "snapshot_date": None, "strategies": [], "total_allocated_pct": 0.0, "overallocated": False }

        account_size = float(snapshot.total_value)
        strategies = []
        total_allocated_pct = 0.0

        for strategy in self.strategy_repo.get_all_with_versions():
            if not strategy.is_active:
                continue

            active_version = self.strategy_version_repo.get_active_for_strategy(strategy.id)
            if not active_version:
                continue

            pct = active_version.config.get("account_capital_pct", 1.0)
            allocated = account_size * pct
            deployed = self._deployed_amount_for_strategy(strategy.id, active_version.implementation_class)

            total_allocated_pct += pct

            strategies.append({
                "strategy_id": strategy.id, "code": strategy.code, "name": strategy.name, "is_active": strategy.is_active,
                "account_capital_pct": pct, "allocated_amount": round(allocated, 2), "deployed_amount": round(deployed, 2),
                "deployed_pct_of_allocated": round(deployed / allocated * 100, 2) if allocated > 0 else None,
            })

        return {
            "account_size": round(account_size, 2), "snapshot_date": snapshot.snapshot_date, "strategies": strategies,
            "total_allocated_pct": round(total_allocated_pct * 100, 2), "overallocated": total_allocated_pct > 1.0,
        }

    def _deployed_amount_for_strategy(self, strategy_id: int, implementation_class: str) -> float:
        """Sum currently-deployed capital for a strategy across every version — open exposure doesn't move when a newer version activates."""
        if implementation_class == "nifty_iron_condor":
            positions = self.options_position_repo.get_open_for_strategy(strategy_id)
            return sum(float(p.margin_per_lot) * p.lots for p in positions if p.margin_per_lot is not None and p.lots)

        trades = self.trade_repo.get_open_trades_for_strategy(strategy_id)
        return sum(float(t.fill_price) * t.fill_quantity for t in trades if t.fill_price is not None and t.fill_quantity)

    # ------------------------------------------------------------------ #
    #  Circuit Breakers                                                   #
    # ------------------------------------------------------------------ #

    def check_drawdown_circuit_breaker(self) -> Optional[dict]:
        """Evaluate the portfolio-wide (equity + options) drawdown breaker and halt new entries via the kill switch on breach.

        Combines realized P&L from both Trade and OptionsPosition history — a drawdown breaker that
        only sees the equity book would be watching a strategy that isn't currently running, since
        the iron condor is the live strategy today. Never auto-clears: like the kill switch itself,
        resuming after a halt is a deliberate human act, not something this check reverses on its own.
        """
        from datetime import datetime, timezone
        from app.enums.trade import TradeStatus
        from app.repositories.circuit_breaker import CircuitBreakerRepository
        from app.repositories.kill_switch import KillSwitchRepository
        from app.services.kill_switch import KillSwitchService
        from app.services.options_trade import OptionsTradeService

        breaker_repo = CircuitBreakerRepository(self.db)
        breaker = breaker_repo.get_by_type("drawdown")
        if not breaker or not breaker.enabled:
            return None

        if KillSwitchRepository(self.db).get_singleton().enabled:
            return None

        equity_closed = [
            { "exit_date": t.exit_date, "pnl": (float(t.exit_price) - float(t.fill_price)) * t.fill_quantity }
            for t in self.trade_repo.get_all_trades(status=TradeStatus.CLOSED) if t.exit_price and t.fill_price and t.fill_quantity and t.exit_date
        ]
        options_service = OptionsTradeService(self.db, self.kite_service)
        options_closed = options_service.get_closed_positions_pnl()

        cumulative = 0.0
        peak = 0.0
        for entry in sorted(equity_closed + options_closed, key=lambda x: x["exit_date"]):
            cumulative += entry["pnl"]
            if cumulative > peak:
                peak = cumulative

        current = cumulative + self._get_equity_unrealized_pnl() + options_service.get_unrealized_pnl()

        # Normalise against the latest daily capital snapshot rather than peak cumulative P&L — peak can be a
        # tiny rupee figure early in a strategy's life, which made drawdown_pct blow past 100% on ordinary
        # losing stretches. Reads AccountSnapshot rather than get_account_size() for the same reason
        # get_capital_allocation() does: no live Kite call for what's a slow-moving capital base.
        snapshot = self.db.query(AccountSnapshot).order_by(AccountSnapshot.snapshot_date.desc()).first()
        capital_base = float(snapshot.total_value) if snapshot else 0.0
        if capital_base <= 0:
            return None

        threshold_pct = breaker.params.get("threshold_pct", 5.0)
        drawdown_pct = (peak - current) / capital_base * 100
        if drawdown_pct < threshold_pct:
            return None

        reason = f"Circuit breaker: portfolio drawdown -{drawdown_pct:.1f}% exceeds -{threshold_pct:.0f}% threshold"
        logger.warning(reason)
        KillSwitchService(self.db).activate(reason=reason)
        breaker_repo.update(breaker, { "last_triggered_at": datetime.now(timezone.utc), "last_reason": reason })

        return { "triggered": True, "peak": round(peak, 2), "current": round(current, 2), "capital_base": round(capital_base, 2), "drawdown_pct": round(drawdown_pct, 2), "threshold_pct": threshold_pct, "reason": reason }

    def _get_equity_unrealized_pnl(self) -> float:
        """Sum mark-to-market P&L across all open equity trades using live LTP quotes."""
        open_trades = [ t for t in self.trade_repo.get_open_trades() if t.fill_price and t.fill_quantity ]
        if not open_trades:
            return 0.0

        tickers = [ f"{EQUITY_KITE_EXCHANGE}:{t.security.ticker}" for t in open_trades ]
        quotes = self.kite_service.get_quotes(tickers)

        unrealized = 0.0
        for t in open_trades:
            quote = quotes.get(f"{EQUITY_KITE_EXCHANGE}:{t.security.ticker}")
            if not quote:
                continue
            unrealized += (quote["last_price"] - float(t.fill_price)) * t.fill_quantity
        return unrealized

    # ------------------------------------------------------------------ #
    #  Stats                                                              #
    # ------------------------------------------------------------------ #

    def get_stats(self) -> dict:
        """Aggregate trade-level performance statistics across all closed trades — equity and options combined.

        Equity (Trade) and options (OptionsPosition) are two separate models, so every metric here
        is built by computing each asset class's contribution separately and summing/concatenating —
        there's no shared ORM type to query across. Only OPEN and CLOSED positions count as real
        options trades; PENDING (not yet filled) and SKIPPED (signal evaluated, never entered) never
        committed capital, matching how equity never creates a Trade row for a skipped signal either.
        """
        from app.enums.trade import TradeStatus
        from app.enums.options import OptionsPositionStatus
        from app.services.options_trade import OptionsTradeService

        all_trades = self.trade_repo.get_all_trades()
        open_equity_trades = [ t for t in all_trades if t.status == TradeStatus.OPEN ]
        closed_equity_trades = [ t for t in all_trades if t.status == TradeStatus.CLOSED and t.exit_price and t.fill_price ]

        equity_pnl_pcts = [(float(t.exit_price) - float(t.fill_price)) / float(t.fill_price) * 100 for t in closed_equity_trades]
        equity_pnl_values = [(float(t.exit_price) - float(t.fill_price)) * t.fill_quantity for t in closed_equity_trades if t.fill_quantity]
        equity_holding_days = [(t.exit_date - t.entry_date).days for t in closed_equity_trades if t.exit_date]
        equity_drawdown_entries = [
            { "exit_date": t.exit_date, "pnl": (float(t.exit_price) - float(t.fill_price)) * t.fill_quantity }
            for t in closed_equity_trades if t.fill_quantity and t.exit_date
        ]

        open_options_positions = self.options_position_repo.get_all_positions(status=OptionsPositionStatus.OPEN)
        closed_options = OptionsTradeService(self.db).get_closed_positions_for_stats()

        options_pnl_pcts = [p["pnl_pct"] for p in closed_options]
        options_pnl_values = [p["pnl"] for p in closed_options]
        options_holding_days = [(p["exit_date"] - p["entry_date"]).days for p in closed_options]
        options_drawdown_entries = [{ "exit_date": p["exit_date"], "pnl": p["pnl"] } for p in closed_options]

        pnl_pcts = equity_pnl_pcts + options_pnl_pcts
        pnl_values = equity_pnl_values + options_pnl_values
        holding_days = equity_holding_days + options_holding_days
        wins = [ p for p in pnl_pcts if p > 0 ]
        losses = [ p for p in pnl_pcts if p <= 0 ]

        net_deposits = FundService(self.db).get_net_deposits()

        return {
            "total_trades": len(all_trades) + len(open_options_positions) + len(closed_options),
            "open_trades": len(open_equity_trades) + len(open_options_positions),
            "closed_trades": len(closed_equity_trades) + len(closed_options),
            "win_rate": round(len(wins) / len(pnl_pcts) * 100, 2) if pnl_pcts else None,
            "avg_holding_days": round(sum(holding_days) / len(holding_days), 1) if holding_days else None,
            "avg_win_pct": round(sum(wins) / len(wins), 4) if wins else None,
            "avg_loss_pct": round(sum(losses) / len(losses), 4) if losses else None,
            "best_trade_pct": round(max(pnl_pcts), 4) if pnl_pcts else None,
            "worst_trade_pct": round(min(pnl_pcts), 4) if pnl_pcts else None,
            "total_pnl": round(sum(pnl_values), 2) if pnl_values else None,
            "sharpe_ratio": self._calculate_sharpe(pnl_pcts, holding_days),
            "max_drawdown_pct": self._calculate_max_drawdown(equity_drawdown_entries + options_drawdown_entries),
            "profit_factor": self._calculate_profit_factor(pnl_values),
            "net_deposits": net_deposits,
            "true_return_pct": self.get_true_return_pct(),
        }

    def _calculate_sharpe(self, pnl_pcts: list[float], holding_days: list[int]) -> Optional[float]:
        """Compute annualised Sharpe ratio using trade-level returns and average holding period."""
        if len(pnl_pcts) < 2:
            return None
        mean_r = sum(pnl_pcts) / len(pnl_pcts)
        variance = sum((r - mean_r)**2 for r in pnl_pcts) / (len(pnl_pcts) - 1)
        std_r = math.sqrt(variance) if variance > 0 else 0
        if std_r == 0:
            return None
        avg_hold = sum(holding_days) / len(holding_days) if holding_days else 1
        trades_per_year = 252 / avg_hold if avg_hold > 0 else 252
        return round(mean_r / std_r * math.sqrt(trades_per_year), 2)

    def _calculate_max_drawdown(self, pnl_entries: list[dict]) -> Optional[float]:
        """Walk chronologically-ordered {exit_date, pnl} entries — equity and options combined — and
        return the largest peak-to-trough drawdown as a percentage of account capital.

        Normalises against capital, not peak cumulative P&L — the same bug already fixed for the
        drawdown circuit breaker (see check_drawdown_circuit_breaker): a peak that's a tiny rupee
        figure early in a strategy's life sends the percentage past 100% on perfectly ordinary
        losing stretches. This mirrors that fix. Also sorts by exit_date explicitly rather than
        trusting caller order — the equity curve must be walked chronologically, and closed trades
        arrive in entry_date-descending order from their respective repositories, which made the
        walk itself wrong on top of the normalisation bug. Takes plain {exit_date, pnl} dicts rather
        than ORM Trade objects so equity and options positions — two different models — can be
        merged into one chronological walk.
        """
        ordered = sorted(pnl_entries, key=lambda e: e["exit_date"])
        if not ordered:
            return None

        snapshot = self.db.query(AccountSnapshot).order_by(AccountSnapshot.snapshot_date.desc()).first()
        capital_base = float(snapshot.total_value) if snapshot else None
        if not capital_base:
            return None

        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        for entry in ordered:
            cumulative += entry["pnl"]
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd
        return round(max_dd / capital_base * 100, 2)

    def _calculate_profit_factor(self, pnl_values: list[float]) -> Optional[float]:
        """Return gross profit divided by gross loss across all closed trades."""
        gross_profit = sum(v for v in pnl_values if v > 0)
        gross_loss = abs(sum(v for v in pnl_values if v < 0))
        return round(gross_profit / gross_loss, 2) if gross_loss > 0 else None

    # ------------------------------------------------------------------ #
    #  Equity curve & analytics                                           #
    # ------------------------------------------------------------------ #

    def get_equity_curve(self) -> list[dict]:
        """Build a time-ordered list of cumulative P&L data points from closed trades."""
        closed_trades = self.trade_repo.get_closed_trades_ordered()
        cumulative = 0.0
        points = []
        for trade in closed_trades:
            if not trade.exit_price or not trade.fill_price or not trade.fill_quantity:
                continue
            pnl = (float(trade.exit_price) - float(trade.fill_price)) * trade.fill_quantity
            cumulative += pnl
            points.append({ "date": trade.exit_date, "cumulative_pnl": round(cumulative, 2), "trade_id": trade.id, "ticker": trade.security.ticker, "pnl": round(pnl, 2), })
        return points

    def get_nav_curve(self) -> list[dict]:
        """Build a time-ordered list of daily account value (cash + holdings) snapshots, with cash flow markers."""
        snapshots = self.db.query(AccountSnapshot).order_by(AccountSnapshot.snapshot_date).all()
        flows_by_date: dict = {}
        for f in self.db.query(CashFlow).all():
            flows_by_date.setdefault(f.flow_date, []).append(f)

        points = []
        for s in snapshots:
            flows = flows_by_date.get(s.snapshot_date, [])
            net_flow = sum((float(f.amount) if f.flow_type == FlowType.DEPOSIT else -float(f.amount)) for f in flows) if flows else None
            points.append({ "date": s.snapshot_date, "cash_balance": float(s.cash_balance), "holdings_value": float(s.holdings_value), "total_value": float(s.total_value), "cash_flow": net_flow, })
        return points

    def get_true_return_pct(self) -> Optional[float]:
        """Compute the cash-flow-adjusted return over the full snapshot history using the Modified Dietz method."""
        snapshots = self.db.query(AccountSnapshot).order_by(AccountSnapshot.snapshot_date).all()
        if len(snapshots) < 2:
            return None

        start, end = snapshots[0], snapshots[-1]
        period_days = (end.snapshot_date - start.snapshot_date).days
        if period_days <= 0:
            return None

        bmv = float(start.total_value)
        emv = float(end.total_value)

        flows = self.db.query(CashFlow).filter(CashFlow.flow_date > start.snapshot_date, CashFlow.flow_date <= end.snapshot_date).all()
        net_cf = 0.0
        weighted_cf = 0.0
        for f in flows:
            signed = float(f.amount) if f.flow_type == FlowType.DEPOSIT else -float(f.amount)
            days_since_flow = (end.snapshot_date - f.flow_date).days
            weight = days_since_flow / period_days
            net_cf += signed
            weighted_cf += signed * weight

        denominator = bmv + weighted_cf
        if denominator == 0:
            return None
        return round(((emv - bmv - net_cf) / denominator) * 100, 2)

    def get_analytics(self) -> dict:
        """Return return distribution buckets and sector-level performance breakdown."""
        from app.enums.trade import TradeStatus
        closed_trades = [ t for t in self.trade_repo.get_all_trades() if t.status == TradeStatus.CLOSED and t.exit_price and t.fill_price ]
        pnl_pcts = [(float(t.exit_price) - float(t.fill_price)) / float(t.fill_price) * 100 for t in closed_trades]

        return { "return_distribution": self._build_return_distribution(pnl_pcts), "sector_performance": self._build_sector_performance(closed_trades), }

    def _build_return_distribution(self, pnl_pcts: list[float]) -> list[dict]:
        """Count trades falling into each fixed P&L percentage bucket."""
        buckets = [("< -20%", -999, -20, False), ("-20 to -10%", -20, -10, False), ("-10 to -5%", -10, -5, False), ("-5 to 0%", -5, 0, False), ("0 to 5%", 0, 5, True), ("5 to 10%", 5, 10, True), ("10 to 20%", 10, 20, True), ("> 20%", 20, 999, True), ]
        return [{ "bucket": label, "count": sum(1 for p in pnl_pcts if lo <= p < hi), "is_win": is_win } for label, lo, hi, is_win in buckets]

    def _build_sector_performance(self, closed_trades: list) -> list[dict]:
        """Group closed trades by sector and compute win rate and average return per sector."""
        sector_map: dict[str, list] = {}
        for t in closed_trades:
            sector = t.security.sector or "Other"
            sector_map.setdefault(sector, []).append(t)

        result = []
        for sector, trades in sorted(sector_map.items(), key=lambda x: -len(x[1])):
            pnls = [(float(t.exit_price) - float(t.fill_price)) / float(t.fill_price) * 100 for t in trades]
            wins = [ p for p in pnls if p > 0 ]
            result.append({ "sector": sector, "trades": len(trades), "wins": len(wins), "win_rate": round(len(wins) / len(pnls) * 100) if pnls else None, "avg_return": round(sum(pnls) / len(pnls), 2) if pnls else None, })
        return result
