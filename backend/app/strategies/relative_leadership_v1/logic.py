# backend/app/strategies/relative_leadership_v1/logic.py
#
# Pure, testable functions implementing the frozen Relative Leadership V1 rules
# (see relative_leadership_v1_strategy_spec.md). Shared by the strategy (signal
# generation) and its exit evaluator (deterioration tracking) — both need the same
# cross-sectional ranking of the same day, computed the same way.

import pandas as pd


def rank_universe(snapshot_df: pd.DataFrame, entry_percentile: float, exit_percentile: float) -> pd.DataFrame:
    """Rank a day's security snapshot by mom_6_1, strongest first, and flag top-10%/top-30% membership.

    Securities with no valid mom_6_1 (insufficient history) are dropped entirely — they have
    no valid momentum value for this session and must not participate in ranking. Ties are
    broken by ticker ascending before rank is assigned, so the rank/percentile boundary is
    deterministic regardless of row order or universe size. percentile_rank is rank / n
    (1/n = the single strongest security), and is_top_10/is_top_30 are inclusive
    (percentile_rank <= threshold) — the one consistent convention used everywhere.
    """
    valid = snapshot_df.dropna(subset=["mom_6_1"]).copy()
    if valid.empty:
        return valid.assign(rank=pd.Series(dtype="int64"), percentile_rank=pd.Series(dtype="float64"), is_top_10=pd.Series(dtype="bool"), is_top_30=pd.Series(dtype="bool"))

    valid = valid.sort_values(by=["mom_6_1", "ticker"], ascending=[False, True]).reset_index(drop=True)
    n = len(valid)

    valid["rank"] = valid.index + 1
    valid["percentile_rank"] = valid["rank"] / n
    valid["is_top_10"] = valid["percentile_rank"] <= entry_percentile
    valid["is_top_30"] = valid["percentile_rank"] <= exit_percentile

    return valid


def detect_transitions(today_ranked: pd.DataFrame, prev_ranked: pd.DataFrame) -> pd.DataFrame:
    """Return securities newly inside the top 10% today that were not inside it in the
    previous ranked session — a security absent from prev_ranked (missing history, or not
    yet in the universe) counts as "not top 10 yesterday". Sorted by mom_6_1 descending,
    ticker ascending — the frozen candidate-priority order; callers must not re-sort this.
    """
    if today_ranked.empty:
        return today_ranked

    prev_top10_tickers: set = set(prev_ranked.loc[prev_ranked["is_top_10"], "ticker"]) if not prev_ranked.empty else set()

    transitions = today_ranked[today_ranked["is_top_10"] & ~today_ranked["ticker"].isin(prev_top10_tickers)].copy()
    return transitions.sort_values(by=["mom_6_1", "ticker"], ascending=[False, True]).reset_index(drop=True)
