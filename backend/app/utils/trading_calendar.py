# backend/app/utils/trading_calendar.py
#
# NSE trading-holiday calendar. NSE publishes this list once a year (nseindia.com
# > Market Timings & Holidays) — NSE_HOLIDAYS below must be extended with the next
# year's list before it runs out, or every date-arithmetic call here silently starts
# treating a holiday as a trading day. Weekend closures don't need to be listed
# (already excluded by the weekday check), only weekday holidays.
#
# The iron condor strategy's own no-trade condition (skip if a leg isn't quotable)
# is a safety net if a holiday is ever missing from this list — a misclassified
# holiday fails the liquidity check and the week gets skipped rather than misfiring
# an order, but the "5 trading days after entry" / "next NSE trading day" arithmetic
# below still depends on this list being accurate.
#
# Confidence by year, as of 2026-08-15:
#   2026 — verified against 3 independent sources (groww.in, calendarlabs.com,
#          smallcase.com), all in exact agreement. High confidence.
#   2027 — NSE had not yet published an official circular for 2027 as of this date
#          (multiple trading-holiday sites explicitly say the 2027 list is still
#          "being compiled"). The dates below are a single secondary source's
#          estimate (calendarlabs.com), not an official confirmation. NSE typically
#          publishes the following year's calendar around December — re-verify this
#          block against the official circular once it's out, don't just trust it.

from datetime import date, timedelta

NSE_HOLIDAYS: set[date] = {
    # 2026 — verified, see confidence note above
    date(2026, 1, 26),   # Republic Day
    date(2026, 3, 3),    # Holi
    date(2026, 3, 26),   # Shri Ram Navami
    date(2026, 3, 31),   # Shri Mahavir Jayanti
    date(2026, 4, 3),    # Good Friday
    date(2026, 4, 14),   # Dr. Baba Saheb Ambedkar Jayanti
    date(2026, 5, 1),    # Maharashtra Day
    date(2026, 5, 28),   # Bakri Id
    date(2026, 6, 26),   # Muharram
    date(2026, 9, 14),   # Ganesh Chaturthi
    date(2026, 10, 2),   # Mahatma Gandhi Jayanti
    date(2026, 10, 20),  # Dussehra
    date(2026, 11, 10),  # Diwali-Balipratipada
    date(2026, 11, 24),  # Guru Nanak Jayanti
    date(2026, 12, 25),  # Christmas

    # 2027 — PROVISIONAL, see confidence note above. Re-verify against NSE's official
    # circular once published (expected ~December 2026).
    date(2027, 1, 26),   # Republic Day
    date(2027, 3, 10),   # Id-ul-Fitr (Ramzan Id)
    date(2027, 3, 22),   # Holi
    date(2027, 3, 26),   # Good Friday
    date(2027, 4, 14),   # Dr. Baba Saheb Ambedkar Jayanti
    date(2027, 4, 15),   # Ram Navami
    date(2027, 4, 19),   # Mahavir Jayanti
    date(2027, 5, 17),   # Bakri Id / Eid ul-Adha
    date(2027, 6, 15),   # Muharram
    date(2027, 10, 29),  # Diwali-Balipratipada / Laxmi Pujan
}


def is_nse_trading_day(d: date) -> bool:
    """True if d is an NSE trading day (weekday, not a listed holiday)."""
    return d.weekday() < 5 and d not in NSE_HOLIDAYS


def calendar_coverage_end() -> date:
    """Last calendar date this module has any holiday data for."""
    return max(NSE_HOLIDAYS)


def is_calendar_stale(as_of_date: date, warn_within_days: int = 60) -> bool:
    """True once as_of_date is getting close to running past known holiday coverage.

    NSE_HOLIDAYS above needs manual yearly extension — this is the automatable half of
    that reminder. warn_within_days=60 means: once we're within 2 months of the last
    date this module knows about, it's time to add next year's list, not after.
    """
    return (calendar_coverage_end() - as_of_date).days < warn_within_days


def next_nse_trading_day(d: date) -> date:
    """First NSE trading day strictly after d."""
    candidate = d + timedelta(days=1)
    while not is_nse_trading_day(candidate):
        candidate += timedelta(days=1)
    return candidate


def add_nse_trading_days(d: date, n: int) -> date:
    """Walk forward n NSE trading days from d (d itself is not counted)."""
    candidate = d
    remaining = n
    while remaining > 0:
        candidate = next_nse_trading_day(candidate)
        remaining -= 1
    return candidate
