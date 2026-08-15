# backend/app/core/celery_schedule.py

from celery.schedules import crontab

# Seeded by d4e8b6c2a9f3_seed_nifty_iron_condor_strategy (strategy_versions.id=3 in production).
IRON_CONDOR_STRATEGY_VERSION_ID = 3

beat_schedule = {
    "kite-daily-token-refresh-07:45": {
        "task": "app.jobs.refresh_broker_token.refresh_kite_token",
        "schedule": crontab(hour=7, minute=45)
    },
    "securities-monthly-import-08:00": {
        "task": "app.jobs.securities_import.import_securities",
        "schedule": crontab(hour=8, minute=0, day_of_month="1")
    },
    "securities-monthly-enrichment-08:30": {
        "task": "app.jobs.enrich_securities.enrich_securities",
        "schedule": crontab(hour=8, minute=30, day_of_month="1")
    },
    "ohlcv-import-live-refresh": {
        "task": "app.jobs.ohlcv_import.import_ohlcv_data",
        "schedule": crontab(minute="*/10", hour="9-15", day_of_week="1-5"),
        "kwargs": {
            "type": "live_refresh"
        },
    },
    "feature-generation-live-refresh": {
        "task": "app.jobs.feature_generation.generate_features",
        "schedule": crontab(minute="2-59/10", hour="9-15", day_of_week="1-5"),
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
    "trade-position-sync-15:15": {
        "task": "app.jobs.position_sync.run_position_sync",
        "schedule": crontab(hour=15, minute=15, day_of_week="1-5"),
    },
    # Momentum screener (strategy_version_id=2) — disabled 2026-08-14 at the user's request
    # in favour of the iron condor. All momentum positions were manually exited and
    # reconciled beforehand. Uncomment these three to resume it.
    # "strategy-execution-15:20": {
    #     "task": "app.jobs.strategy_execution.execute_strategy",
    #     "schedule": crontab(hour=15, minute=20, day_of_week="1-5"),
    #     "kwargs": {
    #         "strategy_version_id": 2
    #     }
    # },
    # "trade-exit-15:25": {
    #     "task": "app.jobs.trade_exit.run_trade_exit",
    #     "schedule": crontab(hour=15, minute=25, day_of_week="1-5"),
    #     "kwargs": {
    #         "strategy_version_id": 2
    #     }
    # },
    # "trade-entry-15:27": {
    #     "task": "app.jobs.trade_entry.run_trade_entry",
    #     "schedule": crontab(hour=15, minute=27, day_of_week="1-5"),
    #     "kwargs": {
    #         "strategy_version_id": 2
    #     }
    # },
    "trade-reconciliation-16:00": {
        "task": "app.jobs.trade_reconciliation.run_trade_reconciliation",
        "schedule": crontab(hour=16, minute=0, day_of_week="1-5"),
    },
    "daily-account-snapshot-16:05": {
        "task": "app.jobs.daily_account_snapshot.run_daily_account_snapshot",
        "schedule": crontab(hour=16, minute=5, day_of_week="1-5"),
    },
    # NIFTY iron condor — strategy_version_id below must match the row seeded by the
    # d4e8b6c2a9f3_seed_nifty_iron_condor_strategy migration (printed to migration output;
    # also queryable via `SELECT id FROM strategy_versions WHERE implementation_class =
    # 'nifty_iron_condor'`). Same manual-hardcode convention as the momentum screener's `2` above.
    "iron-condor-option-chain-import-08:10": {
        "task": "app.jobs.iron_condor_option_chain_import.import_iron_condor_option_chain",
        "schedule": crontab(hour=8, minute=10, day_of_week="1-5"),
    },
    "iron-condor-signal-15:21": {
        "task": "app.jobs.strategy_execution.execute_strategy",
        "schedule": crontab(hour=15, minute=21, day_of_week="1"),
        "kwargs": {
            "strategy_version_id": IRON_CONDOR_STRATEGY_VERSION_ID
        }
    },
    # Places real 4-leg orders. Enabled 2026-08-14 at the user's explicit request, fully
    # unattended from here on — including the first live entry, which will fire with nobody
    # watching whenever the next Monday-signal -> next-trading-day-open condition is met.
    #
    # Runs every 30 min through the trading day, not just once at open: run_entry() is
    # idempotent (no-ops instantly on every call once there's nothing to do), and a leg that's
    # still unfilled after one tick's dead-order check + same-tick retry (see options_trade.py
    # _fill_legs) needs a nearby follow-up rather than waiting a full day — a stuck PENDING
    # position with only its long wings filled is real unhedged exposure sitting in the market.
    "iron-condor-entry-09:20-to-14:50": {
        "task": "app.jobs.iron_condor_entry.run_iron_condor_entry",
        "schedule": crontab(minute="20,50", hour="9-14", day_of_week="1-5"),
        "kwargs": {
            "strategy_version_id": IRON_CONDOR_STRATEGY_VERSION_ID
        }
    },
    "iron-condor-exit-15:10": {
        "task": "app.jobs.iron_condor_exit.run_iron_condor_exit",
        "schedule": crontab(hour=15, minute=10, day_of_week="1-5"),
        "kwargs": {
            "strategy_version_id": IRON_CONDOR_STRATEGY_VERSION_ID
        }
    },
}
