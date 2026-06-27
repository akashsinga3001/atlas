# backend/app/services/portfolio.py

import math

from sqlalchemy.orm import Session

from app.models.strategy import StrategyVersion
from app.repositories.trade import TradeRepository
from app.services.brokers.kite import KiteService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PortfolioService:
    """PortfolioService class to manage portfolio-related operations."""

    def __init__(self, db: Session, kite_service: KiteService = None):
        self.db = db
        self.kite_service = kite_service
        self.trade_repo = TradeRepository(db)

    def get_account_size(self) -> float:
        """Cash + book value of all open holdings from Kite"""
        margins = self.kite_service.get_margins()
        cash = margins["equity"]["available"]["live_balance"]

        holdings = self.kite_service.get_holdings()
        holdings_value = sum(h["average_price"] * h["quantity"] for h in holdings)

        account_size = cash + holdings_value
        logger.info(f"Account Size: cash={cash}, holdings_value={holdings_value}, total_account_size={account_size}")
        return account_size

    def get_position_size(self, strategy_version: StrategyVersion) -> float:
        """Capital to deploy per trade = account_size / max_positions."""
        max_positions = strategy_version.config["selection"]["max_signals"]
        account_size = self.get_account_size()
        position_size = account_size / max_positions
        logger.info(f"Position Size: account_size={account_size}, max_positions={max_positions}, position_size={position_size}")
        return position_size

    def get_available_slots(self, strategy_version: StrategyVersion) -> int:
        """Calculate available slots for new trades based on max_positions and current open trades."""
        max_positions = strategy_version.config["selection"]["max_signals"]
        open_trades = self.trade_repo.get_open_trades_for_strategy_version(strategy_version.id)
        available = max_positions - len(open_trades)
        logger.info(f"Available Slots: max_positions={max_positions}, open_trades={len(open_trades)}, available_slots={available}")
        return max(available, 0)

    def get_stats(self) -> dict:
        from app.enums.trade import TradeStatus
        all_trades = self.trade_repo.get_all_trades()
        open_trades = [ t for t in all_trades if t.status == TradeStatus.OPEN ]
        closed_trades = [ t for t in all_trades if t.status == TradeStatus.CLOSED and t.exit_price and t.fill_price ]

        pnl_pcts = [(float(t.exit_price) - float(t.fill_price)) / float(t.fill_price) * 100 for t in closed_trades]
        wins = [ p for p in pnl_pcts if p > 0 ]
        losses = [ p for p in pnl_pcts if p <= 0 ]
        pnl_values = [(float(t.exit_price) - float(t.fill_price)) * t.fill_quantity for t in closed_trades if t.fill_quantity]
        holding_days = [(t.exit_date - t.entry_date).days for t in closed_trades if t.exit_date]

        # Trade-level annualized Sharpe
        sharpe = None
        if len(pnl_pcts) >= 2:
            mean_r = sum(pnl_pcts) / len(pnl_pcts)
            variance = sum((r - mean_r)**2 for r in pnl_pcts) / (len(pnl_pcts) - 1)
            std_r = math.sqrt(variance) if variance > 0 else 0
            avg_hold = sum(holding_days) / len(holding_days) if holding_days else 1
            trades_per_year = 252 / avg_hold if avg_hold > 0 else 252
            sharpe = round(mean_r / std_r * math.sqrt(trades_per_year), 2) if std_r > 0 else None

        # Max drawdown from equity curve
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
        max_drawdown_pct = round(max_dd / peak * 100, 2) if peak > 0 else None

        # Profit factor
        gross_profit = sum(v for v in pnl_values if v > 0)
        gross_loss = abs(sum(v for v in pnl_values if v < 0))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else None

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
            "sharpe_ratio": sharpe,
            "max_drawdown_pct": max_drawdown_pct,
            "profit_factor": profit_factor,
        }

    def get_equity_curve(self) -> list[dict]:
        closed_trades = self.trade_repo.get_closed_trades_ordered()
        cumulative = 0.0
        points = []
        for trade in closed_trades:
            if not trade.exit_price or not trade.fill_price or not trade.fill_quantity:
                continue
            pnl = (float(trade.exit_price) - float(trade.fill_price)) * trade.fill_quantity
            cumulative += pnl
            points.append({ "date": trade.exit_date, "cumulative_pnl": round(cumulative, 2), "trade_id": trade.id, "ticker": trade.security.ticker, "pnl": round(pnl, 2) })
        return points

    def get_analytics(self) -> dict:
        from app.enums.trade import TradeStatus
        closed_trades = [ t for t in self.trade_repo.get_all_trades() if t.status == TradeStatus.CLOSED and t.exit_price and t.fill_price ]

        pnl_pcts = [(float(t.exit_price) - float(t.fill_price)) / float(t.fill_price) * 100 for t in closed_trades]

        buckets = [("< -20%", -999, -20, False), ("-20 to -10%", -20, -10, False), ("-10 to -5%", -10, -5, False), ("-5 to 0%", -5, 0, False), ("0 to 5%", 0, 5, True), ("5 to 10%", 5, 10, True), ("10 to 20%", 10, 20, True), ("> 20%", 20, 999, True), ]
        return_distribution = []
        for label, lo, hi, is_win in buckets:
            count = sum(1 for p in pnl_pcts if lo <= p < hi)
            return_distribution.append({ "bucket": label, "count": count, "is_win": is_win })

        sector_map: dict[str, list] = {}
        for t in closed_trades:
            sector = t.security.sector or "Other"
            sector_map.setdefault(sector, []).append(t)

        sector_performance = []
        for sector, trades in sorted(sector_map.items(), key=lambda x: -len(x[1])):
            pnls = [(float(t.exit_price) - float(t.fill_price)) / float(t.fill_price) * 100 for t in trades]
            wins = [ p for p in pnls if p > 0 ]
            sector_performance.append({ "sector": sector, "trades": len(trades), "wins": len(wins), "win_rate": round(len(wins) / len(pnls) * 100) if pnls else None, "avg_return": round(sum(pnls) / len(pnls), 2) if pnls else None, })

        return { "return_distribution": return_distribution, "sector_performance": sector_performance, }
