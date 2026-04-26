from sqlalchemy import create_engine, text
from config import settings
import json

e = create_engine(settings.DATABASE_URL, future=True)
with e.connect() as c:
    run_id = c.execute(text("select id from backtest_runs order by id desc limit 1")).scalar_one()
    print(f"RUN_ID={run_id}")
    
    summary = c.execute(text("select total_trades, total_return_pct, final_capital from backtest_runs where id=:id"), {"id": run_id}).fetchone()
    print(f"SUMMARY={summary}")
    
    counts = c.execute(text("select count(*) total, sum(case when ticker like '%FUT' then 1 else 0 end) fut_trades, sum(case when ticker like '%FUT' then 0 else 1 end) non_fut_trades from backtest_trades where backtest_run_id=:id"), {"id": run_id}).fetchone()
    print(f"TRADE_TYPE_COUNTS={counts}")
    
    sample = c.execute(text("select ticker, entry_signal, exit_signal, entry_features->>'signal_ticker' as signal_ticker from backtest_trades where backtest_run_id=:id order by id asc limit 20"), {"id": run_id}).fetchall()
    print(f"SAMPLE={sample}")
    
    roll = c.execute(text("select count(*) from backtest_trades where backtest_run_id=:id and (entry_signal='ROLL_OVER_ENTRY' or exit_signal='ROLL_OVER_EXIT')"), {"id": run_id}).scalar_one()
    print(f"ROLLOVER_EVENTS={roll}")
