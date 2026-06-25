# backend/app/core/celery_schedule.py

from celery.schedules import crontab

beat_schedule = {
    "kite-daily-token-refresh-07:45": {
        "task": "app.jobs.refresh_broker_token.refresh_kite_token",
        "schedule": crontab(hour=7, minute=45)
    },
    "securities-daily-import-08:00": {
        "task": "app.jobs.securities_import.import_securities",
        "schedule": crontab(hour=8, minute=0)
    },
    "securities-monthly-enrichment-08:30": {
        "task": "app.jobs.enrich_securities.enrich_securities",
        "schedule": crontab(hour=8, minute=30, day_of_month="1")
    },
    "ohlcv-import-live-refresh": {
        "task": "app.jobs.ohlcv_import.import_ohlcv_data",
        "schedule": crontab(minute="*/5", hour="9-15", day_of_week="1-5"),
        "kwargs": {
            "type": "live_refresh"
        },
    },
    "feature-generation-live-refresh": {
        "task": "app.jobs.feature_generation.generate_features",
        "schedule": crontab(minute="2-59/5", hour="9-15", day_of_week="1-5"),
        "kwargs": {
            "type": "live_refresh",
            "timeframe": "1d"
        }
    },
    "ohlcv-daily-import-08:00": {
        "task": "app.jobs.ohlcv_import.import_ohlcv_data",
        "schedule": crontab(hour=8, minute=0, day_of_week="1-5"),
        "kwargs": {
            "type": "incremental",
            "timeframe": "1d"
        },
    },
    "feature-generation-daily-import-16:30": {
        "task": "app.jobs.feature_generation.generate_features",
        "schedule": crontab(hour=16, minute=30, day_of_week="1-5"),
        "kwargs": {
            "type": "incremental",
            "timeframe": "1d"
        }
    },
    "trade-position-sync-15:20": {
        "task": "app.jobs.position_sync.run_position_sync",
        "schedule": crontab(hour=15, minute=20, day_of_week="1-5"),
    },
    "trade-exit-15:25": {
        "task": "app.jobs.trade_exit.run_trade_exit",
        "schedule": crontab(hour=15, minute=25, day_of_week="1-5"),
        "kwargs": {
            "strategy_version_id": 2
        }
    },
    "trade-entry-15:27": {
        "task": "app.jobs.trade_entry.run_trade_entry",
        "schedule": crontab(hour=15, minute=27, day_of_week="1-5"),
        "kwargs": {
            "strategy_version_id": 2
        }
    },
    "trade-reconciliation-16:00": {
        "task": "app.jobs.trade_reconciliation.run_trade_reconciliation",
        "schedule": crontab(hour=16, minute=0, day_of_week="1-5"),
    }
}
