# backend/app/celery/tasks.py

from app.celery.base import AtlasTask, NotificationPolicy


class BrokerTokenRefreshTask(AtlasTask):
    display_name = "Broker Token Refresh"
    job_name = "KITE_TOKEN_REFRESH"


class SecuritiesImportTask(AtlasTask):
    display_name = "Securities Import"
    job_name = "SECURITIES_IMPORT"


class SecuritiesEnrichmentTask(AtlasTask):
    display_name = "Securities Enrichment"
    job_name = "SECURITIES_ENRICHMENT"


class OHLCVImportTask(AtlasTask):
    display_name = "OHLCV Import"
    job_name = "OHLCV_IMPORT"

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


class PositionSyncTask(AtlasTask):
    display_name = "Position Sync"
    job_name = "POSITION_SYNC"


class TradeEntryTask(AtlasTask):
    display_name = "Trade Entry"
    job_name = "TRADE_ENTRY"


class TradeExitTask(AtlasTask):
    display_name = "Trade Exit"
    job_name = "TRADE_EXIT"


class TradeReconciliationTask(AtlasTask):
    display_name = "Trade Reconciliation"
    job_name = "TRADE_RECONCILIATION"
