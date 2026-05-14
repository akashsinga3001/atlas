"""Regime-wise feature utility and target behavior analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.feature_selection import mutual_info_classif

from utils.logger import logger


@dataclass
class RegimeAnalysisResult:
    """Container for per-regime analytics outputs."""

    regime_summary: pd.DataFrame
    regime_feature_rankings: dict[str, pd.DataFrame]
    output_files: dict[str, str]


class RegimeAnalyzer:
    """Compute target and feature diagnostics by market regime."""

    def analyze(
        self,
        dataset: pd.DataFrame,
        target_column: str,
        output_dir: str,
        regime_column: str = 'market_regime',
    ) -> RegimeAnalysisResult:
        """Analyze target behavior and feature relevance by regime."""
        if regime_column not in dataset.columns:
            raise ValueError(f'Regime column not found: {regime_column}')
        if target_column not in dataset.columns:
            raise ValueError(f'Target column not found: {target_column}')

        frame = dataset.dropna(subset=[regime_column, target_column]).copy()
        frame[target_column] = frame[target_column].astype(int)

        regime_summary = (
            frame.groupby(regime_column)[target_column]
            .agg(['count', 'mean'])
            .rename(columns={'count': 'rows', 'mean': 'positive_rate'})
            .reset_index()
            .sort_values('rows', ascending=False)
            .reset_index(drop=True)
        )

        feature_columns = [
            column
            for column in frame.columns
            if column not in {'timestamp', 'candle_date', 'security_id', 'ticker', 'sector', regime_column}
            and not column.startswith('target_')
            and pd.api.types.is_numeric_dtype(frame[column])
        ]

        regime_feature_rankings: dict[str, pd.DataFrame] = {}
        for regime_name, group in frame.groupby(regime_column):
            if len(group) < 200 or group[target_column].nunique() < 2:
                continue
            x = group[feature_columns].fillna(group[feature_columns].median())
            y = group[target_column]

            corr = x.corrwith(y).abs().rename('correlation_abs')
            mi = pd.Series(mutual_info_classif(x, y, random_state=42), index=feature_columns, name='mutual_information')
            ranking = pd.concat([corr, mi], axis=1).fillna(0.0)

            max_corr = float(ranking['correlation_abs'].max())
            max_mi = float(ranking['mutual_information'].max())
            if max_corr > 0:
                ranking['correlation_abs'] = ranking['correlation_abs'] / max_corr
            if max_mi > 0:
                ranking['mutual_information'] = ranking['mutual_information'] / max_mi

            ranking['combined_score'] = (ranking['correlation_abs'] * 0.5) + (ranking['mutual_information'] * 0.5)
            ranking = ranking.sort_values('combined_score', ascending=False).reset_index().rename(columns={'index': 'feature'})
            regime_feature_rankings[str(regime_name)] = ranking

        files = self._persist(output_dir, regime_summary, regime_feature_rankings, target_column)
        logger.info('Regime analysis complete regimes={} files={}', len(regime_feature_rankings), files)

        return RegimeAnalysisResult(
            regime_summary=regime_summary,
            regime_feature_rankings=regime_feature_rankings,
            output_files=files,
        )

    def _persist(
        self,
        output_dir: str,
        regime_summary: pd.DataFrame,
        regime_rankings: dict[str, pd.DataFrame],
        target_column: str,
    ) -> dict[str, str]:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        files: dict[str, str] = {}
        summary_path = output_path / f'regime_summary_{target_column}.csv'
        regime_summary.to_csv(summary_path, index=False)
        files['regime_summary'] = str(summary_path)

        for regime_name, ranking in regime_rankings.items():
            safe_name = regime_name.replace(' ', '_').lower()
            ranking_path = output_path / f'regime_feature_ranking_{safe_name}_{target_column}.csv'
            ranking.to_csv(ranking_path, index=False)
            files[f'regime_{safe_name}'] = str(ranking_path)

        return files
