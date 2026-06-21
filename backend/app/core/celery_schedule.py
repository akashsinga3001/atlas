# backend/app/core/celery_schedule.py

from celery.schedules import crontab

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
            "type": "incremental"
        }
    },
    "ohlcv-daily-import-16:00": {
        "task": "app.jobs.ohlcv_import.import_ohlcv_data",
        "schedule": crontab(hour=16, minute=0, day_of_week="1-5"),
        "kwargs": {
            "type": "incremental",
            "timeframe": "1d"
        },
    },
    "feature-generation-daily-import-16:30": {
        "task": "app.jobs.feature_generation.generate_features",
        "schedule": crontab(hour=16, minute=30, day_of_week="1-5"),
        "kwargs": {
            "type": "incremental"
        }
    }
}
