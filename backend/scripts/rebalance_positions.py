"""
Rebalance open trades to equal allocation weight by topping up undersized positions.

Target position size = account_size / max_positions (from strategy config).

Rules:
  - Underweight (invested < target - MIN_SHORTFALL): buy top-up shares
  - Overweight  (invested > target): log and skip — anti-momentum to trim winners
  - Shortfall < MIN_SHORTFALL (₹500): skip — not worth the transaction cost

After a top-up buy:
  - fill_price is updated to the weighted average of original + top-up fills
  - fill_quantity is updated to the new total
  - Old GTT is cancelled and replaced with the same stop price and new quantity

Usage:
    cd backend
    python -m scripts.rebalance_positions                         # dry run, active strategy
    python -m scripts.rebalance_positions --strategy-version 2   # specific version
    python -m scripts.rebalance_positions --execute               # place actual orders
"""

import argparse
import sys
import time

sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.enums.trade import TradeStatus
from app.models.strategy import StrategyVersion
from app.models.trade import Trade
from app.repositories.trade import TradeRepository
from app.services.brokers.kite import KiteService
from app.services.portfolio import PortfolioService

KITE_EXCHANGE = "NSE"
KITE_PRODUCT = "CNC"
GTT_LIMIT_BUFFER = 0.98
ORDER_BUY_BUFFER = 1.002  # limit price slightly above LTP to ensure fill
MIN_SHORTFALL = 500.0  # skip top-up if shortfall is under ₹500
FILL_POLL_SLEEP = 10  # seconds to wait before polling fill
FILL_POLL_ATTEMPTS = 6


def round_to_tick(price: float, tick_size) -> float:
    if not tick_size:
        return round(price, 2)
    ticks = round(price / float(tick_size))
    return round(ticks * float(tick_size), 2)


def poll_fill(kite: KiteService, order_id: str) -> tuple[float | None, int | None]:
    """Poll Kite order trades and return VWAP fill price and total quantity."""
    for attempt in range(FILL_POLL_ATTEMPTS):
        time.sleep(FILL_POLL_SLEEP)
        try:
            trades = kite.get_order_trades(str(order_id))
            if trades:
                total_qty = sum(t["quantity"] for t in trades)
                vwap = sum(t["average_price"] * t["quantity"] for t in trades) / total_qty
                return round(vwap, 4), total_qty
        except Exception as exc:
            print(f"      Poll attempt {attempt + 1} failed: {exc}")
    return None, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy-version", type=int, help="Strategy version ID (default: active version)")
    parser.add_argument("--execute", action="store_true", help="Place actual orders. Omit for dry run.")
    args = parser.parse_args()

    dry_run = not args.execute
    print(f"{'[DRY RUN] ' if dry_run else '[LIVE] '}Rebalancing open positions\n")

    db = SessionLocal()
    kite = KiteService()

    try:
        # Resolve strategy version
        if args.strategy_version:
            sv = db.query(StrategyVersion).filter(StrategyVersion.id == args.strategy_version).first()
            if not sv:
                print(f"Strategy version {args.strategy_version} not found.")
                return
        else:
            sv = db.query(StrategyVersion).filter(StrategyVersion.is_active == True).order_by(StrategyVersion.id.desc()).first()
            if not sv:
                print("No active strategy version found.")
                return

        max_positions = sv.config["selection"]["max_signals"]
        print(f"Strategy version {sv.id} (v{sv.version}), max_positions={max_positions}\n")

        # Calculate target position size from current account state
        portfolio = PortfolioService(db, kite)
        account_size = portfolio.get_account_size()
        target = account_size / max_positions
        print(f"Account size : ₹{account_size:,.2f}")
        print(f"Target/trade : ₹{target:,.2f}  ({100 / max_positions:.1f}% each)\n")

        trade_repo = TradeRepository(db)
        open_trades: list[Trade] = trade_repo.get_open_trades_for_strategy_version(sv.id)

        if not open_trades:
            print("No open trades found.")
            return

        print(f"{'Ticker':<14} {'Invested':>12} {'Target':>12} {'Diff':>12} {'Action'}")
        print("-" * 70)

        to_topup: list[dict] = []

        for trade in open_trades:
            ticker = trade.security.ticker
            invested = float(trade.fill_price or 0) * (trade.fill_quantity or 0)
            diff = target - invested
            pct = (diff / target) * 100

            if diff < -MIN_SHORTFALL:
                print(f"{ticker:<14} ₹{invested:>10,.0f}   ₹{target:>10,.0f}   ₹{diff:>+10,.0f}   SKIP (overweight {abs(pct):.1f}%)")
                continue

            if diff < MIN_SHORTFALL:
                print(f"{ticker:<14} ₹{invested:>10,.0f}   ₹{target:>10,.0f}   ₹{diff:>+10,.0f}   SKIP (within ₹{MIN_SHORTFALL:.0f} threshold)")
                continue

            # Fetch LTP to calculate top-up quantity
            try:
                kite_ticker = f"{KITE_EXCHANGE}:{ticker}"
                quote = kite.get_quotes([kite_ticker])
                ltp = quote[kite_ticker]["last_price"]
            except Exception as exc:
                print(f"{ticker:<14} ₹{invested:>10,.0f}   ₹{target:>10,.0f}   ₹{diff:>+10,.0f}   SKIP (cannot fetch LTP: {exc})")
                continue

            topup_qty = int(diff // ltp)
            if topup_qty < 1:
                print(f"{ticker:<14} ₹{invested:>10,.0f}   ₹{target:>10,.0f}   ₹{diff:>+10,.0f}   SKIP (shortfall < 1 share at ₹{ltp:.2f})")
                continue

            new_total_qty = (trade.fill_quantity or 0) + topup_qty
            new_avg_price = ((float(trade.fill_price) * (trade.fill_quantity or 0)) + (ltp * topup_qty)) / new_total_qty

            stop = (trade.state or {}).get("current_stop")
            if stop:
                old_stop_dist = ((float(trade.fill_price) - float(stop)) / float(trade.fill_price)) * 100
                new_stop_dist = ((new_avg_price - float(stop)) / new_avg_price) * 100
            else:
                old_stop_dist = new_stop_dist = None

            print(f"{ticker:<14} ₹{invested:>10,.0f}   ₹{target:>10,.0f}   ₹{diff:>+10,.0f}   TOP-UP +{topup_qty} shares @ ₹{ltp:.2f}")
            print(f"{'':14}   avg price: ₹{float(trade.fill_price):.2f} → ₹{new_avg_price:.2f}" + (f"   stop dist: {old_stop_dist:.1f}% → {new_stop_dist:.1f}%" if stop else ""))

            to_topup.append({ "trade": trade, "ticker": ticker, "ltp": ltp, "topup_qty": topup_qty, "new_total_qty": new_total_qty, "new_avg_price": new_avg_price, "stop": stop, })

        print()

        if not to_topup:
            print("Nothing to top up.")
            return

        if dry_run:
            print(f"[DRY RUN] Would top up {len(to_topup)} trade(s). Run with --execute to place orders.")
            return

        # ------------------------------------------------------------------ #
        #  Execute top-ups                                                    #
        # ------------------------------------------------------------------ #
        succeeded = []
        failed = []

        for item in to_topup:
            trade: Trade = item["trade"]
            ticker = item["ticker"]
            ltp = item["ltp"]
            topup_qty = item["topup_qty"]
            new_total_qty = item["new_total_qty"]
            new_avg_price = item["new_avg_price"]
            stop = item["stop"]

            print(f"\n→ Topping up {ticker} #{trade.id}: buying {topup_qty} shares")

            # Place limit buy slightly above LTP to ensure fill
            buy_price = round_to_tick(ltp * ORDER_BUY_BUFFER, trade.security.tick_size)
            try:
                order_id = kite.place_order(variety="regular", exchange=KITE_EXCHANGE, tradingsymbol=ticker, transaction_type="BUY", quantity=topup_qty, product=KITE_PRODUCT, order_type="LIMIT", price=buy_price, )
                print(f"  Buy order placed: order_id={order_id}, qty={topup_qty}, limit=₹{buy_price:.2f}")
            except Exception as exc:
                print(f"  FAIL — buy order placement failed: {exc}")
                failed.append(ticker)
                continue

            # Poll for fill
            print(f"  Waiting {FILL_POLL_SLEEP}s for fill...")
            fill_price, fill_qty = poll_fill(kite, str(order_id))
            if fill_price is None:
                print(f"  FAIL — fill not confirmed after {FILL_POLL_ATTEMPTS * FILL_POLL_SLEEP}s. Trade record NOT updated.")
                failed.append(ticker)
                continue

            actual_new_qty = (trade.fill_quantity or 0) + fill_qty
            actual_new_avg = ((float(trade.fill_price) * (trade.fill_quantity or 0)) + (fill_price * fill_qty)) / actual_new_qty
            actual_new_invested = actual_new_avg * actual_new_qty
            print(f"  Filled: {fill_qty} shares @ ₹{fill_price:.2f}")
            print(f"  New total: qty={actual_new_qty}, avg_price=₹{actual_new_avg:.2f}, invested=₹{actual_new_invested:,.2f}")

            # Cancel old GTT and place new one with updated quantity
            if trade.kite_gtt_id and stop:
                try:
                    kite.delete_gtt(int(trade.kite_gtt_id))
                    print(f"  Cancelled old GTT {trade.kite_gtt_id}")
                except Exception as exc:
                    print(f"  Warning — could not cancel GTT {trade.kite_gtt_id}: {exc} (continuing anyway)")

                try:
                    trigger_price = round_to_tick(float(stop), trade.security.tick_size)
                    limit_price = round_to_tick(trigger_price * GTT_LIMIT_BUFFER, trade.security.tick_size)
                    new_gtt_id = str(kite.place_gtt(trigger_type="single", tradingsymbol=ticker, exchange=KITE_EXCHANGE, trigger_values=[trigger_price], last_price=fill_price, orders=[{ "transaction_type": "SELL", "quantity": actual_new_qty, "product": KITE_PRODUCT, "order_type": "LIMIT", "price": limit_price, }], ))
                    print(f"  New GTT placed: trigger=₹{trigger_price}, limit=₹{limit_price}, qty={actual_new_qty}, gtt_id={new_gtt_id}")
                except Exception as exc:
                    print(f"  FAIL — GTT replacement failed: {exc}. Trade record NOT updated to avoid qty mismatch.")
                    failed.append(ticker)
                    continue
            else:
                new_gtt_id = trade.kite_gtt_id  # no stop set, keep as-is

            # Update trade record
            trade.fill_price = actual_new_avg
            trade.fill_quantity = actual_new_qty
            trade.invested_value = actual_new_invested
            if new_gtt_id:
                trade.kite_gtt_id = new_gtt_id
            db.add(trade)
            succeeded.append(ticker)
            print(f"  Trade #{trade.id} updated.")

        db.commit()
        print(f"\nDone. Topped up: {succeeded or 'none'}. Failed: {failed or 'none'}.")

    except Exception as exc:
        db.rollback()
        print(f"\nFailed — rolled back. Error: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
