"""
Aggregate RandomForest feature importances across all walk-forward fold artifacts
to identify features that are stable across market regimes.

Usage:
    py scripts/analyze_feature_stability.py --artifacts ./artifacts/ml --top 40
    py scripts/analyze_feature_stability.py --artifacts ./artifacts/ml --top 40 --direction short
"""

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib


def _load_importances(artifacts_dir: Path, direction: str) -> list[dict]:
    """Load feature importance dicts from all fold model artifacts.

    Args:
        artifacts_dir: Root artifacts directory (e.g. ./artifacts/ml).
        direction: 'long' or 'short'.

    Returns:
        List of {date_dir, feature_importances: [{feature, importance}]} dicts.
    """
    results = []
    pattern = f'{direction}_rf.joblib'

    for date_dir in sorted(artifacts_dir.iterdir()):
        if not date_dir.is_dir():
            continue
        model_path = date_dir / pattern
        if not model_path.exists():
            # Also try ensemble naming
            model_path = date_dir / f'{direction}_ensemble.joblib'
            if not model_path.exists():
                continue

        try:
            bundle = joblib.load(str(model_path))
            importance = bundle.get('feature_importance', [])
            if importance:
                results.append({'date': date_dir.name, 'importance': importance})
                print(f'  Loaded {model_path.name} from {date_dir.name} ({len(importance)} features)')
        except Exception as exc:
            print(f'  WARN: Could not load {model_path}: {exc}')

    return results


def _aggregate(fold_results: list[dict], top_k: int) -> list[dict]:
    """Compute cross-fold stability metrics for each feature.

    For each feature tracks:
    - mean_importance: average RF importance across all folds
    - top15_frequency: fraction of folds where feature ranked in top 15
    - stability_score: harmonic blend of mean_importance and top15_frequency
    - mean_rank: average rank position across folds (lower = better)

    Args:
        fold_results: Output of _load_importances().
        top_k: Number of top features to return.

    Returns:
        Sorted list of feature dicts with stability metrics.
    """
    n_folds = len(fold_results)
    if n_folds == 0:
        return []

    # Build per-feature data
    feature_importances: dict[str, list[float]] = {}
    feature_ranks: dict[str, list[int]] = {}
    feature_top15_count: dict[str, int] = {}

    for fold in fold_results:
        ranked = sorted(fold['importance'], key=lambda x: float(x['importance']), reverse=True)
        for rank_idx, item in enumerate(ranked, start=1):
            feat = str(item['feature'])
            imp = float(item['importance'])
            feature_importances.setdefault(feat, []).append(imp)
            feature_ranks.setdefault(feat, []).append(rank_idx)
            if rank_idx <= 15:
                feature_top15_count[feat] = feature_top15_count.get(feat, 0) + 1

    aggregated = []
    for feat, importances in feature_importances.items():
        mean_imp = sum(importances) / len(importances)
        folds_present = len(importances)
        # Penalise features that disappear in some folds (pad missing folds with rank = total + 1)
        all_ranks = feature_ranks.get(feat, [])
        max_rank = max(len(fold['importance']) for fold in fold_results) + 1
        padded_ranks = all_ranks + [max_rank] * (n_folds - folds_present)
        mean_rank = sum(padded_ranks) / n_folds
        top15_freq = feature_top15_count.get(feat, 0) / n_folds

        # Stability score: reward consistent high importance across ALL folds
        # 0.6 * normalised_mean_importance (relative) + 0.4 * top15_frequency
        aggregated.append({
            'feature': feat,
            'mean_importance': round(mean_imp, 6),
            'mean_rank': round(mean_rank, 1),
            'top15_frequency': round(top15_freq, 3),
            'folds_present': folds_present,
            'n_folds': n_folds,
        })

    # Normalise importance for stability score
    max_imp = max(a['mean_importance'] for a in aggregated) or 1.0
    for a in aggregated:
        norm_imp = a['mean_importance'] / max_imp
        a['stability_score'] = round(0.6 * norm_imp + 0.4 * a['top15_frequency'], 4)

    aggregated.sort(key=lambda x: x['stability_score'], reverse=True)
    return aggregated[:top_k]


def _print_table(rows: list[dict], title: str) -> None:
    """Print a formatted stability table."""
    print(f'\n{"=" * 90}')
    print(f'  {title}')
    print(f'{"=" * 90}')
    print(f'  {"#":>3}  {"Feature":<40}  {"MeanImp":>8}  {"MeanRank":>8}  {"Top15%":>7}  {"Stability":>9}  {"Folds":>5}')
    print(f'  {"-" * 85}')
    for i, row in enumerate(rows, start=1):
        present_flag = '' if row['folds_present'] == row['n_folds'] else f'  ({row["folds_present"]}/{row["n_folds"]} folds)'
        print(
            f'  {i:>3}  {row["feature"]:<40}  {row["mean_importance"]:>8.5f}  '
            f'{row["mean_rank"]:>8.1f}  {row["top15_frequency"]:>7.3f}  '
            f'{row["stability_score"]:>9.4f}{present_flag}'
        )
    print()


def _suggest_whitelist(rows: list[dict], min_stability: float, min_folds_pct: float) -> list[str]:
    """Return feature names meeting the stability and fold-coverage thresholds.

    Args:
        rows: Aggregated stability rows (all features, not just top_k).
        min_stability: Minimum stability_score to include.
        min_folds_pct: Minimum fraction of folds feature must appear in (e.g. 0.8).

    Returns:
        Sorted list of selected feature names.
    """
    n_folds = rows[0]['n_folds'] if rows else 1
    selected = [
        r['feature'] for r in rows
        if r['stability_score'] >= min_stability
        and r['folds_present'] / n_folds >= min_folds_pct
    ]
    return sorted(selected)


def main() -> None:
    parser = argparse.ArgumentParser(description='Analyse cross-fold feature stability from backtest artifacts')
    parser.add_argument('--artifacts', type=str, default='./artifacts/ml', help='Path to artifacts/ml directory')
    parser.add_argument('--top', type=int, default=40, help='Number of top features to display')
    parser.add_argument('--direction', type=str, default='long', choices=['long', 'short'], help='Model direction to analyse')
    parser.add_argument('--min-stability', type=float, default=0.15, help='Minimum stability score for whitelist suggestion')
    parser.add_argument('--min-folds-pct', type=float, default=0.75, help='Minimum fraction of folds a feature must appear in')
    args = parser.parse_args()

    artifacts_dir = Path(args.artifacts)
    if not artifacts_dir.exists():
        print(f'ERROR: Artifacts directory not found: {artifacts_dir}')
        sys.exit(1)

    print(f'\nScanning {artifacts_dir} for {args.direction}_*.joblib artifacts...')
    fold_results = _load_importances(artifacts_dir, args.direction)

    if not fold_results:
        print('ERROR: No model artifacts found. Run the backtest first.')
        sys.exit(1)

    print(f'\nLoaded {len(fold_results)} fold artifacts.')

    # Aggregate across ALL features first for whitelist suggestion
    all_features_aggregated = _aggregate(fold_results, top_k=9999)

    # Display top N
    top_rows = all_features_aggregated[:args.top]
    _print_table(top_rows, f'Feature Stability Report — {args.direction.upper()} — {len(fold_results)} folds')

    # Suggest whitelist
    suggested = _suggest_whitelist(
        all_features_aggregated,
        min_stability=args.min_stability,
        min_folds_pct=args.min_folds_pct,
    )

    print(f'\n{"=" * 90}')
    print(f'  Suggested Whitelist  (stability >= {args.min_stability}, present in >= {args.min_folds_pct*100:.0f}% of folds)')
    print(f'  {len(suggested)} features selected')
    print(f'{"=" * 90}')
    if suggested:
        # Print as config-ready comma-separated string
        whitelist_str = ','.join(suggested)
        print(f'\n  ML_FEATURE_WHITELIST = \'{whitelist_str}\'\n')
        print('  Individual features:')
        for f in suggested:
            row = next((r for r in all_features_aggregated if r['feature'] == f), None)
            if row:
                print(f'    {f:<40}  stability={row["stability_score"]:.4f}  top15_freq={row["top15_frequency"]:.3f}')
    else:
        print('  No features met the threshold. Try lowering --min-stability or --min-folds-pct.')


if __name__ == '__main__':
    main()
