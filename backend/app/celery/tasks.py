# backend/app/celery/tasks.py

from app.celery.base import AtlasTask, NotificationPolicy


class BrokerTokenRefreshTask(AtlasTask):
    display_name = "Broker Token Refresh"


class SecuritiesImportTask(AtlasTask):
    display_name = "Securities Import"


class SecuritiesEnrichmentTask(AtlasTask):
    display_name = "Securities Enrichment"


class OHLCVImportTask(AtlasTask):
    display_name = "OHLCV Import"

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

    def get_notification_policy(self, args: tuple, kwargs: dict) -> NotificationPolicy:
        task_type = kwargs.get("type")
        if task_type == "live_refresh":
            return NotificationPolicy.ON_FAILURE
        return NotificationPolicy.ON_SUCCESS_AND_FAILURE


class StrategyExecutionTask(AtlasTask):
    display_name = "Strategy Execution"


class PositionSyncTask(AtlasTask):
    display_name = "Position Sync"


class TradeEntryTask(AtlasTask):
    display_name = "Trade Entry"


class TradeExitTask(AtlasTask):
    display_name = "Trade Exit"


class TradeReconciliationTask(AtlasTask):
    display_name = "Trade Reconciliation"
