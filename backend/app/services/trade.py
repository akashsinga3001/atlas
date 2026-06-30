#  backend/app/services/trade.py

import time
from datetime import date, timedelta
from sqlalchemy.orm import Session
from typing import Optional

from app.enums.trade import TradeStatus, ExitReason
from app.enums.strategy import StrategyRunStatus
from app.exit_evaluators.context import ExitEvaluatorContext
from app.exit_evaluators.registry import ExitEvaluatorRegistry
from app.models.strategy import StrategyRun, StrategySignal, StrategyVersion
from app.models.trade import Trade, TradeSnapshot
from app.repositories.trade import TradeRepository, TradeSnapshotRepository
from app.schemas.base import APIResponse
from app.schemas.trade import TradeResponse, SecurityInfo
from app.services.brokers.kite import KiteService
from app.services.portfolio import PortfolioService
from app.services.feature import FeatureService
from app.utils.logger import get_logger

logger = get_logger(__name__)

KITE_EXCHANGE = "NSE"
KITE_PRODUCT = "CNC"
GTT_LIMIT_BUFFER = 0.98
ORDER_BUY_BUFFER = 1.002  # 0.2% above LTP to ensure fill
ORDER_SELL_BUFFER = 0.998  # 0.2% below LTP to ensure fill


class TradeService:

    def __init__(self, db: Session, kite_service: KiteService = None):
        """Initialise repositories and sub-services; kite_service is optional for read-only use."""
        self.db = db
        self.kite_service = kite_service
        self.trade_repo = TradeRepository(db)
        self.snapshot_repo = TradeSnapshotRepository(db)
        if kite_service:
            self.portfolio_service = PortfolioService(db, kite_service)
        self.feature_service = FeatureService(db)

    # ------------------------------------------------------------------ #
    #  Trade Listing                                                      #
    # ------------------------------------------------------------------ #

    def get_trades(self, status: Optional[TradeStatus] = None) -> list[dict]:
        """Return all trades, optionally filtered by status, as serialisable dicts."""
        trades = self.trade_repo.get_all_trades(status=status)
        return [self._build_trade_response(t) for t in trades]

    def _build_trade_response(self, trade) -> dict:
        """Compute derived fields (invested value, PnL) and serialise a trade to a dict."""
        invested = None
        pnl = None
        pnl_pct = None

        if trade.fill_price and trade.fill_quantity:
            invested = round(float(trade.fill_price) * trade.fill_quantity, 2)

        if trade.exit_price and trade.fill_price and trade.fill_quantity:
            pnl = round((float(trade.exit_price) - float(trade.fill_price)) * trade.fill_quantity, 2)
            pnl_pct = round((float(trade.exit_price) - float(trade.fill_price)) / float(trade.fill_price) * 100, 4)

        return TradeResponse(
            id=trade.id, security=SecurityInfo(id=trade.security.id, ticker=trade.security.ticker, display_name=trade.security.display_name, sector=trade.security.sector, industry=trade.security.industry,
                                               ), status=trade.status, entry_date=trade.entry_date, fill_price=float(trade.fill_price) if trade.fill_price else None, fill_quantity=trade.fill_quantity, timeout_date=trade.timeout_date, exit_date=trade.exit_date, exit_reason=trade.exit_reason, state=trade.state or {}, invested_value=invested, pnl=pnl, pnl_pct=pnl_pct,
        ).model_dump()

    # ------------------------------------------------------------------ #
    #  Entry Functions                                                    #
    # ------------------------------------------------------------------ #

    def open_trade(self, signal: StrategySignal, strategy_version: StrategyVersion, entry_date: date) -> Optional[Trade]:
        """Place a market buy order, poll for fill, create a GTT stop, and persist the trade."""
        ticker = signal.security.ticker
        position_size = self.portfolio_service.get_position_size(strategy_version)

        kite_ticker = f"{KITE_EXCHANGE}:{ticker}"
        quote = self.kite_service.get_quotes([kite_ticker])
        last_price = quote[kite_ticker]["last_price"]
        quantity = int(position_size // last_price)

        if quantity < 1:
            logger.warning(f"Skipping {ticker} - position size {position_size} too small for last price {last_price}")
            return None

        buy_price = self._round_to_tick(last_price * ORDER_BUY_BUFFER, signal.security.tick_size)
        order_id = self.kite_service.place_order(variety="regular", exchange=KITE_EXCHANGE, tradingsymbol=ticker, transaction_type="BUY", quantity=quantity, product=KITE_PRODUCT, order_type="LIMIT", price=buy_price, )
        logger.info(f"Placed Limit Buy Order for {ticker}, qty: {quantity}, price: {buy_price} (ltp: {last_price}), order_id: {order_id}")

        trade = Trade(strategy_signal_id=signal.id, strategy_version_id=strategy_version.id, security_id=signal.security_id, status=TradeStatus.PENDING, entry_date=entry_date, kite_entry_order_id=str(order_id), timeout_date=entry_date + timedelta(days=60), state={}, )
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)

        time.sleep(10)
        fill_price, fill_quantity = self._poll_fill(order_id)

        if fill_price is None:
            logger.error(f"Fill not confirmed for {ticker} order {order_id} - trade remains PENDING")
            return trade

        gtt_id = self._place_gtt(ticker, fill_price, fill_quantity, signal.security.tick_size)
        self.trade_repo.update(trade, { "status": TradeStatus.OPEN, "fill_price": fill_price, "fill_quantity": fill_quantity, "kite_gtt_id": str(gtt_id), })

        logger.info(f"Trade opened for {ticker}: fill={fill_price}, qty={fill_quantity}, gtt={gtt_id}")
        return trade

    def _round_to_tick(self, price: float, tick_size: float | None) -> float:
        """Round a price to the nearest valid tick size for the instrument."""
        if not tick_size:
            return round(price, 2)
        ticks = round(price / float(tick_size))
        return round(ticks * float(tick_size), 2)

    def _poll_fill(self, order_id: str) -> tuple[float | None, int | None]:
        """Fetch order trades from Kite and return volume-weighted average fill price and quantity."""
        try:
            trades = self.kite_service.get_order_trades(order_id)
            if not trades:
                return None, None
            fill_quantity = sum(trade["quantity"] for trade in trades)
            fill_price = sum(trade["price"] * trade["quantity"] for trade in trades) / fill_quantity
            return round(fill_price, 4), fill_quantity
        except Exception as e:
            logger.error(f"Error polling fill for order {order_id}: {e}", exc_info=True)
            return None, None

    def _place_gtt(self, ticker: str, trigger_price: float, quantity: int, tick_size: float | None = None) -> str:
        """Place a single-leg GTT stop-loss order at trigger_price with a limit buffer."""
        limit_price = self._round_to_tick(trigger_price * GTT_LIMIT_BUFFER, tick_size)
        return self.kite_service.place_gtt(trigger_type="single", tradingsymbol=ticker, exchange=KITE_EXCHANGE, trigger_values=[trigger_price], last_price=trigger_price, orders=[{ "transaction_type": "SELL", "quantity": quantity, "product": KITE_PRODUCT, "order_type": "LIMIT", "price": limit_price, }], )

    # ------------------------------------------------------------------ #
    #  Exit Evaluation                                                    #
    # ------------------------------------------------------------------ #

    def evaluate_exits(self, strategy_version: StrategyVersion, as_of_date: date) -> dict:
        """Run the exit evaluator on every open trade and execute any triggered exits or GTT updates."""
        evaluator_class = ExitEvaluatorRegistry.get(strategy_version.exit_evaluator_class)
        evaluator = evaluator_class()

        open_trades = self.trade_repo.get_open_trades_for_strategy_version(strategy_version.id)
        timed_out = {t.id for t in self.trade_repo.get_timed_out_trades(as_of_date)}

        exits_triggered: list[str] = []
        stops_updated: list[str] = []
        breakeven_crossings: list[str] = []

        for trade in open_trades:
            ticker = trade.security.ticker

            if trade.id in timed_out:
                logger.info(f"Trade {trade.id} for {ticker} has timed out - closing trade")
                self._close_timeout(trade, as_of_date)
                exits_triggered.append(f"{ticker} (TIMEOUT)")
                continue

            kite_ticker = f"{KITE_EXCHANGE}:{ticker}"
            quote = self.kite_service.get_quotes([kite_ticker])
            close_price = quote[kite_ticker]["last_price"]
            features = self.feature_service.get_latest_features_for_security(trade.security_id)

            context = ExitEvaluatorContext(trade=trade, as_of_date=as_of_date, close_price=close_price, features=features)
            decision = evaluator.evaluate(context)

            new_state = { **trade.state, **decision.state_update }
            self.trade_repo.update(trade, { "state": new_state })
            self._write_snapshot(trade, as_of_date, close_price, decision.snapshot_state, exit_triggered=decision.should_exit)

            if decision.should_exit:
                logger.info(f"Exit triggered for trade {trade.id} ({ticker}) - reason: {decision.exit_reason}")
                self._close_trade(trade, as_of_date, close_price, decision.exit_reason)
                exits_triggered.append(f"{ticker} ({decision.exit_reason.value if decision.exit_reason else 'STOP'})")
            else:
                new_stop = decision.state_update.get("current_stop")
                if new_stop and trade.kite_gtt_id:
                    logger.info(f"Updating GTT stop for trade {trade.id} ({ticker}) to {new_stop}")
                    self._update_gtt(trade, new_stop)
                    stops_updated.append(ticker)
                    self._check_breakeven_crossing(trade, ticker, new_stop, close_price, breakeven_crossings)

        return { "trades_evaluated": len(open_trades), "exits_triggered": len(exits_triggered), "stops_updated": len(stops_updated), "breakeven_crossings": len(breakeven_crossings), "exit_details": exits_triggered, "breakeven_tickers": breakeven_crossings, }

    def _check_breakeven_crossing(self, trade: Trade, ticker: str, new_stop: float, close_price: float, breakeven_crossings: list[str]) -> None:
        """Detect when the trailing stop crosses above entry price and fire a Discord alert."""
        prev_stop = trade.state.get("current_stop") if trade.state else None
        fill = float(trade.fill_price) if trade.fill_price else None
        if fill and new_stop > fill and (prev_stop is None or prev_stop <= fill):
            logger.info(f"TSL breakeven crossing for {ticker}: stop ₹{new_stop:.2f} > entry ₹{fill:.2f}")
            breakeven_crossings.append(ticker)
            self._send_breakeven_alert(ticker, fill, new_stop, close_price)

    def _send_breakeven_alert(self, ticker: str, entry: float, stop: float, close: float) -> None:
        """Send a Discord notification when a trade's stop has moved above its entry price."""
        try:
            from app.celery.base import get_discord_service
            from app.schemas.notification import NotificationPayload, NotificationMetric
            discord = get_discord_service()
            if not discord:
                return
            upside_pct = round((close - entry) / entry * 100, 2)
            payload = NotificationPayload(
                operation="TSL Breakeven Alert", status="success", duration_seconds=0, summary=f"{ticker} stop is now above entry — worst case is breakeven exit.", results=[NotificationMetric(label="Ticker", value=ticker),
                                                                                                                                                                             NotificationMetric(label="Entry Price", value=f"₹{entry:.2f}"),
                                                                                                                                                                             NotificationMetric(label="New Stop", value=f"₹{stop:.2f}"),
                                                                                                                                                                             NotificationMetric(label="Current Price", value=f"₹{close:.2f}"),
                                                                                                                                                                             NotificationMetric(label="Upside", value=f"+{upside_pct}%"), ], action_required=["Trade is locked in at breakeven or better. No action needed."],
            )
            discord.send_notification(payload)
        except Exception as exc:
            logger.warning(f"Failed to send breakeven alert for {ticker}: {exc}")

    def _close_timeout(self, trade: Trade, as_of_date: date) -> None:
        """Cancel the GTT, place a market sell, and close the trade with a TIMEOUT reason."""
        ticker = trade.security.ticker
        logger.info(f"Timeout exit for {ticker} trade {trade.id}")

        if trade.kite_gtt_id:
            try:
                self.kite_service.delete_gtt(int(trade.kite_gtt_id))
            except Exception as e:
                logger.error(f"Failed to delete GTT for trade {trade.id} ({ticker}): {e}")

        kite_ticker = f"{KITE_EXCHANGE}:{ticker}"
        quote = self.kite_service.get_quotes([kite_ticker])
        exit_price = quote[kite_ticker]["last_price"]

        sell_price = self._round_to_tick(exit_price * ORDER_SELL_BUFFER, trade.security.tick_size)
        self.kite_service.place_order(variety="regular", exchange=KITE_EXCHANGE, tradingsymbol=ticker, transaction_type="SELL", quantity=trade.fill_quantity, product=KITE_PRODUCT, order_type="LIMIT", price=sell_price, )
        logger.info(f"Placed Limit Sell Order for {ticker}, qty: {trade.fill_quantity}, price: {sell_price} (ltp: {exit_price})")

        self._write_snapshot(trade, as_of_date, exit_price, {}, exit_triggered=True)
        self._close_trade(trade, as_of_date, exit_price, ExitReason.TIMEOUT)

    def _update_gtt(self, trade: Trade, new_stop: float) -> None:
        """Modify the existing GTT trigger price to reflect the updated trailing stop."""
        ticker = trade.security.ticker
        limit_price = self._round_to_tick(new_stop * GTT_LIMIT_BUFFER, trade.security.tick_size)
        try:
            self.kite_service.modify_gtt(trigger_id=int(trade.kite_gtt_id), trigger_type="single", tradingsymbol=ticker, exchange=KITE_EXCHANGE, trigger_values=[new_stop], last_price=new_stop, orders=[{ "transaction_type": "SELL", "quantity": trade.fill_quantity, "product": KITE_PRODUCT, "order_type": "LIMIT", "price": limit_price, }], )
            logger.info(f"Updated GTT for {ticker} trade {trade.id} — new stop: {new_stop}")
        except Exception as exc:
            logger.error(f"Failed to update GTT {trade.kite_gtt_id} for {ticker}: {exc}", exc_info=True)

    def _close_trade(self, trade: Trade, exit_date: date, exit_price: float, exit_reason: ExitReason) -> None:
        """Mark the trade as CLOSED and persist exit details."""
        self.trade_repo.update(trade, { "status": TradeStatus.CLOSED, "exit_date": exit_date, "exit_price": exit_price, "exit_reason": exit_reason, "kite_gtt_id": None, })
        logger.info(f"Trade {trade.id} closed — reason={exit_reason.value}, price={exit_price}")

    # ------------------------------------------------------------------ #
    #  High-level Job Entry Points                                        #
    # ------------------------------------------------------------------ #

    def run_entry(self, strategy_version: StrategyVersion, as_of_date: date, allow_stale_signals: bool = False) -> APIResponse:
        """Evaluate pending signals and open new trades up to the available slot count."""
        try:
            available_slots = self.portfolio_service.get_available_slots(strategy_version)
            if available_slots < 1:
                return APIResponse(success=True, message="NO_SLOTS_AVAILABLE", data={ "trades_opened": 0, "tickers": [] })

            latest_run = (self.db.query(StrategyRun).filter(StrategyRun.strategy_version_id == strategy_version.id).order_by(StrategyRun.id.desc()).first())
            if not latest_run or not latest_run.signals:
                return APIResponse(success=True, message="NO_SIGNALS", data={ "trades_opened": 0, "tickers": [] })

            if latest_run.status != StrategyRunStatus.COMPLETED:
                logger.warning(f"Latest strategy run {latest_run.id} for version {strategy_version.id} is not COMPLETED (status={latest_run.status}). Skipping entry.")
                return APIResponse(success=True, message="LATEST_RUN_NOT_COMPLETED", data={ "trades_opened": 0, "tickers": [] })

            run_date = (latest_run.completed_at or latest_run.started_at).date() if (latest_run.completed_at or latest_run.started_at) else None
            if run_date != as_of_date and not allow_stale_signals:
                logger.warning(f"Latest strategy run {latest_run.id} for version {strategy_version.id} is dated {run_date}, not today ({as_of_date}). Skipping entry to avoid trading on stale signals.")
                return APIResponse(success=True, message="STALE_SIGNALS_SKIPPED", data={ "trades_opened": 0, "tickers": [] })
            elif run_date != as_of_date:
                logger.warning(f"Proceeding with entry on stale signals from {run_date} (allow_stale_signals=True), strategy run {latest_run.id}.")

            signals: list[StrategySignal] = sorted(latest_run.signals, key=lambda s: s.security.ticker)
            trades_opened = 0
            opened_tickers: list[str] = []

            for signal in signals:
                if trades_opened >= available_slots:
                    break
                existing = self.trade_repo.get_by_security_and_status(signal.security_id, TradeStatus.OPEN)
                pending = self.trade_repo.get_by_security_and_status(signal.security_id, TradeStatus.PENDING)
                if existing or pending:
                    logger.info(f"Skipping {signal.security.ticker} — already have an open/pending trade")
                    continue
                trade = self.open_trade(signal=signal, strategy_version=strategy_version, entry_date=as_of_date)
                if trade:
                    trades_opened += 1
                    opened_tickers.append(signal.security.ticker)

            return APIResponse(success=True, message="TRADE_ENTRY_COMPLETED", data={ "trades_opened": trades_opened, "tickers": opened_tickers })
        except Exception as exc:
            logger.error(f"Trade entry failed for strategy version {strategy_version.id}: {exc}", exc_info=True)
            return APIResponse(success=False, message=str(exc))

    def run_exit_evaluation(self, strategy_version: StrategyVersion, as_of_date: date) -> APIResponse:
        """Run exit evaluation for all open trades under the given strategy version."""
        try:
            summary = self.evaluate_exits(strategy_version=strategy_version, as_of_date=as_of_date)
            return APIResponse(success=True, message="TRADE_EXIT_COMPLETED", data=summary)
        except Exception as exc:
            logger.error(f"Trade exit evaluation failed for strategy version {strategy_version.id}: {exc}", exc_info=True)
            return APIResponse(success=False, message=str(exc))

    def run_position_sync(self, as_of_date: date) -> APIResponse:
        """Sync Kite holdings against open trades, close GTT-triggered exits, and check drawdown."""
        try:
            summary = self.sync_positions(as_of_date=as_of_date)
            self._check_portfolio_drawdown(threshold_pct=5.0)
            return APIResponse(success=True, message="POSITION_SYNC_COMPLETED", data=summary)
        except Exception as exc:
            logger.error(f"Position sync failed: {exc}", exc_info=True)
            return APIResponse(success=False, message=str(exc))

    def run_reconciliation(self) -> APIResponse:
        """Resolve PENDING trades whose fills weren't confirmed at entry time."""
        try:
            pending_trades = self.trade_repo.get_pending_trades()
            resolved = 0

            for trade in pending_trades:
                ticker = trade.security.ticker
                try:
                    fill_price, fill_quantity = self._poll_fill(trade.kite_entry_order_id)
                    if fill_price is None:
                        logger.warning(f"Reconciliation: fill still not confirmed for trade {trade.id} ({ticker})")
                        continue
                    gtt_id = self._place_gtt(ticker, fill_price, fill_quantity, trade.security.tick_size)
                    self.trade_repo.update(trade, { "status": TradeStatus.OPEN, "fill_price": fill_price, "fill_quantity": fill_quantity, "kite_gtt_id": str(gtt_id), })
                    resolved += 1
                    logger.info(f"Reconciliation: resolved PENDING trade {trade.id} ({ticker})")
                except Exception as exc:
                    logger.error(f"Reconciliation failed for trade {trade.id} ({ticker}): {exc}", exc_info=True)

            return APIResponse(success=True, message="TRADE_RECONCILIATION_COMPLETED", data={ "resolved": resolved })
        except Exception as exc:
            logger.error(f"Trade reconciliation failed: {exc}", exc_info=True)
            return APIResponse(success=False, message=str(exc))

    # ------------------------------------------------------------------ #
    #  Position Sync                                                      #
    # ------------------------------------------------------------------ #

    def sync_positions(self, as_of_date: date) -> dict:
        """Detect GTT-triggered exits by comparing Kite holdings against open trades in DB."""
        holdings = self.kite_service.get_holdings()
        held_tickers = {h["tradingsymbol"] for h in holdings}
        open_trades = self.trade_repo.get_open_trades()
        closed_tickers: list[str] = []

        for trade in open_trades:
            ticker = trade.security.ticker
            if ticker not in held_tickers:
                logger.info(f"Position gone for {ticker} trade {trade.id} - marking as ATR_STOP exit")
                kite_ticker = f"{KITE_EXCHANGE}:{ticker}"
                quote = self.kite_service.get_quotes([kite_ticker])
                exit_price = quote[kite_ticker]["last_price"]
                self._close_trade(trade, as_of_date, exit_price, ExitReason.ATR_STOP)
                closed_tickers.append(ticker)

        return { "exits_detected": len(closed_tickers), "closed_tickers": closed_tickers, "remaining_open": len(open_trades) - len(closed_tickers), }

    def _check_portfolio_drawdown(self, threshold_pct: float = 5.0) -> None:
        """Alert via Discord if cumulative P&L has fallen more than threshold_pct from its peak."""
        try:
            from app.enums.trade import TradeStatus
            all_trades = self.trade_repo.get_all_trades()
            closed_trades = [ t for t in all_trades if t.status == TradeStatus.CLOSED and t.exit_price and t.fill_price and t.fill_quantity ]

            cumulative = 0.0
            peak = 0.0
            for t in sorted(closed_trades, key=lambda x: x.exit_date or x.entry_date):
                pnl = (float(t.exit_price) - float(t.fill_price)) * t.fill_quantity
                cumulative += pnl
                if cumulative > peak:
                    peak = cumulative

            if peak <= 0:
                return

            current_dd_pct = (peak - cumulative) / peak * 100
            if current_dd_pct < threshold_pct:
                return

            logger.warning(f"Portfolio drawdown alert: {current_dd_pct:.1f}% below peak ₹{peak:,.0f}")
            self._send_drawdown_alert(peak=peak, current=cumulative, drawdown_pct=current_dd_pct, threshold_pct=threshold_pct)
        except Exception as exc:
            logger.warning(f"Portfolio drawdown check failed: {exc}")

    def _send_drawdown_alert(self, peak: float, current: float, drawdown_pct: float, threshold_pct: float) -> None:
        """Send a Discord notification when portfolio drawdown breaches the given threshold."""
        try:
            from app.celery.base import get_discord_service
            from app.schemas.notification import NotificationPayload, NotificationMetric
            discord = get_discord_service()
            if not discord:
                return
            payload = NotificationPayload(
                operation="Portfolio Drawdown Alert", status="warning", duration_seconds=0, summary=f"Portfolio is {drawdown_pct:.1f}% below its peak — breach of {threshold_pct:.0f}% threshold.", results=[NotificationMetric(label="Peak P&L", value=f"₹{peak:,.0f}"),
                                                                                                                                                                                                             NotificationMetric(label="Current P&L", value=f"₹{current:,.0f}"),
                                                                                                                                                                                                             NotificationMetric(label="Drawdown", value=f"-{drawdown_pct:.1f}%"),
                                                                                                                                                                                                             NotificationMetric(label="Threshold", value=f"-{threshold_pct:.0f}%"), ], action_required=["Review open positions and assess risk exposure."],
            )
            discord.send_notification(payload)
        except Exception as exc:
            logger.warning(f"Failed to send drawdown alert: {exc}")

    # ------------------------------------------------------------------ #
    #  Snapshot                                                           #
    # ------------------------------------------------------------------ #

    def _write_snapshot(self, trade: Trade, snapshot_date: date, close_price: float, state: dict, exit_triggered: bool) -> None:
        """Persist a daily trade snapshot; skips if one already exists for this date."""
        existing = self.snapshot_repo.get_for_trade_on_date(trade.id, snapshot_date)
        if existing:
            return

        days_held = (snapshot_date - trade.entry_date).days
        mtm_pct = round((close_price - float(trade.fill_price)) / float(trade.fill_price) * 100, 4)

        snapshot = TradeSnapshot(trade_id=trade.id, snapshot_date=snapshot_date, close_price=close_price, mtm_pct=mtm_pct, days_held=days_held, exit_triggered=exit_triggered, state=state, )
        self.db.add(snapshot)
        self.db.commit()
