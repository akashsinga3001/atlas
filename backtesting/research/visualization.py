"""Visualization helpers for feature research artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


class ResearchVisualizer:
    """Generate charts for ranked features, target balance, regimes, and walk-forward results."""

    def __init__(self) -> None:
        sns.set_theme(style='whitegrid')

    def plot_feature_importance(self, ranking: pd.DataFrame, output_dir: str, top_n: int = 25) -> str:
        """Plot top-N features by combined score."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        top = ranking.head(top_n).iloc[::-1]
        figure, axis = plt.subplots(figsize=(12, 10))
        axis.barh(top['feature'], top['combined_score'], color='#1f77b4')
        axis.set_title('Feature Importance Ranking')
        axis.set_xlabel('Combined Score')
        axis.set_ylabel('Feature')
        figure.tight_layout()

        file_path = output_path / 'feature_importance_chart.png'
        figure.savefig(file_path, dpi=160)
        plt.close(figure)
        return str(file_path)

    def plot_shap_importance(self, shap_importance: pd.DataFrame, output_dir: str, top_n: int = 25) -> str | None:
        """Plot SHAP importance if SHAP output is available."""
        if shap_importance.empty:
            return None

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        top = shap_importance.head(top_n).iloc[::-1]
        figure, axis = plt.subplots(figsize=(12, 10))
        axis.barh(top['feature'], top['shap_importance'], color='#2ca02c')
        axis.set_title('SHAP Feature Importance')
        axis.set_xlabel('Mean Absolute SHAP Value')
        axis.set_ylabel('Feature')
        figure.tight_layout()

        file_path = output_path / 'shap_importance_chart.png'
        figure.savefig(file_path, dpi=160)
        plt.close(figure)
        return str(file_path)

    def plot_target_distribution(self, target_distribution: pd.DataFrame, output_dir: str) -> str:
        """Plot class ratios for the selected target."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        figure, axis = plt.subplots(figsize=(8, 5))
        axis.bar(target_distribution['target_value'].astype(str), target_distribution['ratio'], color='#ff7f0e')
        axis.set_title('Target Distribution')
        axis.set_xlabel('Target Value')
        axis.set_ylabel('Ratio')
        figure.tight_layout()

        file_path = output_path / 'target_distribution_chart.png'
        figure.savefig(file_path, dpi=160)
        plt.close(figure)
        return str(file_path)

    def plot_regime_distribution(self, dataset: pd.DataFrame, output_dir: str, regime_column: str = 'market_regime') -> str | None:
        """Plot counts per market regime if regime column exists."""
        if regime_column not in dataset.columns:
            return None

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        counts = dataset[regime_column].value_counts()
        figure, axis = plt.subplots(figsize=(9, 5))
        axis.bar(counts.index.astype(str), counts.values, color='#9467bd')
        axis.set_title('Regime Distribution')
        axis.set_xlabel('Regime')
        axis.set_ylabel('Count')
        figure.tight_layout()

        file_path = output_path / 'regime_distribution_chart.png'
        figure.savefig(file_path, dpi=160)
        plt.close(figure)
        return str(file_path)

    def plot_rolling_performance(self, folds: list[dict[str, Any]], output_dir: str) -> str | None:
        """Plot rolling walk-forward precision and profit factor by fold."""
        if not folds:
            return None

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        frame = pd.DataFrame(folds)
        if 'fold_index' not in frame.columns:
            return None

        figure, axis_left = plt.subplots(figsize=(12, 6))
        axis_right = axis_left.twinx()

        axis_left.plot(frame['fold_index'], frame.get('precision', 0.0), marker='o', color='#1f77b4', label='Precision')
        axis_left.plot(frame['fold_index'], frame.get('f1', 0.0), marker='o', color='#17becf', label='F1')
        axis_right.plot(frame['fold_index'], frame.get('profit_factor', 0.0), marker='x', color='#d62728', label='Profit Factor')

        axis_left.set_xlabel('Fold Index')
        axis_left.set_ylabel('Classification Metrics')
        axis_right.set_ylabel('Profit Factor')
        axis_left.set_title('Walk-Forward Rolling Performance')

        lines_left, labels_left = axis_left.get_legend_handles_labels()
        lines_right, labels_right = axis_right.get_legend_handles_labels()
        axis_left.legend(lines_left + lines_right, labels_left + labels_right, loc='best')
        figure.tight_layout()

        file_path = output_path / 'rolling_performance_chart.png'
        figure.savefig(file_path, dpi=160)
        plt.close(figure)
        return str(file_path)
