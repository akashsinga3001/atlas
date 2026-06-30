# backend/jobs/__init__.py
# Importing all job modules here ensures their register() calls run,
# populating the registry before JobService reads it.

from app.jobs import (refresh_broker_token, securities_import, enrich_securities, ohlcv_import, feature_generation, strategy_execution, trade_entry, trade_exit, trade_reconciliation, position_sync, daily_account_snapshot, )
