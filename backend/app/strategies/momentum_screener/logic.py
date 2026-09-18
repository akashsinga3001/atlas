# backend/app/strategies/momentum_screener/logic.py

import pandas as pd


def select_signals(snapshot: pd.DataFrame, thresholds: dict[str, float], selection_config: dict) -> pd.DataFrame:
    """Pure signal filter/scoring/selection for the momentum screener: apply every quantile
    threshold, then sort-or-random and cap at max_signals. Extracted out of execute() so this
    capital-gating selection logic is independently callable/auditable (e.g. from a REPL or a
    future test) without a live StrategyContext/FeatureService, per CLAUDE.md's strategy-logic
    convention — relative_leadership_v1 already follows this same pattern.
    """
    signals = snapshot.copy()
    for feature, threshold in thresholds.items():
        signals = signals[signals[feature] >= threshold]

    max_signals = selection_config["max_signals"]
    if selection_config["sort_by"] == "random":
        return signals.sample(n=min(max_signals, len(signals)))

    signals = signals.sort_values(by=selection_config["sort_by"], ascending=selection_config["ascending"])
    return signals.head(max_signals)
