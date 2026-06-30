# backend/app/services/fund.py

from datetime import date

from sqlalchemy.orm import Session

from app.enums.fund import FlowType
from app.enums.trade import TradeStatus
from app.models.fund import CashFlow, AccountSnapshot
from app.repositories.trade import TradeRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)

KITE_EXCHANGE = "NSE"


class FundService:
    """Service class for tracking manual cash flows (deposits/withdrawals) and daily account value snapshots."""

    def __init__(self, db: Session, kite_service=None):
        self.db = db
        self.kite_service = kite_service
        self.trade_repo = TradeRepository(db)

    def record_cash_flow(self, flow_type: FlowType, amount: float, flow_date: date, note: str | None = None) -> CashFlow:
        """Persist a manual deposit/withdrawal entry."""
        flow = CashFlow(flow_type=flow_type, amount=amount, flow_date=flow_date, note=note)
        self.db.add(flow)
        self.db.commit()
        self.db.refresh(flow)
        logger.info(f"Recorded cash flow: {flow_type.value} of {amount} on {flow_date}")
        return flow

    def get_cash_flows(self, start: date | None = None, end: date | None = None) -> list[CashFlow]:
        """Return cash flows ordered by date, optionally filtered to a date range."""
        query = self.db.query(CashFlow)
        if start:
            query = query.filter(CashFlow.flow_date >= start)
        if end:
            query = query.filter(CashFlow.flow_date <= end)
        return query.order_by(CashFlow.flow_date).all()

    def get_net_deposits(self, as_of_date: date | None = None) -> float:
        """Return cumulative deposits minus withdrawals up to and including as_of_date."""
        flows = self.get_cash_flows(end=as_of_date)
        net = 0.0
        for f in flows:
            net += float(f.amount) if f.flow_type == FlowType.DEPOSIT else -float(f.amount)
        return round(net, 2)

    # ------------------------------------------------------------------ #
    #  Daily account snapshot                                             #
    # ------------------------------------------------------------------ #

    def record_daily_snapshot(self, snapshot_date: date) -> AccountSnapshot:
        """Fetch live cash from Kite plus mark-to-market value of Atlas's own open trades, and upsert today's account value snapshot.

        Mark-to-market uses Atlas's open trades (not Kite's holdings() API) because Kite only
        reflects T+1 settled holdings — same-day CNC buys wouldn't show up there until tomorrow,
        which would understate the snapshot on the day a trade is entered.
        """
        margins = self.kite_service.get_margins()
        cash_balance = float(margins["equity"]["available"]["live_balance"])
        holdings_value = self._get_open_trades_value()
        total_value = cash_balance + holdings_value

        existing = self.db.query(AccountSnapshot).filter(AccountSnapshot.snapshot_date == snapshot_date).first()
        if existing:
            existing.cash_balance = cash_balance
            existing.holdings_value = holdings_value
            existing.total_value = total_value
            snapshot = existing
        else:
            snapshot = AccountSnapshot(snapshot_date=snapshot_date, cash_balance=cash_balance, holdings_value=holdings_value, total_value=total_value)
            self.db.add(snapshot)

        self.db.commit()
        self.db.refresh(snapshot)
        logger.info(f"Account snapshot for {snapshot_date}: cash={cash_balance}, holdings={holdings_value}, total={total_value}")
        return snapshot

    def _get_open_trades_value(self) -> float:
        """Mark-to-market value of all OPEN trades using live quotes, falling back to book value per trade."""
        open_trades = self.trade_repo.get_all_trades(status=TradeStatus.OPEN)
        if not open_trades:
            return 0.0

        tickers = [ f"{KITE_EXCHANGE}:{t.security.ticker}" for t in open_trades ]
        try:
            quotes = self.kite_service.get_quotes(tickers)
        except Exception:
            logger.warning("Failed to fetch live quotes for snapshot, falling back to book value.", exc_info=True)
            quotes = {}

        total = 0.0
        for t in open_trades:
            if not t.fill_price or not t.fill_quantity:
                continue
            kite_ticker = f"{KITE_EXCHANGE}:{t.security.ticker}"
            last_price = quotes.get(kite_ticker, {}).get("last_price")
            price = float(last_price) if last_price else float(t.fill_price)
            total += price * t.fill_quantity
        return round(total, 2)

    def get_snapshots(self, start: date | None = None, end: date | None = None) -> list[AccountSnapshot]:
        """Return account snapshots ordered by date, optionally filtered to a date range."""
        query = self.db.query(AccountSnapshot)
        if start:
            query = query.filter(AccountSnapshot.snapshot_date >= start)
        if end:
            query = query.filter(AccountSnapshot.snapshot_date <= end)
        return query.order_by(AccountSnapshot.snapshot_date).all()
