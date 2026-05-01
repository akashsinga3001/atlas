"""Model training, calibration, and inference for directional stock movement prediction."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score, recall_score

from config import settings
from utils.ml_paths import weekly_run_directory


@dataclass
class ModelTrainingResult:
    """Holds outputs produced by one weekly model training run."""

    long_model_path: str
    short_model_path: str
    feature_columns: list[str]
    feature_statistics: dict[str, dict[str, float]]
    long_metrics: dict[str, float]
    short_metrics: dict[str, float]
    long_feature_importance: list[dict[str, float | str]]
    short_feature_importance: list[dict[str, float | str]]
    samples_total: int
    samples_train: int
    samples_validation: int
    long_positive_rate_pct: float
    short_positive_rate_pct: float
    model_type: str  # 'rf', 'lgb', 'xgb', or 'ensemble'


class MlModelService:
    """Train two binary models (long/short) and score inference candidates."""

    def train(
        self,
        run_date: date,
        records: list[dict[str, Any]],
        feature_keys: list[str],
        model_type: str = 'rf',
    ) -> ModelTrainingResult:
        """Train long and short models with a date-based validation split.

        Args:
            run_date: The reference date used to name artifact directories.
            records: Labeled feature rows from the dataset builder.
            feature_keys: Ordered list of feature names.
            model_type: One of 'rf', 'lgb', 'xgb', or 'ensemble'.

        Returns:
            ModelTrainingResult with trained model paths and evaluation metrics.
        """
        if not records:
            raise ValueError('No training records available for model fitting')

        dataframe = self._records_to_frame(records, feature_keys)
        unique_dates = sorted(dataframe['prediction_date'].unique().tolist())
        if len(unique_dates) < 4:
            raise ValueError('Not enough distinct dates for time-based validation split')

        validation_dates = self._validation_dates(unique_dates)
        validation_mask = dataframe['prediction_date'].isin(validation_dates)
        training_mask = ~validation_mask

        if int(training_mask.sum()) < 300:
            raise ValueError('Insufficient training samples after time split')
        if int(validation_mask.sum()) < 50:
            raise ValueError('Insufficient validation samples after time split')

        feature_frame = dataframe.drop(columns=['prediction_date', 'security_id', 'ticker', 'long_label', 'short_label'])
        encoded = pd.get_dummies(feature_frame, dummy_na=True)
        feature_columns = encoded.columns.tolist()

        x_train = encoded.loc[training_mask]
        x_val = encoded.loc[validation_mask]
        y_long_train = dataframe.loc[training_mask, 'long_label']
        y_long_val = dataframe.loc[validation_mask, 'long_label']
        y_short_train = dataframe.loc[training_mask, 'short_label']
        y_short_val = dataframe.loc[validation_mask, 'short_label']

        long_model_bundle = self._train_bundle(model_type, x_train, y_long_train, x_val, y_long_val)
        short_model_bundle = self._train_bundle(model_type, x_train, y_short_train, x_val, y_short_val)

        feature_statistics = self._feature_statistics(x_train)
        run_directory = weekly_run_directory(settings.ML_ARTIFACT_DIR, run_date)
        long_model_path = self._persist_bundle(run_directory, f'long_{model_type}.joblib', long_model_bundle, feature_columns, feature_statistics)
        short_model_path = self._persist_bundle(run_directory, f'short_{model_type}.joblib', short_model_bundle, feature_columns, feature_statistics)

        return ModelTrainingResult(
            long_model_path=long_model_path,
            short_model_path=short_model_path,
            feature_columns=feature_columns,
            feature_statistics=feature_statistics,
            long_metrics=long_model_bundle['metrics'],
            short_metrics=short_model_bundle['metrics'],
            long_feature_importance=long_model_bundle['feature_importance'],
            short_feature_importance=short_model_bundle['feature_importance'],
            samples_total=len(dataframe),
            samples_train=int(training_mask.sum()),
            samples_validation=int(validation_mask.sum()),
            long_positive_rate_pct=float(dataframe['long_label'].mean()) * 100.0,
            short_positive_rate_pct=float(dataframe['short_label'].mean()) * 100.0,
            model_type=model_type,
        )

    def score_direction(
        self,
        records: list[dict[str, Any]],
        feature_keys: list[str],
        model_path: str,
        direction: str,
        top_n: int,
    ) -> list[dict[str, Any]]:
        """Score one direction and return ranked predictions with explanations.

        Args:
            records: Inference feature rows (no labels required).
            feature_keys: Ordered feature key list from dataset builder.
            model_path: Path to joblib artifact file.
            direction: 'long' or 'short'.
            top_n: Maximum number of ranked predictions to return.

        Returns:
            List of prediction dicts with confidence, rank, and feature drivers.
        """
        if not records:
            return []

        model_bundle = joblib.load(model_path)
        feature_columns = model_bundle['feature_columns']
        feature_statistics = model_bundle['feature_statistics']

        frame = self._records_to_frame(records, feature_keys, include_labels=False)
        metadata = frame[['prediction_date', 'security_id', 'ticker']].copy()
        feature_frame = frame.drop(columns=['prediction_date', 'security_id', 'ticker'])
        encoded = pd.get_dummies(feature_frame, dummy_na=True)
        aligned = encoded.reindex(columns=feature_columns, fill_value=0.0)

        estimator = model_bundle['calibrated_model']
        confidence = estimator.predict_proba(aligned)[:, 1]

        metadata['direction'] = direction
        metadata['confidence'] = confidence
        metadata = metadata.sort_values(['confidence', 'ticker'], ascending=[False, True]).reset_index(drop=True)
        metadata['rank'] = metadata.index + 1
        metadata['rank'] = metadata['rank'].where(metadata['rank'] <= top_n, None)

        predictions: list[dict[str, Any]] = []
        for index, row in metadata.iterrows():
            rank_value = row['rank']
            normalized_rank = int(rank_value) if pd.notna(rank_value) else None
            top_features = self._top_feature_drivers(
                row_index=index,
                aligned_features=aligned,
                feature_importance=model_bundle['feature_importance'],
                feature_statistics=feature_statistics,
            )
            predictions.append(
                {
                    'prediction_date': row['prediction_date'],
                    'security_id': int(row['security_id']),
                    'ticker': row['ticker'],
                    'direction': direction,
                    'confidence': float(row['confidence']),
                    'rank': normalized_rank,
                    'top_features': top_features,
                }
            )

        return predictions

    # ── Bundle Dispatcher ──────────────────────────────────────────────────────

    def _train_bundle(
        self,
        model_type: str,
        x_train: pd.DataFrame,
        y_train: pd.Series,
        x_val: pd.DataFrame,
        y_val: pd.Series,
    ) -> dict[str, Any]:
        """Dispatch to the correct training method based on model_type.

        Args:
            model_type: One of 'rf', 'lgb', 'xgb', or 'ensemble'.
            x_train: Training feature matrix.
            y_train: Training labels.
            x_val: Validation feature matrix.
            y_val: Validation labels.

        Returns:
            Bundle dict with calibrated_model, metrics, and feature_importance.
        """
        if model_type == 'lgb':
            return self._train_lgb_bundle(x_train, y_train, x_val, y_val)
        if model_type == 'xgb':
            return self._train_xgb_bundle(x_train, y_train, x_val, y_val)
        if model_type == 'ensemble':
            return self._train_ensemble_bundle(x_train, y_train, x_val, y_val)
        return self._train_rf_bundle(x_train, y_train, x_val, y_val)

    # ── Individual Model Trainers ──────────────────────────────────────────────

    def _train_rf_bundle(
        self,
        x_train: pd.DataFrame,
        y_train: pd.Series,
        x_val: pd.DataFrame,
        y_val: pd.Series,
    ) -> dict[str, Any]:
        """Fit RandomForest classifier with sigmoid calibration.

        Args:
            x_train: Training feature matrix.
            y_train: Training labels.
            x_val: Validation feature matrix.
            y_val: Validation labels.

        Returns:
            Bundle dict with calibrated_model, metrics, and feature_importance.
        """
        model = RandomForestClassifier(
            n_estimators=500,
            max_depth=8,
            min_samples_leaf=10,
            class_weight='balanced_subsample',
            random_state=42,
            n_jobs=-1,
        )
        model.fit(x_train, y_train)

        calibrated_model: Any = self._calibrate(model, x_val, y_val)
        scores = calibrated_model.predict_proba(x_val)[:, 1]
        metrics = self._compute_metrics(y_val, scores)

        feature_importance = self._extract_rf_importance(model, x_train.columns.tolist())
        return {'model': model, 'calibrated_model': calibrated_model, 'metrics': metrics, 'feature_importance': feature_importance}

    def _train_lgb_bundle(
        self,
        x_train: pd.DataFrame,
        y_train: pd.Series,
        x_val: pd.DataFrame,
        y_val: pd.Series,
    ) -> dict[str, Any]:
        """Fit LightGBM classifier with sigmoid calibration.

        Args:
            x_train: Training feature matrix.
            y_train: Training labels.
            x_val: Validation feature matrix.
            y_val: Validation labels.

        Returns:
            Bundle dict with calibrated_model, metrics, and feature_importance.
        """
        import lightgbm as lgb

        model = lgb.LGBMClassifier(
            n_estimators=500,
            max_depth=8,
            learning_rate=0.05,
            num_leaves=63,
            min_child_samples=10,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )
        model.fit(x_train, y_train, eval_set=[(x_val, y_val)])

        calibrated_model: Any = self._calibrate(model, x_val, y_val)
        scores = calibrated_model.predict_proba(x_val)[:, 1]
        metrics = self._compute_metrics(y_val, scores)

        feature_importance = [
            {'feature': feat, 'importance': float(imp)}
            for feat, imp in sorted(zip(x_train.columns.tolist(), model.feature_importances_), key=lambda t: t[1], reverse=True)
        ]
        return {'model': model, 'calibrated_model': calibrated_model, 'metrics': metrics, 'feature_importance': feature_importance}

    def _train_xgb_bundle(
        self,
        x_train: pd.DataFrame,
        y_train: pd.Series,
        x_val: pd.DataFrame,
        y_val: pd.Series,
    ) -> dict[str, Any]:
        """Fit XGBoost classifier with sigmoid calibration.

        Args:
            x_train: Training feature matrix.
            y_train: Training labels.
            x_val: Validation feature matrix.
            y_val: Validation labels.

        Returns:
            Bundle dict with calibrated_model, metrics, and feature_importance.
        """
        import xgboost as xgb

        scale_pos_weight = float((y_train == 0).sum()) / float((y_train == 1).sum()) if (y_train == 1).sum() > 0 else 1.0

        model = xgb.XGBClassifier(
            n_estimators=500,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            random_state=42,
            n_jobs=-1,
            eval_metric='logloss',
            verbosity=0,
        )
        model.fit(x_train, y_train, eval_set=[(x_val, y_val)], verbose=False)

        calibrated_model: Any = self._calibrate(model, x_val, y_val)
        scores = calibrated_model.predict_proba(x_val)[:, 1]
        metrics = self._compute_metrics(y_val, scores)

        feature_importance = [
            {'feature': feat, 'importance': float(imp)}
            for feat, imp in sorted(zip(x_train.columns.tolist(), model.feature_importances_), key=lambda t: t[1], reverse=True)
        ]
        return {'model': model, 'calibrated_model': calibrated_model, 'metrics': metrics, 'feature_importance': feature_importance}

    def _train_ensemble_bundle(
        self,
        x_train: pd.DataFrame,
        y_train: pd.Series,
        x_val: pd.DataFrame,
        y_val: pd.Series,
    ) -> dict[str, Any]:
        """Fit RF + LightGBM + XGBoost and combine via soft voting (averaged probabilities).

        Args:
            x_train: Training feature matrix.
            y_train: Training labels.
            x_val: Validation feature matrix.
            y_val: Validation labels.

        Returns:
            Bundle dict with an EnsembleVoter as calibrated_model, combined metrics and importance.
        """
        rf_bundle = self._train_rf_bundle(x_train, y_train, x_val, y_val)
        lgb_bundle = self._train_lgb_bundle(x_train, y_train, x_val, y_val)
        xgb_bundle = self._train_xgb_bundle(x_train, y_train, x_val, y_val)

        ensemble = _EnsembleVoter(
            models=[rf_bundle['calibrated_model'], lgb_bundle['calibrated_model'], xgb_bundle['calibrated_model']],
            weights=[1.0, 1.0, 1.0],
        )
        scores = ensemble.predict_proba(x_val)[:, 1]
        metrics = self._compute_metrics(y_val, scores)

        # Merge feature importance: average across all three models
        importance_map: dict[str, float] = {}
        for bundle in (rf_bundle, lgb_bundle, xgb_bundle):
            for item in bundle['feature_importance']:
                feat = str(item['feature'])
                importance_map[feat] = importance_map.get(feat, 0.0) + float(item['importance']) / 3.0
        feature_importance = sorted(
            [{'feature': k, 'importance': v} for k, v in importance_map.items()],
            key=lambda t: t['importance'],
            reverse=True,
        )

        # Store sub-model metrics for comparison
        metrics['rf_precision'] = rf_bundle['metrics']['precision']
        metrics['lgb_precision'] = lgb_bundle['metrics']['precision']
        metrics['xgb_precision'] = xgb_bundle['metrics']['precision']

        return {
            'model': ensemble,
            'calibrated_model': ensemble,
            'sub_bundles': {'rf': rf_bundle, 'lgb': lgb_bundle, 'xgb': xgb_bundle},
            'metrics': metrics,
            'feature_importance': feature_importance,
        }

    # ── Shared Helpers ─────────────────────────────────────────────────────────

    def _calibrate(self, model: Any, x_val: pd.DataFrame, y_val: pd.Series) -> Any:
        """Wrap a trained model in sigmoid calibration if the validation set has both classes.

        Args:
            model: Fitted classifier.
            x_val: Validation features.
            y_val: Validation labels.

        Returns:
            Calibrated model or original model if calibration is not possible.
        """
        if y_val.nunique() > 1:
            calibrated: Any = CalibratedClassifierCV(model, method='sigmoid', cv='prefit')
            calibrated.fit(x_val, y_val)
            return calibrated
        return model

    def _compute_metrics(self, y_val: pd.Series, scores: Any) -> dict[str, float]:
        """Compute standard classification metrics from validation scores.

        Args:
            y_val: True validation labels.
            scores: Predicted positive-class probabilities.

        Returns:
            Dict with precision, recall, precision_at_5, precision_at_10.
        """
        labels = (scores >= 0.5).astype(int)
        return {
            'precision': float(precision_score(y_val, labels, zero_division=0)),
            'recall': float(recall_score(y_val, labels, zero_division=0)),
            'precision_at_5': float(self._precision_at_k(y_val, scores, 5)),
            'precision_at_10': float(self._precision_at_k(y_val, scores, 10)),
        }

    def _extract_rf_importance(self, model: RandomForestClassifier, columns: list[str]) -> list[dict[str, float | str]]:
        """Extract and sort RandomForest feature importances.

        Args:
            model: Fitted RandomForestClassifier.
            columns: Feature column names matching model's input.

        Returns:
            Sorted list of {feature, importance} dicts descending by importance.
        """
        importance: list[dict[str, float | str]] = [
            {'feature': feat, 'importance': float(imp)}
            for feat, imp in zip(columns, model.feature_importances_)
        ]
        importance.sort(key=lambda item: float(item['importance']), reverse=True)
        return importance

    def _records_to_frame(self, records: list[dict[str, Any]], feature_keys: list[str], include_labels: bool = True) -> pd.DataFrame:
        """Flatten record payloads into a model-ready DataFrame.

        Args:
            records: Feature row dicts from the dataset builder.
            feature_keys: Ordered list of feature names.
            include_labels: Whether to include long_label and short_label columns.

        Returns:
            Flat DataFrame with one row per record.
        """
        flattened_rows: list[dict[str, Any]] = []
        for row in records:
            flat = {
                'prediction_date': row['prediction_date'],
                'security_id': row['security_id'],
                'ticker': row['ticker'],
            }
            for key in feature_keys:
                flat[key] = row['features'].get(key, 0)
            if include_labels:
                flat['long_label'] = row['long_label']
                flat['short_label'] = row['short_label']
            flattened_rows.append(flat)

        return pd.DataFrame(flattened_rows)

    def _validation_dates(self, unique_dates: list[date]) -> set[date]:
        """Take latest 20% dates as validation window.

        Args:
            unique_dates: Sorted list of unique dates in the dataset.

        Returns:
            Set of dates to use for validation.
        """
        validation_count = max(1, int(len(unique_dates) * 0.2))
        return set(unique_dates[-validation_count:])

    def _precision_at_k(self, labels: pd.Series, scores: Any, k: int) -> float:
        """Compute precision over top-k scored rows.

        Args:
            labels: True binary labels.
            scores: Predicted probabilities.
            k: Number of top predictions to evaluate.

        Returns:
            Precision@K value between 0 and 1.
        """
        if len(labels) == 0:
            return 0.0
        top_k = min(k, len(labels))
        ranked = pd.DataFrame({'label': labels.values, 'score': scores}).sort_values('score', ascending=False).head(top_k)
        if len(ranked) == 0:
            return 0.0
        return float(ranked['label'].sum()) / float(len(ranked))

    def _feature_statistics(self, frame: pd.DataFrame) -> dict[str, dict[str, float]]:
        """Store train statistics used for per-stock contribution estimates.

        Args:
            frame: Training feature matrix (already encoded).

        Returns:
            Dict of {column: {mean, std}} for z-score normalisation.
        """
        statistics: dict[str, dict[str, float]] = {}
        for column in frame.columns:
            series = frame[column]
            statistics[column] = {
                'mean': float(series.mean()),
                'std': float(series.std()) if float(series.std()) > 0 else 1.0,
            }
        return statistics

    def _persist_bundle(
        self,
        run_directory: Path,
        file_name: str,
        bundle: dict[str, Any],
        feature_columns: list[str],
        feature_statistics: dict[str, dict[str, float]],
    ) -> str:
        """Persist one model bundle to disk and return file path.

        Args:
            run_directory: Directory under which the file is saved.
            file_name: Filename for the joblib artifact.
            bundle: Model bundle dict from a training method.
            feature_columns: Ordered list of feature column names.
            feature_statistics: Per-column mean/std statistics.

        Returns:
            Absolute path string of the saved file.
        """
        payload = {
            'model': bundle['model'],
            'calibrated_model': bundle['calibrated_model'],
            'metrics': bundle['metrics'],
            'feature_importance': bundle['feature_importance'],
            'feature_columns': feature_columns,
            'feature_statistics': feature_statistics,
        }
        path = run_directory / file_name
        joblib.dump(payload, path)
        return str(path)

    def _top_feature_drivers(
        self,
        row_index: int,
        aligned_features: pd.DataFrame,
        feature_importance: list[dict[str, float | str]],
        feature_statistics: dict[str, dict[str, float]],
    ) -> list[dict[str, float | str]]:
        """Approximate top per-stock drivers using z-score weighted importances.

        Args:
            row_index: Row position in aligned_features for this stock.
            aligned_features: Full encoded inference feature matrix.
            feature_importance: Sorted list of {feature, importance} dicts.
            feature_statistics: Per-feature {mean, std} from training data.

        Returns:
            Top 3 contributing features with their values and contribution scores.
        """
        top_candidates: list[dict[str, float | str]] = []
        for item in feature_importance[:20]:
            feature_name = str(item['feature'])
            importance = float(item['importance'])
            value = float(aligned_features.iloc[row_index][feature_name])
            stats = feature_statistics.get(feature_name, {'mean': 0.0, 'std': 1.0})
            z_score = abs((value - float(stats['mean'])) / max(float(stats['std']), 1e-9))
            contribution = z_score * importance
            top_candidates.append({'feature': feature_name, 'value': value, 'contribution': contribution})

        top_candidates.sort(key=lambda item: float(item['contribution']), reverse=True)
        return top_candidates[:3]


class _EnsembleVoter:
    """Soft-voting ensemble that averages predicted probabilities from multiple classifiers."""

    def __init__(self, models: list[Any], weights: list[float]) -> None:
        """Initialise with a list of fitted calibrated classifiers and weights.

        Args:
            models: List of fitted classifiers each exposing predict_proba().
            weights: Per-model weight (will be normalised to sum to 1).
        """
        self._models = models
        total = sum(weights)
        self._weights = [w / total for w in weights]

    def predict_proba(self, x: pd.DataFrame) -> Any:
        """Average calibrated probabilities across all member models.

        Args:
            x: Feature matrix aligned to the common feature column list.

        Returns:
            Numpy array of shape (n_samples, 2) with averaged class probabilities.
        """
        import numpy as np

        weighted_sum = sum(
            model.predict_proba(x) * weight
            for model, weight in zip(self._models, self._weights)
        )
        return weighted_sum

