"""Leakage-safe walk-forward model training and evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

from backtesting.config import ModelConfig
from utils.logger import logger


@dataclass
class ModelFoldResult:
    """Metrics captured for one walk-forward fold."""

    model_type: str
    fold_index: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    precision: float
    recall: float
    f1: float
    roc_auc: float
    profit_factor: float
    rows_train: int
    rows_test: int


class BaselineModelTrainingPipeline:
    """Train and evaluate baseline models with walk-forward windows."""

    def __init__(self, config: ModelConfig) -> None:
        self._config = config

    def run(self, dataset: pd.DataFrame, feature_columns: list[str], output_dir: str) -> dict[str, Any]:
        """Run walk-forward training for each configured model type."""
        if self._config.target_column not in dataset.columns:
            raise ValueError(f'Target column not found: {self._config.target_column}')

        frame = dataset.copy().sort_values('timestamp').reset_index(drop=True)
        frame['timestamp'] = pd.to_datetime(frame['timestamp'])

        valid = frame.dropna(subset=[self._config.target_column]).copy()
        valid[self._config.target_column] = valid[self._config.target_column].astype(int)
        valid = valid.replace([np.inf, -np.inf], np.nan)

        feature_columns = [column for column in feature_columns if column in valid.columns]
        if not feature_columns:
            raise ValueError('No valid feature columns available for model training')

        fold_specs = self._build_fold_windows(valid)
        if not fold_specs:
            raise ValueError('No walk-forward windows could be built from this dataset')

        all_results: dict[str, list[ModelFoldResult]] = {}
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for model_type in self._config.model_types:
            logger.info('Training model_type={} folds={}', model_type, len(fold_specs))
            fold_results: list[ModelFoldResult] = []
            for fold_index, train_start, train_end, test_start, test_end in fold_specs:
                train_mask = (valid['timestamp'] >= train_start) & (valid['timestamp'] <= train_end)
                test_mask = (valid['timestamp'] >= test_start) & (valid['timestamp'] <= test_end)

                train_frame = valid.loc[train_mask]
                test_frame = valid.loc[test_mask]

                if len(train_frame) < self._config.min_train_rows or len(test_frame) < self._config.min_test_rows:
                    continue

                x_train = train_frame[feature_columns].fillna(train_frame[feature_columns].median())
                y_train = train_frame[self._config.target_column]
                x_test = test_frame[feature_columns].fillna(train_frame[feature_columns].median())
                y_test = test_frame[self._config.target_column]

                if y_train.nunique() < 2 or y_test.nunique() < 2:
                    continue

                model = self._build_model(model_type)
                model.fit(x_train, y_train)

                probabilities = model.predict_proba(x_test)[:, 1]
                predictions = (probabilities >= self._config.probability_threshold).astype(int)

                future_return_col = self._infer_future_return_column(valid)
                profit_factor = self._profit_factor(test_frame, predictions, future_return_col)

                fold_results.append(
                    ModelFoldResult(
                        model_type=model_type,
                        fold_index=fold_index,
                        train_start=train_start,
                        train_end=train_end,
                        test_start=test_start,
                        test_end=test_end,
                        precision=float(precision_score(y_test, predictions, zero_division=0)),
                        recall=float(recall_score(y_test, predictions, zero_division=0)),
                        f1=float(f1_score(y_test, predictions, zero_division=0)),
                        roc_auc=float(roc_auc_score(y_test, probabilities)),
                        profit_factor=profit_factor,
                        rows_train=len(train_frame),
                        rows_test=len(test_frame),
                    )
                )

            all_results[model_type] = fold_results
            self._save_fold_results(fold_results, output_path / f'walk_forward_metrics_{model_type}.csv')

        summary = self._summarize(all_results)
        pd.DataFrame(summary).to_csv(output_path / 'walk_forward_summary.csv', index=False)

        return {'fold_results': all_results, 'summary': summary}

    def _build_model(self, model_type: str) -> Any:
        """Instantiate baseline model by type."""
        if model_type == 'xgb':
            import xgboost as xgb

            params = dict(self._config.xgb_params)
            params.setdefault('random_state', self._config.random_state)
            return xgb.XGBClassifier(**params)

        if model_type == 'lgb':
            import lightgbm as lgb

            params = dict(self._config.lgb_params)
            params.setdefault('random_state', self._config.random_state)
            return lgb.LGBMClassifier(**params)

        params = dict(self._config.rf_params)
        params.setdefault('random_state', self._config.random_state)
        return RandomForestClassifier(**params)

    def _build_fold_windows(
        self,
        frame: pd.DataFrame,
    ) -> list[tuple[int, pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]]:
        """Construct rolling walk-forward windows from dataset timestamps."""
        min_date = frame['timestamp'].min().normalize()
        max_date = frame['timestamp'].max().normalize()

        fold_index = 0
        test_start = min_date + timedelta(days=self._config.walk_forward_train_days)
        folds: list[tuple[int, pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]] = []

        while test_start + timedelta(days=self._config.walk_forward_test_days - 1) <= max_date:
            train_start = test_start - timedelta(days=self._config.walk_forward_train_days)
            train_end = test_start - timedelta(days=1)
            test_end = test_start + timedelta(days=self._config.walk_forward_test_days - 1)
            folds.append((fold_index, train_start, train_end, test_start, test_end))
            fold_index += 1
            test_start += timedelta(days=self._config.walk_forward_step_days)

        return folds

    def _infer_future_return_column(self, frame: pd.DataFrame) -> str:
        """Infer a future-return helper column to compute profit-factor-style metric."""
        candidates = sorted([column for column in frame.columns if column.startswith('future_return_')])
        if not candidates:
            raise ValueError('No future_return_* column found for profit-factor evaluation')
        preferred = f'future_return_{self._extract_window_from_target()}d'
        return preferred if preferred in candidates else candidates[0]

    def _extract_window_from_target(self) -> int:
        """Extract lookahead window from target naming convention."""
        parts = self._config.target_column.split('_')
        for part in parts:
            if part.endswith('d') and part[:-1].isdigit():
                return int(part[:-1])
        return 20

    def _profit_factor(self, frame: pd.DataFrame, predictions: np.ndarray, future_return_col: str) -> float:
        """Compute profit factor from predicted-positive strategy returns."""
        selected = frame.copy()
        selected['pred'] = predictions
        selected = selected[selected['pred'] == 1]
        if selected.empty:
            return 0.0

        returns = selected[future_return_col].fillna(0.0)
        gross_profit = float(returns[returns > 0].sum())
        gross_loss = float(-returns[returns < 0].sum())
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        return gross_profit / gross_loss

    def _save_fold_results(self, fold_results: list[ModelFoldResult], output_path: Path) -> None:
        """Persist fold-level metrics."""
        rows = [
            {
                'model_type': result.model_type,
                'fold_index': result.fold_index,
                'train_start': result.train_start,
                'train_end': result.train_end,
                'test_start': result.test_start,
                'test_end': result.test_end,
                'precision': result.precision,
                'recall': result.recall,
                'f1': result.f1,
                'roc_auc': result.roc_auc,
                'profit_factor': result.profit_factor,
                'rows_train': result.rows_train,
                'rows_test': result.rows_test,
            }
            for result in fold_results
        ]
        pd.DataFrame(rows).to_csv(output_path, index=False)

    def _summarize(self, all_results: dict[str, list[ModelFoldResult]]) -> list[dict[str, Any]]:
        """Aggregate fold-level metrics to model-level summary."""
        summary_rows: list[dict[str, Any]] = []

        for model_type, fold_results in all_results.items():
            if not fold_results:
                summary_rows.append(
                    {
                        'model_type': model_type,
                        'folds': 0,
                        'precision': 0.0,
                        'recall': 0.0,
                        'f1': 0.0,
                        'roc_auc': 0.0,
                        'profit_factor': 0.0,
                    }
                )
                continue

            frame = pd.DataFrame([
                {
                    'precision': result.precision,
                    'recall': result.recall,
                    'f1': result.f1,
                    'roc_auc': result.roc_auc,
                    'profit_factor': result.profit_factor,
                }
                for result in fold_results
            ])

            summary_rows.append(
                {
                    'model_type': model_type,
                    'folds': len(fold_results),
                    'precision': float(frame['precision'].mean()),
                    'recall': float(frame['recall'].mean()),
                    'f1': float(frame['f1'].mean()),
                    'roc_auc': float(frame['roc_auc'].mean()),
                    'profit_factor': float(frame['profit_factor'].replace([np.inf, -np.inf], np.nan).fillna(0.0).mean()),
                }
            )

        return summary_rows
