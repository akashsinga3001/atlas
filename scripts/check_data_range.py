"""Quick script to check available data range and feature completeness."""
from sqlalchemy import create_engine, text
from config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as c:
    r = c.execute(text("SELECT MIN(candle_date), MAX(candle_date), COUNT(DISTINCT candle_date), COUNT(DISTINCT security_id) FROM ohlcv WHERE timeframe='1DAY'")).one()
    print(f"OHLCV 1DAY: min={r[0]} max={r[1]} trading_days={r[2]} securities={r[3]}")

    r2 = c.execute(text("SELECT MIN(candle_date), MAX(candle_date), COUNT(*) FROM ohlcv WHERE timeframe='1DAY' AND security_id IN (SELECT id FROM securities WHERE type='EQ' AND is_active=true)")).one()
    print(f"Active EQ: min={r2[0]} max={r2[1]} rows={r2[2]}")

    r3 = c.execute(text("SELECT COUNT(*) FROM features WHERE rsi_14 IS NOT NULL")).one()
    r4 = c.execute(text("SELECT COUNT(*) FROM features")).one()
    print(f"Features: total={r4[0]} with_rsi={r3[0]}")

    r5 = c.execute(text("SELECT candle_date, COUNT(DISTINCT security_id) as n FROM ohlcv WHERE timeframe='1DAY' GROUP BY candle_date ORDER BY candle_date")).fetchall()
    years = {}
    for row in r5:
        y = str(row[0])[:4]
        years[y] = years.get(y, 0) + 1
    print("Trading days per year:", dict(sorted(years.items())))
