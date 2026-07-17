# backend/app/services/portfolio.py

import math
from typing import Optional

from sqlalchemy.orm import Session

from app.enums.fund import FlowType
from app.models.fund import AccountSnapshot, CashFlow
from app.models.strategy import StrategyVersion
from app.repositories.trade import TradeRepository
from app.services.brokers.kite import KiteService
from app.services.fund import FundService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PortfolioService:

    def __init__(self, db: Session, kite_service: KiteService = None):
        """Initialise with a DB session and an optional Kite client for live account data."""
        self.db = db
        self.kite_service = kite_service
        self.trade_repo = TradeRepository(db)

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

    def get_position_size(self, strategy_version: StrategyVersion) -> float:
        """Calculate capital to deploy per trade as account size divided by max positions."""
        max_positions = strategy_version.config["selection"]["max_signals"]
        account_size = self.get_account_size()
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
    #  Stats                                                              #
    # ------------------------------------------------------------------ #

    def get_stats(self) -> dict:
        """Aggregate trade-level performance statistics across all closed trades."""
        from app.enums.trade import TradeStatus
        all_trades = self.trade_repo.get_all_trades()
        open_trades = [ t for t in all_trades if t.status == TradeStatus.OPEN ]
        closed_trades = [ t for t in all_trades if t.status == TradeStatus.CLOSED and t.exit_price and t.fill_price ]

        pnl_pcts = [(float(t.exit_price) - float(t.fill_price)) / float(t.fill_price) * 100 for t in closed_trades]
        wins = [ p for p in pnl_pcts if p > 0 ]
        losses = [ p for p in pnl_pcts if p <= 0 ]
        pnl_values = [(float(t.exit_price) - float(t.fill_price)) * t.fill_quantity for t in closed_trades if t.fill_quantity]
        holding_days = [(t.exit_date - t.entry_date).days for t in closed_trades if t.exit_date]

        net_deposits = FundService(self.db).get_net_deposits()

        return {
            "total_trades": len(all_trades),
            "open_trades": len(open_trades),
            "closed_trades": len(closed_trades),
            "win_rate": round(len(wins) / len(pnl_pcts) * 100, 2) if pnl_pcts else None,
            "avg_holding_days": round(sum(holding_days) / len(holding_days), 1) if holding_days else None,
            "avg_win_pct": round(sum(wins) / len(wins), 4) if wins else None,
            "avg_loss_pct": round(sum(losses) / len(losses), 4) if losses else None,
            "best_trade_pct": round(max(pnl_pcts), 4) if pnl_pcts else None,
            "worst_trade_pct": round(min(pnl_pcts), 4) if pnl_pcts else None,
            "total_pnl": round(sum(pnl_values), 2) if pnl_values else None,
            "sharpe_ratio": self._calculate_sharpe(pnl_pcts, holding_days),
            "max_drawdown_pct": self._calculate_max_drawdown(closed_trades),
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

    def _calculate_max_drawdown(self, closed_trades: list) -> Optional[float]:
        """Walk the equity curve and return the largest peak-to-trough drawdown as a percentage."""
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        for t in closed_trades:
            if not t.exit_price or not t.fill_price or not t.fill_quantity:
                continue
            pnl = (float(t.exit_price) - float(t.fill_price)) * t.fill_quantity
            cumulative += pnl
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd
        return round(max_dd / peak * 100, 2) if peak > 0 else None

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
