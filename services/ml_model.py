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


class MlModelService:
    """Train two binary models (long/short) and score inference candidates."""

    def train(
        self,
        run_date: date,
        records: list[dict[str, Any]],
        feature_keys: list[str],
    ) -> ModelTrainingResult:
        """Train long and short models with a date-based validation split."""
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

        long_model_bundle = self._train_binary_bundle(x_train, y_long_train, x_val, y_long_val)
        short_model_bundle = self._train_binary_bundle(x_train, y_short_train, x_val, y_short_val)

        feature_statistics = self._feature_statistics(x_train)

        run_directory = weekly_run_directory(settings.ML_ARTIFACT_DIR, run_date)
        long_model_path = self._persist_bundle(run_directory, 'long_model.joblib', long_model_bundle, feature_columns, feature_statistics)
        short_model_path = self._persist_bundle(run_directory, 'short_model.joblib', short_model_bundle, feature_columns, feature_statistics)

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
        )

    def score_direction(
        self,
        records: list[dict[str, Any]],
        feature_keys: list[str],
        model_path: str,
        direction: str,
        top_n: int,
    ) -> list[dict[str, Any]]:
        """Score one direction and return ranked predictions with explanations."""
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

    def _train_binary_bundle(
        self,
        x_train: pd.DataFrame,
        y_train: pd.Series,
        x_val: pd.DataFrame,
        y_val: pd.Series,
    ) -> dict[str, Any]:
        """Fit classifier + calibration and compute validation metrics."""
        model = RandomForestClassifier(
            n_estimators=500,
            max_depth=8,
            min_samples_leaf=10,
            class_weight='balanced_subsample',
            random_state=42,
            n_jobs=-1,
        )
        model.fit(x_train, y_train)

        if y_val.nunique() > 1:
            calibrated_model: Any = CalibratedClassifierCV(model, method='sigmoid', cv='prefit')
            calibrated_model.fit(x_val, y_val)
        else:
            calibrated_model = model

        scores = calibrated_model.predict_proba(x_val)[:, 1]
        labels = (scores >= 0.5).astype(int)

        metrics = {
            'precision': float(precision_score(y_val, labels, zero_division=0)),
            'recall': float(recall_score(y_val, labels, zero_division=0)),
            'precision_at_5': float(self._precision_at_k(y_val, scores, 5)),
            'precision_at_10': float(self._precision_at_k(y_val, scores, 10)),
        }

        feature_importance: list[dict[str, float | str]] = [
            {
                'feature': feature,
                'importance': float(importance),
            }
            for feature, importance in zip(x_train.columns.tolist(), model.feature_importances_)
        ]
        feature_importance.sort(key=lambda item: float(item['importance']), reverse=True)

        return {
            'model': model,
            'calibrated_model': calibrated_model,
            'metrics': metrics,
            'feature_importance': feature_importance,
        }

    def _records_to_frame(self, records: list[dict[str, Any]], feature_keys: list[str], include_labels: bool = True) -> pd.DataFrame:
        """Flatten record payloads into a model-ready DataFrame."""
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
        """Take latest 20% dates as validation window."""
        validation_count = max(1, int(len(unique_dates) * 0.2))
        return set(unique_dates[-validation_count:])

    def _precision_at_k(self, labels: pd.Series, scores: Any, k: int) -> float:
        """Compute precision over top-k scored rows."""
        if len(labels) == 0:
            return 0.0
        top_k = min(k, len(labels))
        ranked = pd.DataFrame({'label': labels.values, 'score': scores}).sort_values('score', ascending=False).head(top_k)
        if len(ranked) == 0:
            return 0.0
        return float(ranked['label'].sum()) / float(len(ranked))

    def _feature_statistics(self, frame: pd.DataFrame) -> dict[str, dict[str, float]]:
        """Store train statistics used for simple per-stock contribution estimates."""
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
        """Persist one model bundle to disk and return file path."""
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
        """Approximate top per-stock drivers using z-score weighted importances."""
        top_candidates: list[dict[str, float | str]] = []
        capped_importance = feature_importance[:20]

        for item in capped_importance:
            feature_name = str(item['feature'])
            importance = float(item['importance'])
            value = float(aligned_features.iloc[row_index][feature_name])
            stats = feature_statistics.get(feature_name, {'mean': 0.0, 'std': 1.0})
            z_score = abs((value - float(stats['mean'])) / max(float(stats['std']), 1e-9))
            contribution = z_score * importance
            top_candidates.append(
                {
                    'feature': feature_name,
                    'value': value,
                    'contribution': contribution,
                }
            )

        top_candidates.sort(key=lambda item: float(item['contribution']), reverse=True)
        return top_candidates[:3]

    def decimal_confidence(self, value: float) -> Decimal:
        """Convert floating confidence to decimal suitable for persistence."""
        return Decimal(str(round(value, 6)))
