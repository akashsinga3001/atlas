"""Feature contribution analysis service for stock movement prediction."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
import base64
from typing import Any

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import pointbiserialr, spearmanr
from sklearn.feature_selection import mutual_info_classif
from sqlalchemy import and_, create_engine, select
from sqlalchemy.orm import sessionmaker

from config import settings
from models.feature import Feature
from models.ohlcv import Ohlcv
from models.security import Security
from utils.logger import logger


@dataclass
class FeatureImportanceResult:
    """Result container for feature importance analysis."""

    feature_name: str
    correlation: float
    mutual_information: float
    spearman_rho: float
    point_biserial: float
    combined_importance: float
    missing_rate_pct: float
    long_mean: float
    short_mean: float
    neutral_mean: float


@dataclass
class AnalysisResult:
    """Container for complete feature analysis output."""

    total_rows: int
    rows_retained: int
    retention_rate_pct: float = 0.0
    long_count: int = 0
    short_count: int = 0
    neutral_count: int = 0
    feature_importance: list[FeatureImportanceResult] = field(default_factory=list)
    correlation_matrix: pd.DataFrame = None
    missing_data: dict[str, float] = field(default_factory=dict)
    feature_statistics: dict[str, dict[str, float]] = field(default_factory=dict)
    by_stock: dict[int, dict[str, Any]] = field(default_factory=dict)


class FeatureAnalysisService:
    """Analyze feature contribution to stock price movement prediction."""

    FEATURE_COLUMNS = [
        'body_size_pct', 'upper_wick_pct', 'lower_wick_pct', 'range_pct', 'close_position_pct',
        'volatility_10d', 'volatility_20d', 'volatility_ratio_10_20',
        'close_vs_sma10_pct', 'close_vs_sma20_pct', 'close_vs_sma50_pct',
        'sma10_slope', 'sma20_slope', 'sma50_slope', 'uptrend_alignment',
        'volume_zscore_20d', 'volume_ratio_5_20',
        'roc_5d', 'roc_10d', 'roc_20d', 'rsi_14', 'stochastic_k_14',
        'dist_from_20d_high_pct', 'dist_from_20d_low_pct',
        'dist_from_52w_high_pct', 'dist_from_52w_low_pct'
    ]

    def __init__(self) -> None:
        self._engine = create_engine(settings.DATABASE_URL, echo=settings.DB_ECHO, future=True)
        self._session_factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, future=True)

    def analyze(
        self,
        timeframe: str = '1DAY',
        horizon_days: int = 20,
        threshold_pct: float = 5.0,
        train_start_date: date | None = None,
        train_end_date: date | None = None,
        include_stock_level: bool = False,
    ) -> AnalysisResult:
        """Perform comprehensive feature analysis for stock movement prediction.
        
        Args:
            timeframe: OHLCV timeframe ('1DAY', '1WEEK', '1MONTH')
            horizon_days: Forward-looking window for label computation
            threshold_pct: Minimum % move to classify as long/short
            train_start_date: Optional lower-bound on prediction_date (inclusive)
            train_end_date: Optional upper-bound on prediction_date (inclusive)
            include_stock_level: If True, include per-stock breakdown
            
        Returns:
            AnalysisResult with feature importance rankings and statistics
        """
        logger.info(
            'Feature analysis started timeframe={} horizon_days={} threshold_pct={} '
            'train_start_date={} train_end_date={} stock_level={}',
            timeframe, horizon_days, threshold_pct, train_start_date, train_end_date, include_stock_level
        )

        # Build dataset
        df, feature_cols = self._build_dataset(
            timeframe, horizon_days, threshold_pct, train_start_date, train_end_date
        )

        result = AnalysisResult(
            total_rows=df.shape[0],
            rows_retained=df.dropna(subset=feature_cols).shape[0],
        )
        result.retention_rate_pct = (result.rows_retained / result.total_rows * 100) if result.total_rows > 0 else 0

        # Compute label distribution
        label_counts = df['label'].value_counts()
        result.long_count = int(label_counts.get(1, 0))
        result.short_count = int(label_counts.get(-1, 0))
        result.neutral_count = int(label_counts.get(0, 0))

        logger.info(
            'Dataset built total_rows={} retained={} retention_rate={}% labels: long={} short={} neutral={}',
            result.total_rows, result.rows_retained, round(result.retention_rate_pct, 2),
            result.long_count, result.short_count, result.neutral_count
        )

        # Convert all columns to float and handle NaN
        for col in feature_cols:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except Exception:
                df[col] = np.nan

        # Drop rows with missing feature values
        df_clean = df.dropna(subset=feature_cols).copy()
        # Also drop rows with NaN labels
        df_clean = df_clean[df_clean['label'].notna()].copy()

        if df_clean.shape[0] == 0:
            logger.warning('No complete feature rows after dropping NaN values')
            return result

        # Compute feature importance
        result.feature_importance = self._compute_feature_importance(
            df_clean, feature_cols
        )

        # Compute statistics
        result.correlation_matrix = df_clean[feature_cols + ['label']].corr()
        result.missing_data = {col: (df[col].isna().sum() / len(df) * 100) for col in feature_cols}
        result.feature_statistics = self._compute_statistics(df_clean, feature_cols)

        # Per-stock analysis if requested
        if include_stock_level:
            result.by_stock = self._analyze_by_stock(df_clean, feature_cols)

        logger.info(
            'Feature analysis completed importance_rankings={} features with non-zero importance',
            len([f for f in result.feature_importance if f.combined_importance > 0.01])
        )

        return result

    def _build_dataset(
        self,
        timeframe: str,
        horizon_days: int,
        threshold_pct: float,
        train_start_date: date | None,
        train_end_date: date | None,
    ) -> tuple[pd.DataFrame, list[str]]:
        """Load features and labels from database, return DataFrame with label column.
        
        Returns:
            Tuple of (DataFrame with all columns + 'label', list of feature column names)
        """
        with self._session_factory() as session:
            # Load all OHLCV records for the timeframe
            query = select(
                Ohlcv.id,
                Ohlcv.security_id,
                Ohlcv.candle_date,
                Ohlcv.close,
                Feature.id.label('feature_id'),
                *[getattr(Feature, col) for col in self.FEATURE_COLUMNS]
            ).join(Feature, Ohlcv.id == Feature.ohlcv_id).where(
                Ohlcv.timeframe == timeframe
            ).order_by(Ohlcv.security_id, Ohlcv.candle_date)

            rows = list(session.execute(query).all())

        # Convert to DataFrame
        columns = ['ohlcv_id', 'security_id', 'candle_date', 'close', 'feature_id'] + self.FEATURE_COLUMNS
        df = pd.DataFrame(rows, columns=columns)

        if len(df) == 0:
            logger.warning('No OHLCV/Feature records found for timeframe={}', timeframe)
            return pd.DataFrame(), self.FEATURE_COLUMNS

        logger.info('Loaded records={} for timeframe={}', len(df), timeframe)

        # Compute labels: forward returns over horizon_days efficiently
        threshold = float(threshold_pct) / 100.0
        df_sorted = df.sort_values(['security_id', 'candle_date']).reset_index(drop=True)
        df_sorted['candle_date'] = pd.to_datetime(df_sorted['candle_date'])
        
        def compute_labels_for_security(group):
            """Compute labels for a single security using searchsorted."""
            group = group.reset_index(drop=True)
            labels = np.full(len(group), np.nan)
            
            dates_array = group['candle_date'].values
            
            for idx in range(len(group)):
                target_date = dates_array[idx] + np.timedelta64(horizon_days, 'D')
                
                # Find first future row with date >= target
                pos = np.searchsorted(dates_array[idx+1:], target_date, side='left')
                future_idx = idx + 1 + pos
                
                if future_idx < len(group):
                    future_close = float(group['close'].iloc[future_idx])
                    current_close = float(group['close'].iloc[idx])
                    future_return = (future_close - current_close) / current_close
                    
                    if future_return >= threshold:
                        labels[idx] = 1
                    elif future_return <= -threshold:
                        labels[idx] = -1
                    else:
                        labels[idx] = 0
            
            return pd.Series(labels, index=group.index)
        
        # Apply label computation per security
        labels_series = df_sorted.groupby('security_id', sort=False).apply(
            compute_labels_for_security, include_groups=False
        ).reset_index(drop=True)
        
        df['label'] = labels_series

        # Filter by date range if provided
        if train_start_date is not None:
            df = df[df['candle_date'] >= train_start_date]
        if train_end_date is not None:
            df = df[df['candle_date'] <= train_end_date]

        return df, self.FEATURE_COLUMNS

    def _compute_feature_importance(
        self,
        df: pd.DataFrame,
        feature_cols: list[str],
    ) -> list[FeatureImportanceResult]:
        """Compute feature importance via multiple methods and combine scores.
        
        Args:
            df: DataFrame with features and 'label' column
            feature_cols: List of feature column names
            
        Returns:
            Sorted list of FeatureImportanceResult objects
        """
        X = df[feature_cols].values.astype(np.float64)
        y = df['label'].values.astype(np.float64)
        
        logger.info('Feature matrix shape: {} Label distribution: {} unique values', X.shape, np.unique(y))

        # Method 1: Correlation with label
        correlations = {}
        for i, col in enumerate(feature_cols):
            try:
                corr, _ = pointbiserialr(y, X[:, i])
                correlations[col] = abs(corr) if not np.isnan(corr) else 0.0
            except Exception:
                correlations[col] = 0.0

        # Method 2: Mutual Information
        try:
            mi_scores = mutual_info_classif(X, y, random_state=42)
            mi_dict = {col: float(score) for col, score in zip(feature_cols, mi_scores)}
        except Exception:
            logger.warning('Mutual information computation failed, using zeros')
            mi_dict = {col: 0.0 for col in feature_cols}

        # Method 3: Spearman rank correlation
        spearman_scores = {}
        for i, col in enumerate(feature_cols):
            try:
                rho, _ = spearmanr(X[:, i], y)
                spearman_scores[col] = abs(rho) if not np.isnan(rho) else 0.0
            except Exception:
                spearman_scores[col] = 0.0

        # Normalize scores to [0, 1]
        corr_max = max(correlations.values()) if correlations.values() else 1.0
        mi_max = max(mi_dict.values()) if mi_dict.values() else 1.0
        spear_max = max(spearman_scores.values()) if spearman_scores.values() else 1.0

        correlations = {k: v / corr_max if corr_max > 0 else 0 for k, v in correlations.items()}
        mi_dict = {k: v / mi_max if mi_max > 0 else 0 for k, v in mi_dict.items()}
        spearman_scores = {k: v / spear_max if spear_max > 0 else 0 for k, v in spearman_scores.items()}

        # Compute per-class statistics
        class_stats = {}
        for col in feature_cols:
            col_data = df[col]
            class_stats[col] = {
                'long_mean': float(df[df['label'] == 1][col].mean()) if (df['label'] == 1).any() else np.nan,
                'short_mean': float(df[df['label'] == -1][col].mean()) if (df['label'] == -1).any() else np.nan,
                'neutral_mean': float(df[df['label'] == 0][col].mean()) if (df['label'] == 0).any() else np.nan,
                'missing_rate': float(df[col].isna().sum() / len(df) * 100),
            }

        # Combine importance: correlation (40%), MI (40%), Spearman (20%)
        results = []
        for col in feature_cols:
            combined = (
                correlations[col] * 0.4 +
                mi_dict[col] * 0.4 +
                spearman_scores[col] * 0.2
            )

            results.append(FeatureImportanceResult(
                feature_name=col,
                correlation=float(correlations[col]),
                mutual_information=float(mi_dict[col]),
                spearman_rho=float(spearman_scores[col]),
                point_biserial=float(correlations[col]),  # Same as correlation for binary/continuous
                combined_importance=float(combined),
                missing_rate_pct=class_stats[col]['missing_rate'],
                long_mean=class_stats[col]['long_mean'],
                short_mean=class_stats[col]['short_mean'],
                neutral_mean=class_stats[col]['neutral_mean'],
            ))

        # Sort by combined importance
        results.sort(key=lambda x: x.combined_importance, reverse=True)
        return results

    def _compute_statistics(
        self,
        df: pd.DataFrame,
        feature_cols: list[str],
    ) -> dict[str, dict[str, float]]:
        """Compute descriptive statistics for each feature.
        
        Returns:
            Dict mapping feature name to stats (mean, std, min, max, q25, q50, q75)
        """
        stats = {}
        for col in feature_cols:
            col_data = df[col].dropna()
            if len(col_data) > 0:
                stats[col] = {
                    'mean': float(col_data.mean()),
                    'std': float(col_data.std()),
                    'min': float(col_data.min()),
                    'max': float(col_data.max()),
                    'q25': float(col_data.quantile(0.25)),
                    'q50': float(col_data.quantile(0.50)),
                    'q75': float(col_data.quantile(0.75)),
                }
            else:
                stats[col] = {}
        return stats

    def _analyze_by_stock(
        self,
        df: pd.DataFrame,
        feature_cols: list[str],
    ) -> dict[int, dict[str, Any]]:
        """Perform per-stock feature importance analysis.
        
        Returns:
            Dict mapping security_id to analysis results
        """
        by_stock = {}
        for security_id in df['security_id'].unique():
            df_stock = df[df['security_id'] == security_id]
            if len(df_stock) < 50:  # Skip stocks with too few records
                continue

            try:
                importance = self._compute_feature_importance(df_stock, feature_cols)
                top_5 = [{'feature': f.feature_name, 'importance': f.combined_importance} for f in importance[:5]]
                by_stock[security_id] = {
                    'rows': len(df_stock),
                    'top_features': top_5
                }
            except Exception as e:
                logger.warning('Per-stock analysis failed for security_id={}: {}', security_id, str(e))

        return by_stock

    def generate_html_report(self, result: AnalysisResult, timeframe: str, threshold_pct: float) -> str:
        """Generate comprehensive HTML report with charts and tables.
        
        Args:
            result: AnalysisResult from analyze() method
            timeframe: OHLCV timeframe used
            threshold_pct: Threshold percentage used for label generation
            
        Returns:
            HTML string ready for file output
        """
        # Generate chart images
        importance_chart = self._chart_feature_importance(result.feature_importance)
        distribution_chart = self._chart_feature_distributions(result.feature_importance)
        missing_chart = self._chart_missing_data(result.missing_data)

        # Build feature importance table
        top_features_html = self._table_top_features(result.feature_importance[:15])
        bottom_features_html = self._table_top_features(result.feature_importance[-5:], reverse=True)

        # Build statistics table
        stats_html = self._table_feature_statistics(result.feature_importance)

        # Build missing data table
        missing_html = self._table_missing_data(result.missing_data)

        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'>
  <title>Feature Contribution Analysis Report</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      background: #f5f7fa;
      color: #2d3748;
      margin: 0;
      padding: 20px;
    }}
    .container {{
      max-width: 1400px;
      margin: 0 auto;
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      overflow: hidden;
    }}
    .header {{
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 30px;
    }}
    .header h1 {{
      margin: 0 0 10px;
      font-size: 32px;
    }}
    .header p {{
      margin: 5px 0;
      font-size: 14px;
      opacity: 0.9;
    }}
    .section {{
      padding: 30px;
      border-bottom: 1px solid #e2e8f0;
    }}
    .section:last-child {{
      border-bottom: none;
    }}
    .section h2 {{
      margin: 0 0 20px;
      font-size: 24px;
      color: #1a202c;
      border-bottom: 3px solid #667eea;
      padding-bottom: 10px;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 20px;
      margin-bottom: 30px;
    }}
    .metric-card {{
      background: #f7fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 20px;
      text-align: center;
    }}
    .metric-card .label {{
      font-size: 12px;
      color: #718096;
      text-transform: uppercase;
      margin-bottom: 8px;
    }}
    .metric-card .value {{
      font-size: 28px;
      font-weight: bold;
      color: #667eea;
    }}
    .chart {{
      margin: 30px 0;
      text-align: center;
    }}
    .chart img {{
      max-width: 100%;
      height: auto;
      border-radius: 6px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 20px 0;
    }}
    table thead {{
      background: #f7fafc;
      border-bottom: 2px solid #e2e8f0;
    }}
    table th {{
      padding: 12px;
      text-align: left;
      font-weight: 600;
      font-size: 13px;
      text-transform: uppercase;
      color: #4a5568;
    }}
    table td {{
      padding: 12px;
      border-bottom: 1px solid #e2e8f0;
    }}
    table tr:hover {{
      background: #f7fafc;
    }}
    .rank {{
      display: inline-block;
      background: #667eea;
      color: white;
      width: 30px;
      height: 30px;
      border-radius: 50%;
      line-height: 30px;
      text-align: center;
      font-size: 12px;
      font-weight: bold;
    }}
    .bar {{
      display: inline-block;
      background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
      height: 20px;
      border-radius: 3px;
      min-width: 20px;
    }}
    .score-high {{
      color: #22863a;
      font-weight: 600;
    }}
    .score-medium {{
      color: #b08500;
      font-weight: 500;
    }}
    .score-low {{
      color: #6f42c1;
    }}
    .warning {{
      background: #fff8e1;
      border-left: 4px solid #ffc107;
      padding: 15px;
      margin: 20px 0;
      border-radius: 4px;
      font-size: 14px;
    }}
    .footer {{
      background: #f7fafc;
      padding: 20px 30px;
      font-size: 12px;
      color: #718096;
      text-align: center;
    }}
  </style>
</head>
<body>
  <div class='container'>
    <div class='header'>
      <h1>Feature Contribution Analysis</h1>
      <p>Comprehensive analysis of feature importance for stock movement prediction</p>
      <p>Timeframe: {timeframe} | Move Threshold: {threshold_pct}%</p>
    </div>

    <div class='section'>
      <h2>Dataset Summary</h2>
      <div class='metrics'>
        <div class='metric-card'>
          <div class='label'>Total Records</div>
          <div class='value'>{result.total_rows:,}</div>
        </div>
        <div class='metric-card'>
          <div class='label'>Records with Complete Features</div>
          <div class='value'>{result.rows_retained:,}</div>
        </div>
        <div class='metric-card'>
          <div class='label'>Retention Rate</div>
          <div class='value'>{result.retention_rate_pct:.1f}%</div>
        </div>
        <div class='metric-card'>
          <div class='label'>Long Moves</div>
          <div class='value' style='color: #22863a;'>{result.long_count:,}</div>
        </div>
        <div class='metric-card'>
          <div class='label'>Short Moves</div>
          <div class='value' style='color: #cb2431;'>{result.short_count:,}</div>
        </div>
        <div class='metric-card'>
          <div class='label'>Neutral</div>
          <div class='value'>{result.neutral_count:,}</div>
        </div>
      </div>
    </div>

    <div class='section'>
      <h2>Feature Importance Ranking</h2>
      <div class='chart'>
        <img src='data:image/png;base64,{importance_chart}' alt='Feature Importance Chart'>
      </div>
      {top_features_html}
    </div>

    <div class='section'>
      <h2>Feature Distributions by Label</h2>
      <div class='chart'>
        <img src='data:image/png;base64,{distribution_chart}' alt='Feature Distributions'>
      </div>
    </div>

    <div class='section'>
      <h2>Missing Data Analysis</h2>
      <div class='chart'>
        <img src='data:image/png;base64,{missing_chart}' alt='Missing Data Chart'>
      </div>
      {missing_html}
    </div>

    <div class='section'>
      <h2>Detailed Feature Statistics</h2>
      {stats_html}
    </div>

    <div class='section'>
      <h2>Bottom Features (Lowest Importance)</h2>
      {bottom_features_html}
    </div>

    <div class='section'>
      <h2>Key Insights & Recommendations</h2>
      <div style='background: #f0f4ff; padding: 20px; border-radius: 6px; margin: 20px 0;'>
        <h3 style='margin-top: 0;'>Top Contributing Features</h3>
        <ul>
          {self._recommendations_top_features(result.feature_importance)}
        </ul>
      </div>
      <div style='background: #fff0f5; padding: 20px; border-radius: 6px; margin: 20px 0;'>
        <h3 style='margin-top: 0;'>Features with High Missing Data</h3>
        {self._recommendations_missing_data(result.missing_data)}
      </div>
      <div style='background: #f0fff4; padding: 20px; border-radius: 6px;'>
        <h3 style='margin-top: 0;'>Analysis Notes</h3>
        <ul>
          <li>Importance scores combine: Correlation (40%), Mutual Information (40%), Spearman Rank (20%)</li>
          <li>Only records with complete feature values are included in ranking calculation</li>
          <li>Class means show average feature values for each prediction direction</li>
          <li>Missing rate represents % of records with NaN values</li>
        </ul>
      </div>
    </div>

    <div class='footer'>
      Generated on {date.today().isoformat()} | Feature Contribution Analysis v1.0
    </div>
  </div>
</body>
</html>"""

        return html

    def _chart_feature_importance(self, importance: list[FeatureImportanceResult]) -> str:
        """Generate and return base64-encoded feature importance chart."""
        fig, ax = plt.subplots(figsize=(12, 8))

        top_n = min(20, len(importance))
        top_features = importance[:top_n]

        names = [f.feature_name for f in top_features]
        scores = [f.combined_importance for f in top_features]

        colors = plt.cm.viridis(np.linspace(0, 1, top_n))
        ax.barh(range(top_n), scores, color=colors)

        ax.set_yticks(range(top_n))
        ax.set_yticklabels(names)
        ax.set_xlabel('Combined Importance Score', fontsize=12, fontweight='bold')
        ax.set_title('Top Features Contributing to Stock Movement', fontsize=14, fontweight='bold', pad=20)
        ax.invert_yaxis()
        ax.grid(axis='x', alpha=0.3, linestyle='--')

        plt.tight_layout()
        return self._fig_to_base64(fig)

    def _chart_feature_distributions(self, importance: list[FeatureImportanceResult]) -> str:
        """Generate and return base64-encoded feature distributions chart."""
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        axes = axes.flatten()

        top_6 = importance[:6]

        for idx, feature in enumerate(top_6):
            ax = axes[idx]

            means = [
                feature.long_mean if not np.isnan(feature.long_mean) else 0,
                feature.neutral_mean if not np.isnan(feature.neutral_mean) else 0,
                feature.short_mean if not np.isnan(feature.short_mean) else 0,
            ]
            labels = ['Long', 'Neutral', 'Short']
            colors = ['#22863a', '#6f42c1', '#cb2431']

            ax.bar(labels, means, color=colors, alpha=0.7, edgecolor='black', linewidth=1.2)
            ax.set_ylabel('Mean Value', fontsize=10)
            ax.set_title(f'{feature.feature_name}\n(Importance: {feature.combined_importance:.3f})', 
                        fontsize=11, fontweight='bold')
            ax.grid(axis='y', alpha=0.3, linestyle='--')

        plt.suptitle('Distribution of Top Features by Prediction Direction', fontsize=14, fontweight='bold', y=1.00)
        plt.tight_layout()
        return self._fig_to_base64(fig)

    def _chart_missing_data(self, missing_data: dict[str, float]) -> str:
        """Generate and return base64-encoded missing data chart."""
        fig, ax = plt.subplots(figsize=(12, 6))

        sorted_missing = sorted(missing_data.items(), key=lambda x: x[1], reverse=True)[:15]
        names = [name for name, _ in sorted_missing]
        rates = [rate for _, rate in sorted_missing]

        colors = ['#cb2431' if rate > 20 else '#ffc107' if rate > 5 else '#28a745' for rate in rates]
        ax.barh(range(len(names)), rates, color=colors)

        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names)
        ax.set_xlabel('Missing Data Rate (%)', fontsize=12, fontweight='bold')
        ax.set_title('Feature Completeness (Top 15 Most Missing)', fontsize=14, fontweight='bold', pad=20)
        ax.invert_yaxis()
        ax.grid(axis='x', alpha=0.3, linestyle='--')

        plt.tight_layout()
        return self._fig_to_base64(fig)

    def _table_top_features(self, features: list[FeatureImportanceResult], reverse: bool = False) -> str:
        """Generate HTML table of top/bottom features."""
        rows_html = []
        features_to_show = reversed(features) if reverse else features

        for idx, feature in enumerate(features_to_show, 1):
            rank_class = 'rank'
            score_class = 'score-high' if feature.combined_importance > 0.6 else 'score-medium' if feature.combined_importance > 0.3 else 'score-low'

            rows_html.append(f"""
            <tr>
              <td><span class='{rank_class}'>{idx}</span></td>
              <td><strong>{feature.feature_name}</strong></td>
              <td><span class='{score_class}'>{feature.combined_importance:.4f}</span></td>
              <td>{feature.correlation:.4f}</td>
              <td>{feature.mutual_information:.4f}</td>
              <td>{feature.spearman_rho:.4f}</td>
              <td>{feature.missing_rate_pct:.2f}%</td>
            </tr>
            """)

        table_html = f"""
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Feature</th>
              <th>Combined Score</th>
              <th>Correlation</th>
              <th>Mutual Info</th>
              <th>Spearman Rho</th>
              <th>Missing %</th>
            </tr>
          </thead>
          <tbody>
            {"".join(rows_html)}
          </tbody>
        </table>
        """
        return table_html

    def _table_feature_statistics(self, features: list[FeatureImportanceResult]) -> str:
        """Generate HTML table of feature statistics."""
        rows_html = []

        for feature in features[:15]:  # Show top 15
            if not np.isnan(feature.long_mean):
                rows_html.append(f"""
                <tr>
                  <td><strong>{feature.feature_name}</strong></td>
                  <td>{feature.long_mean:.6f}</td>
                  <td>{feature.neutral_mean:.6f}</td>
                  <td>{feature.short_mean:.6f}</td>
                  <td>{feature.missing_rate_pct:.2f}%</td>
                </tr>
                """)

        table_html = f"""
        <table>
          <thead>
            <tr>
              <th>Feature</th>
              <th>Long Mean</th>
              <th>Neutral Mean</th>
              <th>Short Mean</th>
              <th>Missing %</th>
            </tr>
          </thead>
          <tbody>
            {"".join(rows_html)}
          </tbody>
        </table>
        """
        return table_html

    def _table_missing_data(self, missing_data: dict[str, float]) -> str:
        """Generate HTML table of missing data rates."""
        sorted_missing = sorted(missing_data.items(), key=lambda x: x[1], reverse=True)

        rows_html = []
        for feature, rate in sorted_missing:
            if rate > 0:
                status = '🔴 Critical' if rate > 50 else '🟠 High' if rate > 20 else '🟡 Moderate' if rate > 5 else '🟢 Low'
                rows_html.append(f"""
                <tr>
                  <td><strong>{feature}</strong></td>
                  <td>{rate:.2f}%</td>
                  <td>{status}</td>
                </tr>
                """)

        table_html = f"""
        <table>
          <thead>
            <tr>
              <th>Feature</th>
              <th>Missing Rate</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {"".join(rows_html)}
          </tbody>
        </table>
        """
        return table_html

    def _recommendations_top_features(self, features: list[FeatureImportanceResult]) -> str:
        """Generate bullet points for top contributing features."""
        html_items = []
        for idx, feature in enumerate(features[:5], 1):
            html_items.append(f"<li><strong>{feature.feature_name}</strong> - Score: {feature.combined_importance:.4f} (Correlation: {feature.correlation:.4f}, MI: {feature.mutual_information:.4f})</li>")
        return "\n          ".join(html_items)

    def _recommendations_missing_data(self, missing_data: dict[str, float]) -> str:
        """Generate recommendations for missing data."""
        high_missing = {k: v for k, v in missing_data.items() if v > 20}

        if not high_missing:
            return "<ul><li>All features have acceptable missing data rates (&lt;20%)</li></ul>"

        html_items = []
        for feature, rate in sorted(high_missing.items(), key=lambda x: x[1], reverse=True):
            html_items.append(f"<li><strong>{feature}</strong>: {rate:.1f}% missing - Consider filtering or imputation</li>")

        return "<ul>\n        " + "\n        ".join(html_items) + "\n      </ul>"

    def _fig_to_base64(self, fig: plt.Figure) -> str:
        """Convert matplotlib figure to base64-encoded PNG."""
        try:
            buffer = BytesIO()
            fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close(fig)
            return image_base64
        except Exception as e:
            logger.warning('Chart generation failed: {}', str(e))
            plt.close(fig)
            # Return transparent placeholder
            return 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
