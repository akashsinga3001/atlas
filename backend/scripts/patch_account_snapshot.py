"""
Patch an incorrect AccountSnapshot by recomputing holdings_value from Atlas's open trades.

When to use:
    The 07-16 snapshot was recorded at 4:05 PM after 3 trades were falsely CLOSED at 3:20 PM.
    Now that those trades are reopened, the snapshot understates total_value by ~₹73K.
    This script recomputes holdings_value using the mark-to-market method (same as FundService)
    and upserts the corrected snapshot.

Usage:
    cd backend
    python -m scripts.patch_account_snapshot --date 2026-07-16
    python -m scripts.patch_account_snapshot --date 2026-07-16 --dry-run
"""

import argparse
import sys
from datetime import date

sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.models.fund import AccountSnapshot
from app.services.brokers.kite import KiteService
from app.services.fund import FundService

KITE_EXCHANGE = "NSE"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="Snapshot date to patch (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would change without committing")
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date)
    dry_run = args.dry_run

    print(f"{'[DRY RUN] ' if dry_run else ''}Patching AccountSnapshot for {target_date}\n")

    db = SessionLocal()
    kite = KiteService()

    try:
        existing = db.query(AccountSnapshot).filter(AccountSnapshot.snapshot_date == target_date).first()
        if not existing:
            print(f"No AccountSnapshot found for {target_date}. Nothing to patch.")
            return

        print(f"Current snapshot:")
        print(f"  cash_balance  = ₹{existing.cash_balance:,.2f}")
        print(f"  holdings_value= ₹{existing.holdings_value:,.2f}")
        print(f"  total_value   = ₹{existing.total_value:,.2f}\n")

        # Recompute using FundService (same logic as the daily job)
        fund_service = FundService(db, kite)
        new_holdings_value = fund_service._get_open_trades_value()

        # Cash balance stays as-is — we trust what was recorded at 4:05 PM
        new_total = float(existing.cash_balance) + new_holdings_value

        print(f"Recomputed:")
        print(f"  holdings_value= ₹{new_holdings_value:,.2f}  (was ₹{float(existing.holdings_value):,.2f})")
        print(f"  total_value   = ₹{new_total:,.2f}  (was ₹{float(existing.total_value):,.2f})\n")

        if not dry_run:
            existing.holdings_value = new_holdings_value
            existing.total_value = new_total
            db.commit()
            print("Snapshot updated and committed.")
        else:
            print("[DRY RUN] No changes written.")

    except Exception as exc:
        db.rollback()
        print(f"\nFailed — rolled back. Error: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
