# backend/app/services/fund.py

from datetime import date

from sqlalchemy.orm import Session

from app.enums.fund import FlowType
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
        self._open_trades_quotes_cache: tuple[list, dict] | None = None

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

        cash_balance (available.live_balance) excludes margin currently blocked for open NRML
        positions (e.g. the iron condor) by definition — that capital hasn't vanished, it's
        collateral. Without adding it back, total_value understates the account by the full
        blocked-margin amount the moment any margin position opens, which reads as a huge false
        loss on the NAV curve and true-return calculation (caught live: a ~₹110K span+exposure
        block on 2026-08-18 made true_return_pct show -50% against a real realized P&L of -₹546).
        Using span+exposure specifically, not the broader utilised.debits, so this can never
        double-count against equity holdings tracked separately via _get_open_trades_value() —
        equity CNC purchases debit cash directly rather than blocking margin, so the two are
        already disjoint in practice, but this keeps that true structurally, not by coincidence.
        """
        margins = self.kite_service.get_margins()
        cash_balance = float(margins["equity"]["available"]["live_balance"])
        utilised = margins["equity"]["utilised"]
        blocked_margin = float(utilised.get("span", 0)) + float(utilised.get("exposure", 0))
        holdings_value = self._get_open_trades_value() + blocked_margin
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

    def _get_open_trades_with_quotes(self) -> tuple[list, dict]:
        """Fetch open trades plus a single batch of live quotes for them; cached per-instance so callers can share one Kite round-trip."""
        if self._open_trades_quotes_cache is not None:
            return self._open_trades_quotes_cache

        open_trades = self.trade_repo.get_open_trades()
        quotes: dict = {}
        if open_trades:
            tickers = [ f"{KITE_EXCHANGE}:{t.security.ticker}" for t in open_trades ]
            try:
                quotes = self.kite_service.get_quotes(tickers)
            except Exception:
                logger.warning("Failed to fetch live quotes for open trades, falling back to book value.", exc_info=True)

        self._open_trades_quotes_cache = (open_trades, quotes)
        return self._open_trades_quotes_cache

    def _get_open_trades_value(self) -> float:
        """Mark-to-market value of all OPEN trades using live quotes, falling back to book value per trade."""
        open_trades, quotes = self._get_open_trades_with_quotes()

        total = 0.0
        for t in open_trades:
            if not t.fill_price or not t.fill_quantity:
                continue
            kite_ticker = f"{KITE_EXCHANGE}:{t.security.ticker}"
            last_price = quotes.get(kite_ticker, {}).get("last_price")
            price = float(last_price) if last_price else float(t.fill_price)
            total += price * t.fill_quantity
        return round(total, 2)

    def _get_position_breakdown(self) -> list[dict]:
        """Per-position today's price move (LTP vs. previous close) for every OPEN trade."""
        open_trades, quotes = self._get_open_trades_with_quotes()

        rows = []
        for t in open_trades:
            kite_ticker = f"{KITE_EXCHANGE}:{t.security.ticker}"
            quote = quotes.get(kite_ticker, {})
            last_price = quote.get("last_price")
            prev_close = quote.get("ohlc", {}).get("close")
            if last_price is None or not prev_close:
                continue

            day_change = round(float(last_price) - float(prev_close), 2)
            day_change_pct = round(day_change / float(prev_close) * 100, 2)
            rows.append({ "ticker": t.security.ticker, "last_price": round(float(last_price), 2), "day_change": day_change, "day_change_pct": day_change_pct, })

        rows.sort(key=lambda r: r["day_change_pct"], reverse=True)
        return rows

    def build_daily_summary(self, snapshot: AccountSnapshot) -> dict:
        """Build day-over-day summary metrics (P&L, per-position breakdown, trades opened/closed) for the end-of-day notification."""
        snapshot_date = snapshot.snapshot_date
        previous = self.db.query(AccountSnapshot).filter(AccountSnapshot.snapshot_date < snapshot_date).order_by(AccountSnapshot.snapshot_date.desc()).first()

        day_pnl = None
        day_pnl_pct = None
        if previous:
            net_deposits_since = self.get_net_deposits(snapshot_date) - self.get_net_deposits(previous.snapshot_date)
            day_pnl = round(float(snapshot.total_value) - float(previous.total_value) - net_deposits_since, 2)
            if previous.total_value:
                day_pnl_pct = round(day_pnl / float(previous.total_value) * 100, 2)

        opened = self.trade_repo.get_trades_opened_on(snapshot_date)
        closed = self.trade_repo.get_trades_closed_on(snapshot_date)

        realized_pnl_today = round(sum((float(t.exit_price) - float(t.fill_price)) * t.fill_quantity for t in closed if t.exit_price and t.fill_price and t.fill_quantity), 2)
        open_trades, _ = self._get_open_trades_with_quotes()
        positions = self._get_position_breakdown()

        return { "day_pnl": day_pnl, "day_pnl_pct": day_pnl_pct, "open_positions": len(open_trades), "positions": positions, "trades_opened": [t.security.ticker for t in opened], "trades_closed": [t.security.ticker for t in closed], "realized_pnl_today": realized_pnl_today, }

    def get_snapshots(self, start: date | None = None, end: date | None = None) -> list[AccountSnapshot]:
        """Return account snapshots ordered by date, optionally filtered to a date range."""
        query = self.db.query(AccountSnapshot)
        if start:
            query = query.filter(AccountSnapshot.snapshot_date >= start)
        if end:
            query = query.filter(AccountSnapshot.snapshot_date <= end)
        return query.order_by(AccountSnapshot.snapshot_date).all()
