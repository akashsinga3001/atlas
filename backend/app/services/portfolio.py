# backend/app/services/portfolio.py

from sqlalchemy.orm import Session

from app.models.strategy import StrategyVersion
from app.repositories.trade import TradeRepository
from app.services.brokers.kite import KiteService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PortfolioService:
    """PortfolioService class to manage portfolio-related operations."""

    def __init__(self, db: Session, kite_service: KiteService):
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
        max_positions = strategy_version.config["max_positions"]
        account_size = self.get_account_size()
        position_size = account_size / max_positions
        logger.info(f"Position Size: account_size={account_size}, max_positions={max_positions}, position_size={position_size}")
        return position_size

    def get_available_slots(self, strategy_version: StrategyVersion) -> int:
        """Calculate available slots for new trades based on max_positions and current open trades."""
        max_positions = strategy_version.config["max_positions"]
        open_trades = self.trade_repo.get_open_trades_for_strategy_version(strategy_version.id)
        available = max_positions - len(open_trades)
        logger.info(f"Available Slots: max_positions={max_positions}, open_trades={len(open_trades)}, available_slots={available}")
        return max(available, 0)
