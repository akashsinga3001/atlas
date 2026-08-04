# backend/app/celery/tasks.py

from app.celery.base import AtlasTask, NotificationPolicy
from app.schemas.notification import NotificationPayload, NotificationMetric


class BrokerTokenRefreshTask(AtlasTask):
    display_name = "Broker Token Refresh"
    job_name = "KITE_TOKEN_REFRESH"


class SecuritiesImportTask(AtlasTask):
    display_name = "Securities Import"
    job_name = "SECURITIES_IMPORT"
    soft_time_limit = 3600  # 1 hour
    time_limit = 3660


class SecuritiesEnrichmentTask(AtlasTask):
    display_name = "Securities Enrichment"
    job_name = "SECURITIES_ENRICHMENT"
    soft_time_limit = 39600  # 11 hours — enriches 500 securities via yfinance
    time_limit = 39660


class OHLCVImportTask(AtlasTask):
    display_name = "OHLCV Import"
    job_name = "OHLCV_IMPORT"
    soft_time_limit = 39600  # 11 hours — historical backfill across 500 securities
    time_limit = 39660

    def get_notification_policy(self, args: tuple, kwargs: dict) -> NotificationPolicy:
        task_type = kwargs.get("type")
        if task_type == "live_refresh":
            return NotificationPolicy.ON_FAILURE
        return NotificationPolicy.ON_SUCCESS_AND_FAILURE

    def get_display_name(self, kwargs: dict) -> str:
        task_type = kwargs.get("type")
        if task_type == "historical":
            return "OHLCV Historical Import"
        if task_type == "incremental":
            return "OHLCV Incremental Sync"
        if task_type == "live_refresh":
            return "OHLCV Live Refresh"
        return self.display_name


class FeatureGenerationTask(AtlasTask):
    display_name = "Feature Generation"
    job_name = "FEATURE_GENERATION"

    def get_notification_policy(self, args: tuple, kwargs: dict) -> NotificationPolicy:
        task_type = kwargs.get("type")
        if task_type == "live_refresh":
            return NotificationPolicy.ON_FAILURE
        return NotificationPolicy.ON_SUCCESS_AND_FAILURE


class StrategyExecutionTask(AtlasTask):
    display_name = "Strategy Execution"
    job_name = "STRATEGY_EXECUTION"

    def build_success_notification(self, duration_seconds: float, result: dict, args, kwargs) -> NotificationPayload:
        data = (result or {}).get("data", {})
        signals_count = data.get("signals_count", 0)
        tickers = data.get("tickers", [])

        summary = f"{signals_count} signal{'s' if signals_count != 1 else ''} generated."
        metrics = [NotificationMetric(label="Signals", value=str(signals_count))]
        if tickers:
            metrics.append(NotificationMetric(label="Tickers", value=", ".join(tickers)))

        return NotificationPayload(operation=self.get_display_name(kwargs), status="success", duration_seconds=duration_seconds, summary=summary, results=metrics, )


class PositionSyncTask(AtlasTask):
    display_name = "Position Sync"
    job_name = "POSITION_SYNC"

    def build_success_notification(self, duration_seconds: float, result: dict, args, kwargs) -> NotificationPayload:
        data = (result or {}).get("data", {})
        exits = data.get("exits_detected", 0)
        closed_tickers = data.get("closed_tickers", [])
        remaining = data.get("remaining_open", 0)
        gap_down_recoveries = data.get("gap_down_recoveries", [])

        if exits == 0:
            summary = f"No GTT exits detected. {remaining} position{'s' if remaining != 1 else ''} still open."
        else:
            summary = f"{exits} GTT exit{'s' if exits != 1 else ''} detected. {remaining} position{'s' if remaining != 1 else ''} remaining."

        metrics = [NotificationMetric(label="Exits Detected", value=str(exits)), NotificationMetric(label="Remaining Open", value=str(remaining)), ]
        if closed_tickers:
            metrics.append(NotificationMetric(label="Closed", value=", ".join(closed_tickers)))

        action_required = []
        if gap_down_recoveries:
            metrics.append(NotificationMetric(label="Gap-Down Recovery", value=", ".join(gap_down_recoveries)))
            action_required.append(f"Gap-down exit triggered for: {', '.join(gap_down_recoveries)} — verify fills in Kite.")

        return NotificationPayload(operation=self.get_display_name(kwargs), status="success", duration_seconds=duration_seconds, summary=summary, results=metrics, action_required=action_required, )


class TradeEntryTask(AtlasTask):
    display_name = "Trade Entry"
    job_name = "TRADE_ENTRY"

    def build_success_notification(self, duration_seconds: float, result: dict, args, kwargs) -> NotificationPayload:
        data = (result or {}).get("data", {})
        trades_opened = data.get("trades_opened", 0)
        trades = data.get("trades", [])
        message = (result or {}).get("message", "")

        if message == "NO_SLOTS_AVAILABLE":
            summary = "No available slots — all positions filled."
        elif message == "NO_SIGNALS":
            summary = "No signals to act on."
        elif trades_opened == 0:
            summary = "No trades opened."
        else:
            summary = f"{trades_opened} trade{'s' if trades_opened != 1 else ''} opened."

        metrics = [NotificationMetric(label="Trades Opened", value=str(trades_opened))]
        for t in trades:
            ticker = t.get("ticker", "?")
            if t.get("status") == "pending":
                metrics.append(NotificationMetric(label=ticker, value="Order placed — fill not yet confirmed"))
                continue
            fill_price = t.get("fill_price")
            qty = t.get("fill_quantity")
            stop = t.get("stop_loss")
            parts = []
            if fill_price is not None:
                parts.append(f"Entry ₹{fill_price:.2f}")
            if qty is not None:
                parts.append(f"Qty {qty}")
            if stop is not None:
                parts.append(f"SL ₹{stop:.2f}")
            metrics.append(NotificationMetric(label=ticker, value=" · ".join(parts) if parts else "—"))

        return NotificationPayload(operation=self.get_display_name(kwargs), status="success", duration_seconds=duration_seconds, summary=summary, results=metrics, )


class TradeExitTask(AtlasTask):
    display_name = "Trade Exit"
    job_name = "TRADE_EXIT"

    def build_success_notification(self, duration_seconds: float, result: dict, args, kwargs) -> NotificationPayload:
        data = (result or {}).get("data", {})
        evaluated = data.get("trades_evaluated", 0)
        exits = data.get("exits_triggered", 0)
        stops = data.get("stops_updated", 0)
        breakevens = data.get("breakeven_crossings", 0)
        exit_details = data.get("exit_details", [])
        breakeven_tickers = data.get("breakeven_tickers", [])

        parts = []
        if exits:
            parts.append(f"{exits} exit{'s' if exits != 1 else ''} triggered")
        if stops:
            parts.append(f"{stops} stop{'s' if stops != 1 else ''} updated")
        if breakevens:
            parts.append(f"{breakevens} breakeven crossing{'s' if breakevens != 1 else ''}")
        summary = ", ".join(parts) + "." if parts else f"{evaluated} trades evaluated, no changes."

        metrics = [NotificationMetric(label="Evaluated", value=str(evaluated)), NotificationMetric(label="Exits", value=str(exits)), NotificationMetric(label="Stops Updated", value=str(stops)), ]
        if exit_details:
            metrics.append(NotificationMetric(label="Exited", value=", ".join(exit_details)))
        if breakeven_tickers:
            metrics.append(NotificationMetric(label="Breakeven", value=", ".join(breakeven_tickers)))

        action_required = []
        if breakeven_tickers:
            action_required.append(f"TSL above entry for: {', '.join(breakeven_tickers)} — locked in at breakeven or better.")

        return NotificationPayload(operation=self.get_display_name(kwargs), status="success", duration_seconds=duration_seconds, summary=summary, results=metrics, action_required=action_required, )


class TradeReconciliationTask(AtlasTask):
    display_name = "Trade Reconciliation"
    job_name = "TRADE_RECONCILIATION"

    def build_success_notification(self, duration_seconds: float, result: dict, args, kwargs) -> NotificationPayload:
        data = (result or {}).get("data", {})
        resolved = data.get("resolved", 0)
        summary = f"{resolved} pending trade{'s' if resolved != 1 else ''} reconciled." if resolved else "No pending trades to reconcile."

        return NotificationPayload(operation=self.get_display_name(kwargs), status="success", duration_seconds=duration_seconds, summary=summary, results=[NotificationMetric(label="Resolved", value=str(resolved))], )


def _format_positions_table(positions: list[dict]) -> str:
    """Render per-position LTP / day change / day change % as a monospace Discord table."""
    header = f"{'Ticker':<11}{'LTP':>10}{'Chg':>10}{'Chg %':>9}"
    lines = [ header, "-" * len(header) ]
    for p in positions:
        ticker = p["ticker"][:10]
        chg_str = f"{p['day_change']:+,.2f}"
        pct_str = f"{p['day_change_pct']:+.2f}%"
        lines.append(f"{ticker:<11}{p['last_price']:>10,.2f}{chg_str:>10}{pct_str:>9}")
    return "```\n" + "\n".join(lines) + "\n```"


class DailyAccountSnapshotTask(AtlasTask):
    display_name = "Daily Summary"
    job_name = "DAILY_ACCOUNT_SNAPSHOT"

    def build_success_notification(self, duration_seconds: float, result: dict, args, kwargs) -> NotificationPayload:
        data = (result or {}).get("data", {})
        total_value = data.get("total_value")
        day_pnl = data.get("day_pnl")
        day_pnl_pct = data.get("day_pnl_pct")
        positions = data.get("positions", [])
        trades_opened = data.get("trades_opened", [])
        trades_closed = data.get("trades_closed", [])
        realized_pnl_today = data.get("realized_pnl_today", 0)

        if total_value is not None:
            summary = f"Total value ₹{total_value:,.2f}"
            if day_pnl is not None:
                pct_suffix = f", {day_pnl_pct:+.2f}%" if day_pnl_pct is not None else ""
                summary += f" ({day_pnl:+,.2f}{pct_suffix} today)"
        else:
            summary = "Account snapshot recorded."

        metrics = [NotificationMetric(label="Total Value", value=f"₹{data.get('total_value', 0):,.2f}"), NotificationMetric(label="Cash", value=f"₹{data.get('cash_balance', 0):,.2f}"), NotificationMetric(label="Holdings", value=f"₹{data.get('holdings_value', 0):,.2f}"), ]
        if day_pnl is not None:
            metrics.append(NotificationMetric(label="Daily Change", value=f"₹{day_pnl:+,.2f}"))
        if day_pnl_pct is not None:
            metrics.append(NotificationMetric(label="Daily Change (%)", value=f"{day_pnl_pct:+.2f}%"))
        metrics.append(NotificationMetric(label="Open Positions", value=str(data.get("open_positions", 0))))

        if positions:
            metrics.append(NotificationMetric(label="📊 Positions", value=_format_positions_table(positions)))

        if trades_opened:
            metrics.append(NotificationMetric(label="Opened Today", value=", ".join(trades_opened)))
        if trades_closed:
            metrics.append(NotificationMetric(label="Closed Today", value=", ".join(trades_closed)))
            metrics.append(NotificationMetric(label="Realized P&L Today", value=f"₹{realized_pnl_today:+,.2f}"))

        return NotificationPayload(operation=self.get_display_name(kwargs), status="success", duration_seconds=duration_seconds, summary=summary, results=metrics, )
