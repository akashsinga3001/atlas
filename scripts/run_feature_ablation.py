"""Run ML feature ablation experiments and compare validation metrics."""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from time import perf_counter

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from services.ml_dataset import MlDatasetService
from services.ml_model import MlModelService
from utils.logger import logger


def _resolve_analysis_csv(path_override: str | None) -> Path:
    """Resolve the feature-importance CSV to use for top/bottom feature lists."""
    if path_override:
        path = Path(path_override)
        if not path.exists():
            raise FileNotFoundError(f'Provided analysis CSV does not exist: {path}')
        return path

    analysis_dir = PROJECT_ROOT / 'artifacts' / 'analysis'
    candidates = sorted(analysis_dir.glob('feature_importance_1DAY_*.csv'))
    if not candidates:
        raise FileNotFoundError('No feature importance CSV found in artifacts/analysis')
    return candidates[-1]


def _parse_feature_rankings(csv_path: Path) -> tuple[list[str], list[str]]:
    """Return sorted top-to-bottom feature names from contribution analysis CSV."""
    frame = pd.read_csv(csv_path)
    if 'feature' not in frame.columns or 'combined_importance' not in frame.columns:
        raise ValueError(f'Invalid analysis CSV format: {csv_path}')

    frame = frame.sort_values('combined_importance', ascending=False)
    ordered = frame['feature'].astype(str).tolist()
    return ordered, list(reversed(ordered))


def _split_whitelist(raw: str) -> list[str]:
    """Split comma-separated whitelist while preserving order."""
    return [item.strip() for item in str(raw).split(',') if item.strip()]


def _map_features_to_available(features: list[str], available: list[str]) -> list[str]:
    """Map analysis feature names to available model feature columns."""
    available_set = set(available)
    mapped: list[str] = []
    for feature in features:
        if feature in available_set:
            mapped.append(feature)
            continue

        for alias in (f'd_{feature}', f'w_{feature}', f'm_{feature}'):
            if alias in available_set:
                mapped.append(alias)
                break
        else:
            mapped.append(feature)

    return mapped


def _run_variant(
    name: str,
    run_date: date,
    records: list[dict],
    feature_keys: list[str],
    model_service: MlModelService,
    model_type: str,
    whitelist: list[str],
    top_k: int,
) -> dict:
    """Run one ablation variant and return summary metrics."""
    settings.ML_FEATURE_WHITELIST = ','.join(whitelist)
    settings.ML_FEATURE_TOP_K = int(top_k)

    started_at = perf_counter()
    trained = model_service.train(
        run_date=run_date,
        records=records,
        feature_keys=feature_keys,
        model_type=model_type,
    )
    elapsed = round(perf_counter() - started_at, 2)

    return {
        'variant': name,
        'model_type': model_type,
        'selected_feature_count': len(trained.feature_columns),
        'samples_total': trained.samples_total,
        'samples_train': trained.samples_train,
        'samples_validation': trained.samples_validation,
        'long_precision': float(trained.long_metrics.get('precision', 0.0)),
        'long_recall': float(trained.long_metrics.get('recall', 0.0)),
        'long_precision_at_5': float(trained.long_metrics.get('precision_at_5', 0.0)),
        'long_precision_at_10': float(trained.long_metrics.get('precision_at_10', 0.0)),
        'short_precision': float(trained.short_metrics.get('precision', 0.0)),
        'short_recall': float(trained.short_metrics.get('recall', 0.0)),
        'short_precision_at_5': float(trained.short_metrics.get('precision_at_5', 0.0)),
        'short_precision_at_10': float(trained.short_metrics.get('precision_at_10', 0.0)),
        'elapsed_seconds': elapsed,
    }


def main() -> int:
    """Run baseline and ablation variants, then save comparison outputs."""
    parser = argparse.ArgumentParser(description='Run feature ablation training experiments.')
    parser.add_argument('--analysis-csv', type=str, default=None, help='Path to feature importance CSV from contribution analysis')
    parser.add_argument('--top-n', type=int, default=10, help='Top-N features to keep/remove for ablation')
    parser.add_argument('--model-type', type=str, default=None, choices=['rf', 'lgb', 'xgb', 'ensemble'], help='Override model type')
    parser.add_argument('--train-start-date', type=str, default='2024-01-01', help='Training lower bound date (YYYY-MM-DD)')
    parser.add_argument('--train-end-date', type=str, default='2024-12-31', help='Training upper bound date (YYYY-MM-DD)')
    parser.add_argument('--output-dir', type=str, default='./artifacts/analysis/ablation', help='Output directory')
    args = parser.parse_args()

    train_start_date = date.fromisoformat(args.train_start_date) if args.train_start_date else None
    train_end_date = date.fromisoformat(args.train_end_date) if args.train_end_date else None

    analysis_csv = _resolve_analysis_csv(args.analysis_csv)
    ordered_top, ordered_bottom = _parse_feature_rankings(analysis_csv)
    top_n = max(1, int(args.top_n))
    top_features = ordered_top[:top_n]
    bottom_features = ordered_bottom[:top_n]

    logger.info('Ablation started analysis_csv={} top_n={} train_start_date={} train_end_date={}', analysis_csv, top_n, train_start_date, train_end_date)

    original_whitelist = str(settings.ML_FEATURE_WHITELIST)
    original_top_k = int(settings.ML_FEATURE_TOP_K)
    model_type = args.model_type or str(settings.ML_MODEL_TYPE)

    baseline_whitelist = _split_whitelist(original_whitelist)
    if not baseline_whitelist:
        raise ValueError('Baseline ML_FEATURE_WHITELIST is empty; set it first to run ablation comparisons safely')

    top_features = _map_features_to_available(top_features, baseline_whitelist)
    bottom_features = _map_features_to_available(bottom_features, baseline_whitelist)

    drop_top_whitelist = [f for f in baseline_whitelist if f not in set(top_features)]
    drop_bottom_whitelist = [f for f in baseline_whitelist if f not in set(bottom_features)]

    dataset_service = MlDatasetService()
    model_service = MlModelService()

    dataset = dataset_service.build_training_dataset(
        horizon_days=int(settings.ML_HORIZON_DAYS),
        threshold_pct=float(settings.ML_MOVE_THRESHOLD_PCT),
        train_start_date=train_start_date,
        train_end_date=train_end_date,
    )

    if not dataset.records:
        raise ValueError('No training records found for requested date window')

    logger.info('Ablation dataset loaded records={} feature_keys={}', len(dataset.records), len(dataset.feature_keys))

    run_date = date.today()

    try:
        results: list[dict] = []

        results.append(
            _run_variant(
                name='baseline_whitelist',
                run_date=run_date,
                records=dataset.records,
                feature_keys=dataset.feature_keys,
                model_service=model_service,
                model_type=model_type,
                whitelist=baseline_whitelist,
                top_k=0,
            )
        )

        results.append(
            _run_variant(
                name=f'top_{top_n}_only',
                run_date=run_date,
                records=dataset.records,
                feature_keys=dataset.feature_keys,
                model_service=model_service,
                model_type=model_type,
                whitelist=top_features,
                top_k=0,
            )
        )

        if not drop_top_whitelist:
            raise ValueError('Drop-top variant has zero features after removal; reduce --top-n')
        results.append(
            _run_variant(
                name=f'drop_top_{top_n}',
                run_date=run_date,
                records=dataset.records,
                feature_keys=dataset.feature_keys,
                model_service=model_service,
                model_type=model_type,
                whitelist=drop_top_whitelist,
                top_k=0,
            )
        )

        if not drop_bottom_whitelist:
            raise ValueError('Drop-bottom variant has zero features after removal; reduce --top-n')
        results.append(
            _run_variant(
                name=f'drop_bottom_{top_n}',
                run_date=run_date,
                records=dataset.records,
                feature_keys=dataset.feature_keys,
                model_service=model_service,
                model_type=model_type,
                whitelist=drop_bottom_whitelist,
                top_k=0,
            )
        )

    finally:
        # Restore original runtime settings after experiment
        settings.ML_FEATURE_WHITELIST = original_whitelist
        settings.ML_FEATURE_TOP_K = original_top_k

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()

    frame = pd.DataFrame(results)
    csv_path = output_dir / f'feature_ablation_{stamp}.csv'
    frame.to_csv(csv_path, index=False)

    payload = {
        'analysis_csv': str(analysis_csv),
        'top_features': top_features,
        'bottom_features': bottom_features,
        'model_type': model_type,
        'train_start_date': str(train_start_date) if train_start_date else None,
        'train_end_date': str(train_end_date) if train_end_date else None,
        'results': results,
        'csv_path': str(csv_path),
    }

    json_path = output_dir / f'feature_ablation_{stamp}.json'
    json_path.write_text(json.dumps(payload, indent=2))

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
