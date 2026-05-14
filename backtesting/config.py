"""Configuration models for the quantitative feature research framework."""

from __future__ import annotations

from pathlib import Path
import json
from typing import Any

from pydantic import BaseModel, Field


class FeatureToggleConfig(BaseModel):
    """Enable or disable feature families."""

    candle: bool = True
    trend: bool = True
    volatility: bool = True
    volume: bool = True
    relative_strength: bool = True
    structure: bool = True
    market_regime: bool = True
    multi_timeframe: bool = True


class WindowConfig(BaseModel):
    """Rolling windows for feature computation."""

    short: int = 10
    medium: int = 20
    long: int = 50
    very_long: int = 200
    yearly: int = 252


class FeatureThresholdConfig(BaseModel):
    """Thresholds used by feature and target logic."""

    expansion_range_multiplier: float = 1.5
    contraction_range_multiplier: float = 0.7
    atr_compression_threshold: float = 0.8
    atr_expansion_threshold: float = 1.2
    relative_volume_spike_threshold: float = 2.0
    volatility_expansion_threshold: float = 1.4


class FutureReturnTargetConfig(BaseModel):
    """Future expansion target definition."""

    threshold_pct: float
    lookahead_days: int


class BreakoutTargetConfig(BaseModel):
    """Breakout target definition."""

    lookahead_days: int = 20
    yearly_high_window: int = 252
    expansion_threshold: float = 1.25


class VolatilityTargetConfig(BaseModel):
    """Volatility expansion target definition."""

    lookahead_days: int = 20
    realized_vol_window: int = 20
    expansion_threshold: float = 1.4


class MomentumTargetConfig(BaseModel):
    """Momentum continuation target definition."""

    lookahead_days: int = 20
    min_return_pct: float = 5.0
    max_drawdown_pct: float = -3.0


class TargetConfig(BaseModel):
    """Target-generation configuration."""

    future_return_targets: list[FutureReturnTargetConfig] = Field(
        default_factory=lambda: [
            FutureReturnTargetConfig(threshold_pct=10.0, lookahead_days=20),
            FutureReturnTargetConfig(threshold_pct=15.0, lookahead_days=30),
            FutureReturnTargetConfig(threshold_pct=25.0, lookahead_days=60),
        ]
    )
    breakout_target: BreakoutTargetConfig = Field(default_factory=BreakoutTargetConfig)
    volatility_target: VolatilityTargetConfig = Field(default_factory=VolatilityTargetConfig)
    momentum_target: MomentumTargetConfig = Field(default_factory=MomentumTargetConfig)


class DatasetConfig(BaseModel):
    """Dataset assembly and export settings."""

    start_date: str | None = None
    end_date: str | None = None
    daily_timeframe: str = '1DAY'
    weekly_timeframe: str = '1WEEK'
    monthly_timeframe: str = '1MONTH'
    min_history_rows: int = 260
    dropna_feature_threshold: float = 0.5
    output_dir: str = './artifacts/analysis'
    output_prefix: str = 'quant_feature_dataset'
    export_csv: bool = True
    export_parquet: bool = True


class RegimeConfig(BaseModel):
    """Market regime detection configuration."""

    volatility_window: int = 20
    trend_window: int = 50
    breadth_window: int = 20
    panic_vol_zscore: float = 1.2
    choppy_trend_abs_threshold: float = 0.015
    expansion_momentum_threshold: float = 0.05
    clustering_enabled: bool = False
    clustering_regimes: int = 4


class ModelConfig(BaseModel):
    """Model-training configuration."""

    model_types: list[str] = Field(default_factory=lambda: ['xgb', 'lgb', 'rf'])
    target_column: str = 'target_up_10pct_within_20d'
    walk_forward_train_days: int = 365
    walk_forward_test_days: int = 90
    walk_forward_step_days: int = 90
    min_train_rows: int = 1000
    min_test_rows: int = 100
    probability_threshold: float = 0.55
    random_state: int = 42
    xgb_params: dict[str, Any] = Field(
        default_factory=lambda: {
            'n_estimators': 500,
            'max_depth': 6,
            'learning_rate': 0.05,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'eval_metric': 'logloss',
            'n_jobs': 1,
        }
    )
    lgb_params: dict[str, Any] = Field(
        default_factory=lambda: {
            'n_estimators': 500,
            'max_depth': 6,
            'learning_rate': 0.05,
            'num_leaves': 63,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'n_jobs': 1,
            'verbose': -1,
        }
    )
    rf_params: dict[str, Any] = Field(
        default_factory=lambda: {
            'n_estimators': 500,
            'max_depth': 10,
            'min_samples_leaf': 10,
            'class_weight': 'balanced_subsample',
            'n_jobs': 1,
        }
    )


class QuantResearchConfig(BaseModel):
    """Top-level quantitative research configuration."""

    benchmark_ticker: str = 'NIFTY 50'
    benchmark_universe_tickers: list[str] = Field(default_factory=list)
    feature_toggles: FeatureToggleConfig = Field(default_factory=FeatureToggleConfig)
    windows: WindowConfig = Field(default_factory=WindowConfig)
    thresholds: FeatureThresholdConfig = Field(default_factory=FeatureThresholdConfig)
    targets: TargetConfig = Field(default_factory=TargetConfig)
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    regime: RegimeConfig = Field(default_factory=RegimeConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)


def load_research_config(config_path: str | Path) -> QuantResearchConfig:
    """Load YAML or JSON configuration into a validated config model."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f'Config file not found: {path}')

    if path.suffix.lower() in {'.yaml', '.yml'}:
        import yaml

        raw = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    elif path.suffix.lower() == '.json':
        raw = json.loads(path.read_text(encoding='utf-8'))
    else:
        raise ValueError('Unsupported config format. Use .yaml, .yml, or .json')

    return QuantResearchConfig.model_validate(raw)
