"""Leakage-safe walk-forward model training and evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

try:
    from sklearn.frozen import FrozenEstimator
except Exception:  # pragma: no cover - sklearn version dependent
    FrozenEstimator = None

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
    applied_threshold: float
    threshold_objective_score: float
    calibration_used: bool
    calibration_rows: int
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
        future_return_col = self._infer_future_return_column(valid)

        for model_type in self._config.model_types:
            model_started = perf_counter()
            logger.info(
                'Training baseline_model model_type={} folds={} calibration={} threshold_opt={}',
                model_type,
                len(fold_specs),
                self._config.calibration_enabled,
                self._config.threshold_optimization_enabled,
            )
            fold_results: list[ModelFoldResult] = []
            for fold_index, train_start, train_end, test_start, test_end in fold_specs:
                fold_started = perf_counter()
                train_mask = (valid['timestamp'] >= train_start) & (valid['timestamp'] <= train_end)
                test_mask = (valid['timestamp'] >= test_start) & (valid['timestamp'] <= test_end)

                train_frame = valid.loc[train_mask]
                test_frame = valid.loc[test_mask]

                if len(train_frame) < self._config.min_train_rows or len(test_frame) < self._config.min_test_rows:
                    logger.info(
                        'Fold {} skipped model_type={} reason=insufficient_rows train_rows={} test_rows={} required_train={} required_test={}',
                        fold_index,
                        model_type,
                        len(train_frame),
                        len(test_frame),
                        self._config.min_train_rows,
                        self._config.min_test_rows,
                    )
                    continue

                fit_frame, calibration_frame = self._split_train_calibration(train_frame)
                x_train = fit_frame[feature_columns].fillna(fit_frame[feature_columns].median())
                y_train = fit_frame[self._config.target_column]
                x_test = test_frame[feature_columns].fillna(fit_frame[feature_columns].median())
                y_test = test_frame[self._config.target_column]

                if y_train.nunique() < 2 or y_test.nunique() < 2:
                    logger.info(
                        'Fold {} skipped model_type={} reason=insufficient_label_variance train_classes={} test_classes={}',
                        fold_index,
                        model_type,
                        int(y_train.nunique()),
                        int(y_test.nunique()),
                    )
                    continue

                logger.info(
                    'Fold {} starting model_type={} train_range=[{}, {}] test_range=[{}, {}] rows_fit={} rows_calibration={} rows_test={}',
                    fold_index,
                    model_type,
                    train_start.date(),
                    train_end.date(),
                    test_start.date(),
                    test_end.date(),
                    len(fit_frame),
                    len(calibration_frame),
                    len(test_frame),
                )

                x_calibration = pd.DataFrame()
                y_calibration = pd.Series(dtype=int)
                calibration_rows = 0
                if not calibration_frame.empty:
                    x_calibration = calibration_frame[feature_columns].fillna(fit_frame[feature_columns].median())
                    y_calibration = calibration_frame[self._config.target_column]
                    calibration_rows = len(calibration_frame)

                model = self._build_model(model_type)
                model.fit(x_train, y_train)

                calibrated_estimator, calibration_used = self._maybe_calibrate(
                    model=model,
                    x_calibration=x_calibration,
                    y_calibration=y_calibration,
                )

                probabilities = calibrated_estimator.predict_proba(x_test)[:, 1]

                threshold, threshold_objective_score = self._resolve_threshold(
                    estimator=calibrated_estimator,
                    calibration_frame=calibration_frame,
                    x_calibration=x_calibration,
                    y_calibration=y_calibration,
                    future_return_col=future_return_col,
                )
                predictions = (probabilities >= threshold).astype(int)

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
                        applied_threshold=float(threshold),
                        threshold_objective_score=float(threshold_objective_score),
                        calibration_used=bool(calibration_used),
                        calibration_rows=int(calibration_rows),
                        rows_train=len(fit_frame),
                        rows_test=len(test_frame),
                    )
                )
                logger.info(
                    'Fold {} complete model_type={} runtime_s={:.2f} threshold={:.3f} objective_score={:.3f} f1={:.3f} precision={:.3f} recall={:.3f} pf={:.3f} calibration_used={} roc_auc={:.3f}',
                    fold_index,
                    model_type,
                    perf_counter() - fold_started,
                    threshold,
                    threshold_objective_score,
                    f1_score(y_test, predictions, zero_division=0),
                    precision_score(y_test, predictions, zero_division=0),
                    recall_score(y_test, predictions, zero_division=0),
                    profit_factor,
                    calibration_used,
                    roc_auc_score(y_test, probabilities),
                )

            all_results[model_type] = fold_results
            self._save_fold_results(fold_results, output_path / f'walk_forward_metrics_{model_type}.csv')
            logger.info(
                'Model {} complete folds_trained={} avg_f1={:.3f} avg_threshold={:.3f} calibration_rate={}',
                model_type,
                len(fold_results),
                float(pd.Series([r.f1 for r in fold_results]).mean()) if fold_results else 0.0,
                float(pd.Series([r.applied_threshold for r in fold_results]).mean()) if fold_results else 0.0,
                f'{100 * pd.Series([r.calibration_used for r in fold_results]).mean():.1f}%' if fold_results else '0%',
            )
            logger.info('Model {} runtime_s={:.2f}', model_type, perf_counter() - model_started)

        summary = self._summarize(all_results)
        pd.DataFrame(summary).to_csv(output_path / 'walk_forward_summary.csv', index=False)
        logger.info('Walk-forward training complete output_dir={}', output_dir)

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

    def _split_train_calibration(self, train_frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Split in-window train data into fit and calibration slices (chronological)."""
        if not self._config.calibration_enabled and not self._config.threshold_optimization_enabled:
            logger.debug('Calibration and threshold optimization both disabled; using full training set')
            return train_frame, pd.DataFrame(columns=train_frame.columns)

        if len(train_frame) < (self._config.calibration_min_rows * 2):
            logger.debug(
                'Train frame too small for split ({} < {}) ; skipping calibration',
                len(train_frame),
                self._config.calibration_min_rows * 2,
            )
            return train_frame, pd.DataFrame(columns=train_frame.columns)

        split_size = max(self._config.calibration_min_rows, int(len(train_frame) * self._config.calibration_fraction))
        split_size = min(split_size, len(train_frame) - self._config.calibration_min_rows)
        if split_size <= 0:
            logger.debug('Invalid split size; skipping calibration')
            return train_frame, pd.DataFrame(columns=train_frame.columns)

        fit_frame = train_frame.iloc[:-split_size].copy()
        calibration_frame = train_frame.iloc[-split_size:].copy()
        logger.debug(
            'Split train window: fit_rows={} calibration_rows={} (fraction={})',
            len(fit_frame),
            len(calibration_frame),
            self._config.calibration_fraction,
        )
        return fit_frame, calibration_frame

    def _maybe_calibrate(
        self,
        model: Any,
        x_calibration: pd.DataFrame,
        y_calibration: pd.Series,
    ) -> tuple[Any, bool]:
        """Apply probability calibration using calibration split when available."""
        if not self._config.calibration_enabled:
            logger.debug('Calibration disabled by config')
            return model, False

        if x_calibration.empty or y_calibration.empty or y_calibration.nunique() < 2:
            logger.debug('Calibration data unavailable or insufficient labels; skipping')
            return model, False

        try:
            if FrozenEstimator is not None:
                calibrated = CalibratedClassifierCV(
                    estimator=FrozenEstimator(model),
                    method=self._config.calibration_method,
                )
            else:
                calibrated = CalibratedClassifierCV(
                    estimator=model,
                    method=self._config.calibration_method,
                    cv='prefit',
                )
            calibrated.fit(x_calibration, y_calibration)
            logger.info(
                'Calibration succeeded method={} rows={} pos_rate={}',
                self._config.calibration_method,
                len(x_calibration),
                float(y_calibration.mean()),
            )
            return calibrated, True
        except Exception as err:
            logger.warning('Calibration failed ({}); using uncalibrated model', str(err))
            return model, False

    def _resolve_threshold(
        self,
        estimator: Any,
        calibration_frame: pd.DataFrame,
        x_calibration: pd.DataFrame,
        y_calibration: pd.Series,
        future_return_col: str,
    ) -> tuple[float, float]:
        """Select fold threshold by configured objective on calibration data."""
        base_threshold = float(self._config.probability_threshold)
        if not self._config.threshold_optimization_enabled:
            logger.debug('Threshold optimization disabled by config')
            return base_threshold, 0.0

        if calibration_frame.empty or x_calibration.empty or y_calibration.empty or y_calibration.nunique() < 2:
            logger.info('Threshold optimization skipped; using base threshold={}', base_threshold)
            return base_threshold, 0.0

        probabilities = estimator.predict_proba(x_calibration)[:, 1]
        thresholds = np.arange(
            self._config.threshold_search_min,
            self._config.threshold_search_max + 1e-9,
            self._config.threshold_search_step,
        )
        if thresholds.size == 0:
            logger.warning('Threshold search range empty; using base threshold={}', base_threshold)
            return base_threshold, 0.0

        best_threshold = base_threshold
        best_score = float('-inf')
        search_results = []

        for threshold in thresholds:
            predictions = (probabilities >= threshold).astype(int)
            if self._config.threshold_objective == 'profit_factor':
                score = self._profit_factor(calibration_frame, predictions, future_return_col)
            else:
                score = float(f1_score(y_calibration, predictions, zero_division=0))

            search_results.append((threshold, score))
            if score > best_score:
                best_score = score
                best_threshold = float(threshold)

        if not np.isfinite(best_score):
            logger.warning('Threshold search produced no finite scores; using base threshold={}', base_threshold)
            return base_threshold, 0.0

        logger.info(
            'Threshold optimization complete objective={} best_threshold={} best_score={} search_points={}',
            self._config.threshold_objective,
            best_threshold,
            best_score,
            len(search_results),
        )
        return best_threshold, float(best_score)

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
                'applied_threshold': result.applied_threshold,
                'threshold_objective_score': result.threshold_objective_score,
                'calibration_used': result.calibration_used,
                'calibration_rows': result.calibration_rows,
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
                        'profit_factor_mean_finite': 0.0,
                        'profit_factor_median_finite': 0.0,
                        'profit_factor_inf_folds': 0,
                        'profit_factor_valid_folds': 0,
                        'applied_threshold': 0.0,
                        'calibration_usage_rate': 0.0,
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
                    'applied_threshold': result.applied_threshold,
                    'calibration_used': float(result.calibration_used),
                }
                for result in fold_results
            ])

            profit_factor_series = frame['profit_factor']
            finite_profit_factor = profit_factor_series.replace([np.inf, -np.inf], np.nan)
            finite_profit_factor = finite_profit_factor.dropna()
            inf_profit_factor_folds = int(np.isinf(profit_factor_series).sum())
            finite_profit_factor_mean = float(finite_profit_factor.mean()) if not finite_profit_factor.empty else 0.0
            finite_profit_factor_median = float(finite_profit_factor.median()) if not finite_profit_factor.empty else 0.0

            summary_rows.append(
                {
                    'model_type': model_type,
                    'folds': len(fold_results),
                    'precision': float(frame['precision'].mean()),
                    'recall': float(frame['recall'].mean()),
                    'f1': float(frame['f1'].mean()),
                    'roc_auc': float(frame['roc_auc'].mean()),
                    'profit_factor': finite_profit_factor_mean,
                    'profit_factor_mean_finite': finite_profit_factor_mean,
                    'profit_factor_median_finite': finite_profit_factor_median,
                    'profit_factor_inf_folds': inf_profit_factor_folds,
                    'profit_factor_valid_folds': int(finite_profit_factor.shape[0]),
                    'applied_threshold': float(frame['applied_threshold'].mean()),
                    'calibration_usage_rate': float(frame['calibration_used'].mean()),
                }
            )

        return summary_rows
