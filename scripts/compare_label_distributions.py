"""Compare old vs new horizon-label distributions.

Old logic:
- up_target = current_close * (1 + threshold)
- down_target = current_close * (1 - threshold)

New logic:
- up_target = current_high * (1 + threshold)
- down_target = current_low * (1 - threshold)
"""

from dataclasses import dataclass
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from services.ml_dataset import MlDatasetService


@dataclass
class LabelStats:
    total_windows: int = 0
    ambiguous: int = 0
    kept: int = 0
    long_positive: int = 0
    short_positive: int = 0
    flat: int = 0


def resolve_label(rows: list[dict], index: int, horizon_days: int, up_target: float, down_target: float) -> tuple[bool, bool, bool]:
    """Return (long_label, short_label, ambiguous) using first-hit tie logic."""
    long_hit_step = None
    short_hit_step = None

    for step in range(1, horizon_days + 1):
        future_row = rows[index + step]
        if long_hit_step is None and float(future_row['high']) >= up_target:
            long_hit_step = step
        if short_hit_step is None and float(future_row['low']) <= down_target:
            short_hit_step = step
        if long_hit_step is not None and short_hit_step is not None:
            break

    if long_hit_step is None and short_hit_step is None:
        return False, False, False

    if long_hit_step is not None and short_hit_step is not None:
        if long_hit_step == short_hit_step:
            return False, False, True
        if long_hit_step < short_hit_step:
            return True, False, False
        return False, True, False

    if long_hit_step is not None:
        return True, False, False

    return False, True, False


def update_stats(stats: LabelStats, long_label: bool, short_label: bool, ambiguous: bool) -> None:
    stats.total_windows += 1
    if ambiguous:
        stats.ambiguous += 1
        return

    stats.kept += 1
    if long_label:
        stats.long_positive += 1
    elif short_label:
        stats.short_positive += 1
    else:
        stats.flat += 1


def pct(n: int, d: int) -> float:
    return (n * 100.0 / d) if d > 0 else 0.0


def main() -> None:
    service = MlDatasetService()
    daily_rows_by_security = service.preload_daily_rows_for_inference()

    horizon_days = int(settings.ML_HORIZON_DAYS)
    threshold = float(settings.ML_MOVE_THRESHOLD_PCT) / 100.0

    old_stats = LabelStats()
    new_stats = LabelStats()

    for _security_id, rows in daily_rows_by_security.items():
        if len(rows) <= horizon_days:
            continue

        for index in range(len(rows) - horizon_days):
            current = rows[index]
            current_close = float(current['close'])
            current_high = float(current['high'])
            current_low = float(current['low'])

            old_up_target = current_close * (1.0 + threshold)
            old_down_target = current_close * (1.0 - threshold)
            new_up_target = current_high * (1.0 + threshold)
            new_down_target = current_low * (1.0 - threshold)

            old_long, old_short, old_ambiguous = resolve_label(rows, index, horizon_days, old_up_target, old_down_target)
            new_long, new_short, new_ambiguous = resolve_label(rows, index, horizon_days, new_up_target, new_down_target)

            update_stats(old_stats, old_long, old_short, old_ambiguous)
            update_stats(new_stats, new_long, new_short, new_ambiguous)

    print('Label Distribution Comparison')
    print(f'horizon_days={horizon_days} threshold_pct={float(settings.ML_MOVE_THRESHOLD_PCT):.2f}')
    print('')

    print('Old (close-based up/down targets):')
    print(f'  total_windows:     {old_stats.total_windows}')
    print(f'  ambiguous:         {old_stats.ambiguous} ({pct(old_stats.ambiguous, old_stats.total_windows):.2f}%)')
    print(f'  kept_windows:      {old_stats.kept}')
    print(f'  long_positive:     {old_stats.long_positive} ({pct(old_stats.long_positive, old_stats.kept):.2f}% of kept)')
    print(f'  short_positive:    {old_stats.short_positive} ({pct(old_stats.short_positive, old_stats.kept):.2f}% of kept)')
    print(f'  flat:              {old_stats.flat} ({pct(old_stats.flat, old_stats.kept):.2f}% of kept)')
    print('')

    print('New (high-based long target, low-based short target):')
    print(f'  total_windows:     {new_stats.total_windows}')
    print(f'  ambiguous:         {new_stats.ambiguous} ({pct(new_stats.ambiguous, new_stats.total_windows):.2f}%)')
    print(f'  kept_windows:      {new_stats.kept}')
    print(f'  long_positive:     {new_stats.long_positive} ({pct(new_stats.long_positive, new_stats.kept):.2f}% of kept)')
    print(f'  short_positive:    {new_stats.short_positive} ({pct(new_stats.short_positive, new_stats.kept):.2f}% of kept)')
    print(f'  flat:              {new_stats.flat} ({pct(new_stats.flat, new_stats.kept):.2f}% of kept)')
    print('')

    print('Delta (new - old):')
    print(f'  ambiguous:         {new_stats.ambiguous - old_stats.ambiguous}')
    print(f'  kept_windows:      {new_stats.kept - old_stats.kept}')
    print(f'  long_positive:     {new_stats.long_positive - old_stats.long_positive}')
    print(f'  short_positive:    {new_stats.short_positive - old_stats.short_positive}')
    print(f'  flat:              {new_stats.flat - old_stats.flat}')


if __name__ == '__main__':
    main()
