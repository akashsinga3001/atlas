"""
Reopen trades incorrectly closed as MANUAL exits due to t1_quantity bug.

What happened:
    The manual exit detection in sync_positions used only h["quantity"] from Kite holdings.
    CNC trades entered on T-1 show quantity=0 / t1_quantity>0 until settlement completes,
    causing them to be falsely detected as manual exits and closed.

What this script does:
    1. Finds all trades closed with exit_reason=MANUAL on the affected date.
    2. For each trade, checks if LTP is still above the stored stop — if so, re-places the GTT
       and reopens the trade. If LTP has already dropped below the stop, prints a warning and
       skips (requires manual decision).
    3. Deletes the incorrect exit TradeSnapshot for the affected date.
    4. Restores trade to OPEN status.

Usage:
    cd backend
    python -m scripts.reopen_false_manual_exits               # defaults to yesterday
    python -m scripts.reopen_false_manual_exits --date 2026-07-16  # specific date
    python -m scripts.reopen_false_manual_exits --dry-run     # preview only, no changes
"""

import argparse
import sys
from datetime import date, timedelta

sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.enums.trade import TradeStatus, ExitReason
from app.models.trade import Trade, TradeSnapshot
from app.services.brokers.kite import KiteService

KITE_EXCHANGE = "NSE"
KITE_PRODUCT = "CNC"
GTT_LIMIT_BUFFER = 0.98


def round_to_tick(price: float, tick_size) -> float:
    if not tick_size:
        return round(price, 2)
    ticks = round(price / float(tick_size))
    return round(ticks * float(tick_size), 2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, help="Affected date (YYYY-MM-DD). Defaults to yesterday.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen without making any changes.")
    args = parser.parse_args()

    affected_date = date.fromisoformat(args.date) if args.date else date.today() - timedelta(days=1)
    dry_run = args.dry_run

    print(f"{'[DRY RUN] ' if dry_run else ''}Scanning for false manual exits on {affected_date}\n")

    db = SessionLocal()
    kite = KiteService()

    try:
        false_exits = (db.query(Trade).filter(Trade.status == TradeStatus.CLOSED, Trade.exit_reason == ExitReason.MANUAL, Trade.exit_date == affected_date, ).all())

        if not false_exits:
            print("No MANUAL exits found on that date. Nothing to do.")
            return

        print(f"Found {len(false_exits)} trade(s) closed as MANUAL on {affected_date}:\n")
        for t in false_exits:
            stop = (t.state or {}).get("current_stop")
            print(f"  Trade #{t.id}  {t.security.ticker}  entry={t.entry_date}  fill=₹{t.fill_price}  qty={t.fill_quantity}  stop=₹{stop}")
        print()

        skipped = []
        reopened = []

        for trade in false_exits:
            ticker = trade.security.ticker
            stop = (trade.state or {}).get("current_stop")

            if not stop:
                print(f"  SKIP {ticker} #{trade.id} — no current_stop in state, cannot place GTT")
                skipped.append(ticker)
                continue

            if not trade.fill_quantity:
                print(f"  SKIP {ticker} #{trade.id} — fill_quantity is null, cannot place GTT")
                skipped.append(ticker)
                continue

            # Fetch LTP to validate stop is still below market price
            kite_ticker = f"{KITE_EXCHANGE}:{ticker}"
            try:
                quote = kite.get_quotes([kite_ticker])
                ltp = quote[kite_ticker]["last_price"]
            except Exception as exc:
                print(f"  SKIP {ticker} #{trade.id} — could not fetch LTP: {exc}")
                skipped.append(ticker)
                continue

            if ltp <= float(stop):
                print(f"  SKIP {ticker} #{trade.id} — LTP ₹{ltp} is at or below stop ₹{stop}. "
                      f"Stop would have triggered. Review manually.")
                skipped.append(ticker)
                continue

            print(f"  REOPEN {ticker} #{trade.id} — LTP ₹{ltp} > stop ₹{stop}. Placing GTT and reopening.")

            if not dry_run:
                # Place new GTT
                trigger_price = round_to_tick(float(stop), trade.security.tick_size)
                limit_price = round_to_tick(trigger_price * GTT_LIMIT_BUFFER, trade.security.tick_size)
                try:
                    # Use native kiteconnect library directly — bypasses the custom order
                    # service (KITE_ORDER_SERVICE_URL) which isn't running in script context.
                    result = kite.kite.place_gtt(trigger_type="single", tradingsymbol=ticker, exchange=KITE_EXCHANGE, trigger_values=[trigger_price], last_price=ltp, orders=[{ "transaction_type": "SELL", "quantity": trade.fill_quantity, "product": KITE_PRODUCT, "order_type": "LIMIT", "price": limit_price, }])
                    gtt_id = str(result["trigger_id"])
                    print(f"    GTT placed: trigger=₹{trigger_price}, limit=₹{limit_price}, gtt_id={gtt_id}")
                except Exception as exc:
                    print(f"  FAIL {ticker} #{trade.id} — GTT placement failed: {exc}. Skipping reopen.")
                    skipped.append(ticker)
                    continue

                # Delete the incorrect exit snapshot for the affected date
                bad_snapshot = (db.query(TradeSnapshot).filter(TradeSnapshot.trade_id == trade.id, TradeSnapshot.snapshot_date == affected_date).first())
                if bad_snapshot:
                    db.delete(bad_snapshot)
                    print(f"    Deleted snapshot for {affected_date}")

                # Reopen the trade
                trade.status = TradeStatus.OPEN
                trade.exit_date = None
                trade.exit_price = None
                trade.exit_reason = None
                trade.kite_gtt_id = str(gtt_id)
                db.add(trade)

            reopened.append(ticker)

        if not dry_run:
            db.commit()
            print(f"\nCommitted. Reopened: {reopened or 'none'}. Skipped: {skipped or 'none'}.")
        else:
            print(f"\n[DRY RUN] Would reopen: {reopened or 'none'}. Would skip: {skipped or 'none'}.")

    except Exception as exc:
        db.rollback()
        print(f"\nFailed — rolled back. Error: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
