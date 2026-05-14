"""Feature research toolkit: correlation, MI, model importance, permutation, and SHAP."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import mutual_info_classif
from sklearn.inspection import permutation_importance

from utils.logger import logger


@dataclass
class FeatureResearchResult:
    """Container for ranked feature outputs and summary stats."""

    ranked_features: pd.DataFrame
    target_distribution: pd.DataFrame
    shap_importance: pd.DataFrame
    output_files: dict[str, str]


class FeatureResearchAnalyzer:
    """Run statistical feature utility analysis against a selected target."""

    MAX_ANALYSIS_ROWS = 40000
    MAX_PERMUTATION_ROWS = 6000
    PERMUTATION_REPEATS = 5
    SHAP_MAX_ROWS = 800

    def analyze(
        self,
        dataset: pd.DataFrame,
        target_column: str,
        output_dir: str,
    ) -> FeatureResearchResult:
        """Execute feature research workflow and persist ranked reports."""
        if target_column not in dataset.columns:
            raise ValueError(f'Target column not found: {target_column}')

        frame = dataset.copy()
        frame = frame.sort_values('timestamp').reset_index(drop=True)
        feature_columns = self._feature_columns(frame, target_column)
        if not feature_columns:
            raise ValueError('No numeric feature columns found for analysis')

        clean = frame[feature_columns + [target_column]].replace([np.inf, -np.inf], np.nan)
        clean = clean.dropna(subset=[target_column])
        x = clean[feature_columns].fillna(clean[feature_columns].median())
        y = clean[target_column].astype(int)

        if len(x) > self.MAX_ANALYSIS_ROWS:
            sampled = clean.sample(n=self.MAX_ANALYSIS_ROWS, random_state=42)
            x = sampled[feature_columns].fillna(sampled[feature_columns].median())
            y = sampled[target_column].astype(int)
            logger.info('Downsampled analysis dataset rows={} original_rows={}', len(x), len(clean))

        if y.nunique() < 2:
            raise ValueError(f'Target {target_column} has a single class in current dataset')

        logger.info('Running feature research rows={} features={} target={}', len(x), len(feature_columns), target_column)

        corr = x.corrwith(y).abs().rename('correlation_abs')
        mi = pd.Series(mutual_info_classif(x, y, random_state=42), index=feature_columns, name='mutual_information')

        split_index = int(len(x) * 0.8)
        x_train = x.iloc[:split_index]
        y_train = y.iloc[:split_index]
        x_test = x.iloc[split_index:]
        y_test = y.iloc[split_index:]

        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=10,
            class_weight='balanced_subsample',
            random_state=42,
            n_jobs=1,
        )
        model.fit(x_train, y_train)

        model_importance = pd.Series(model.feature_importances_, index=feature_columns, name='model_importance')
        if len(x_test) > self.MAX_PERMUTATION_ROWS:
            idx = np.random.RandomState(42).choice(len(x_test), size=self.MAX_PERMUTATION_ROWS, replace=False)
            x_test_perm = x_test.iloc[idx]
            y_test_perm = y_test.iloc[idx]
        else:
            x_test_perm = x_test
            y_test_perm = y_test

        perm = permutation_importance(
            model,
            x_test_perm,
            y_test_perm,
            n_repeats=self.PERMUTATION_REPEATS,
            random_state=42,
            n_jobs=1,
        )
        permutation = pd.Series(perm.importances_mean, index=feature_columns, name='permutation_importance')

        shap_importance = self._shap_importance(model, x_test)

        ranked = pd.concat([corr, mi, model_importance, permutation], axis=1).fillna(0.0)
        ranked = self._normalize_columns(ranked)
        ranked['combined_score'] = (
            ranked['correlation_abs'] * 0.25
            + ranked['mutual_information'] * 0.25
            + ranked['model_importance'] * 0.30
            + ranked['permutation_importance'] * 0.20
        )
        ranked = ranked.sort_values('combined_score', ascending=False).reset_index().rename(columns={'index': 'feature'})

        target_distribution = y.value_counts(normalize=True).rename('ratio').reset_index()
        target_distribution.columns = ['target_value', 'ratio']
        target_distribution = target_distribution.sort_values('target_value').reset_index(drop=True)

        outputs = self._persist_outputs(ranked, target_distribution, shap_importance, output_dir, target_column)

        return FeatureResearchResult(
            ranked_features=ranked,
            target_distribution=target_distribution,
            shap_importance=shap_importance,
            output_files=outputs,
        )

    def _feature_columns(self, frame: pd.DataFrame, target_column: str) -> list[str]:
        excluded = {
            'timestamp',
            'candle_date',
            'security_id',
            'ticker',
            'sector',
            'market_regime',
            target_column,
        }
        excluded.update({column for column in frame.columns if column.startswith('target_') and column != target_column})

        return [
            column
            for column in frame.columns
            if (
                column not in excluded
                and not column.startswith('future_return_')
                and pd.api.types.is_numeric_dtype(frame[column])
            )
        ]

    def _normalize_columns(self, frame: pd.DataFrame) -> pd.DataFrame:
        normalized = frame.copy()
        for column in ['correlation_abs', 'mutual_information', 'model_importance', 'permutation_importance']:
            max_value = float(normalized[column].max())
            if max_value > 0:
                normalized[column] = normalized[column] / max_value
        return normalized

    def _shap_importance(self, model: RandomForestClassifier, x_test: pd.DataFrame) -> pd.DataFrame:
        """Compute mean absolute SHAP importance if shap is installed."""
        if os.getenv('QUANT_RESEARCH_SKIP_SHAP', '0') == '1':
            logger.info('Skipping SHAP importance due to QUANT_RESEARCH_SKIP_SHAP=1')
            return pd.DataFrame(columns=['feature', 'shap_importance'])

        try:
            import shap
        except Exception:
            return pd.DataFrame(columns=['feature', 'shap_importance'])

        sample = x_test.iloc[: min(len(x_test), self.SHAP_MAX_ROWS)]
        if sample.empty:
            return pd.DataFrame(columns=['feature', 'shap_importance'])

        explainer = shap.TreeExplainer(model)
        values = explainer.shap_values(sample)
        if isinstance(values, list):
            values = values[-1]

        importance = np.abs(values).mean(axis=0)
        result = pd.DataFrame({'feature': sample.columns, 'shap_importance': importance})
        return result.sort_values('shap_importance', ascending=False).reset_index(drop=True)

    def _persist_outputs(
        self,
        ranked: pd.DataFrame,
        target_distribution: pd.DataFrame,
        shap_importance: pd.DataFrame,
        output_dir: str,
        target_column: str,
    ) -> dict[str, str]:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        files: dict[str, str] = {}
        ranked_path = output_path / f'feature_ranking_{target_column}.csv'
        ranked.to_csv(ranked_path, index=False)
        files['feature_ranking'] = str(ranked_path)

        target_path = output_path / f'target_distribution_{target_column}.csv'
        target_distribution.to_csv(target_path, index=False)
        files['target_distribution'] = str(target_path)

        if not shap_importance.empty:
            shap_path = output_path / f'shap_importance_{target_column}.csv'
            shap_importance.to_csv(shap_path, index=False)
            files['shap_importance'] = str(shap_path)

        return files
