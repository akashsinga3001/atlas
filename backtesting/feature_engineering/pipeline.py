"""End-to-end feature engineering and dataset assembly pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import and_, create_engine, select
from sqlalchemy.orm import sessionmaker

from backtesting.config import QuantResearchConfig
from backtesting.feature_engineering.candle_features import generate_candle_features
from backtesting.feature_engineering.market_regime_features import generate_market_regime_features
from backtesting.feature_engineering.multi_timeframe_features import generate_multi_timeframe_features
from backtesting.feature_engineering.relative_strength_features import generate_relative_strength_features
from backtesting.feature_engineering.structure_features import generate_structure_features
from backtesting.feature_engineering.target_generation import TargetGenerator
from backtesting.feature_engineering.trend_features import generate_trend_features
from backtesting.feature_engineering.volatility_features import generate_volatility_features
from backtesting.feature_engineering.volume_features import generate_volume_features
from config import settings
from models.ohlcv import Ohlcv
from models.security import Security
from utils.logger import logger


@dataclass
class DatasetBuildArtifacts:
    """Metadata and export paths for a built research dataset."""

    dataset: pd.DataFrame
    feature_columns: list[str]
    target_columns: list[str]
    exports: dict[str, str]


class FeatureDatasetPipeline:
    """Build leakage-safe training datasets from multi-timeframe OHLCV data."""

    BASE_COLUMNS = {
        'timestamp',
        'candle_date',
        'security_id',
        'ticker',
        'sector',
        'benchmark_close',
        'sector_close',
        'universe_close',
        'open',
        'high',
        'low',
        'close',
        'volume',
        'w_open',
        'w_high',
        'w_low',
        'w_close',
        'w_volume',
        'm_open',
        'm_high',
        'm_low',
        'm_close',
        'm_volume',
    }

    def __init__(self, config: QuantResearchConfig) -> None:
        self._config = config
        self._target_generator = TargetGenerator(config.targets)
        self._engine = create_engine(settings.DATABASE_URL, echo=settings.DB_ECHO, future=True)
        self._session_factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, future=True)

    def build_dataset(self) -> DatasetBuildArtifacts:
        """Build feature+target dataset from 1DAY/1WEEK/1MONTH OHLCV streams."""
        logger.info('Building quantitative feature dataset')

        daily_all = self._load_timeframe(self._config.dataset.daily_timeframe)
        weekly_all = self._load_timeframe(self._config.dataset.weekly_timeframe)
        monthly_all = self._load_timeframe(self._config.dataset.monthly_timeframe)

        daily_eq = daily_all[daily_all['type'] == 'EQ'].copy()
        weekly_eq = weekly_all[weekly_all['type'] == 'EQ'].copy()
        monthly_eq = monthly_all[monthly_all['type'] == 'EQ'].copy()

        frame = self._attach_context(daily_eq, daily_all)
        frame = self._join_timeframes(frame, weekly_eq, monthly_eq)

        if self._config.feature_toggles.candle:
            frame = generate_candle_features(frame, self._config.windows, self._config.thresholds)
        if self._config.feature_toggles.trend:
            frame = generate_trend_features(frame, self._config.windows)
        if self._config.feature_toggles.volatility:
            frame = generate_volatility_features(frame, self._config.windows, self._config.thresholds)
        if self._config.feature_toggles.volume:
            frame = generate_volume_features(frame, self._config.windows)
        if self._config.feature_toggles.relative_strength:
            frame = generate_relative_strength_features(frame, self._config.windows)
        if self._config.feature_toggles.structure:
            frame = generate_structure_features(frame, self._config.windows)
        if self._config.feature_toggles.market_regime:
            frame = generate_market_regime_features(frame, self._config.regime)
        if self._config.feature_toggles.multi_timeframe:
            frame = generate_multi_timeframe_features(frame, self._config.windows)

        frame = self._target_generator.generate(frame)
        frame = self._post_process(frame)

        feature_columns = self._feature_columns(frame)
        target_columns = sorted([column for column in frame.columns if column.startswith('target_')])

        exports = self._export(frame)
        logger.info(
            'Dataset build complete rows={} features={} targets={} exports={}',
            len(frame),
            len(feature_columns),
            len(target_columns),
            exports,
        )

        return DatasetBuildArtifacts(
            dataset=frame,
            feature_columns=feature_columns,
            target_columns=target_columns,
            exports=exports,
        )

    def _load_timeframe(self, timeframe: str) -> pd.DataFrame:
        """Load OHLCV rows with security metadata for a given timeframe."""
        with self._session_factory() as session:
            query = (
                select(
                    Ohlcv.security_id,
                    Ohlcv.candle_date,
                    Ohlcv.open,
                    Ohlcv.high,
                    Ohlcv.low,
                    Ohlcv.close,
                    Ohlcv.volume,
                    Security.ticker,
                    Security.sector,
                    Security.type,
                )
                .join(Security, Security.id == Ohlcv.security_id)
                .where(Security.is_active.is_(True), Ohlcv.timeframe == timeframe)
                .order_by(Ohlcv.security_id.asc(), Ohlcv.candle_date.asc())
            )
            rows = list(session.execute(query).all())

        frame = pd.DataFrame(
            rows,
            columns=['security_id', 'candle_date', 'open', 'high', 'low', 'close', 'volume', 'ticker', 'sector', 'type'],
        )
        if frame.empty:
            raise ValueError(f'No OHLCV rows found for timeframe={timeframe}')

        frame['candle_date'] = pd.to_datetime(frame['candle_date'])
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for column in numeric_columns:
            frame[column] = pd.to_numeric(frame[column], errors='coerce')

        if self._config.dataset.start_date:
            frame = frame[frame['candle_date'] >= pd.Timestamp(self._config.dataset.start_date)]
        if self._config.dataset.end_date:
            frame = frame[frame['candle_date'] <= pd.Timestamp(self._config.dataset.end_date)]

        return frame.reset_index(drop=True)

    def _attach_context(self, daily_eq: pd.DataFrame, daily_all: pd.DataFrame) -> pd.DataFrame:
        """Attach benchmark, sector, and universe context columns."""
        frame = daily_eq.copy()

        benchmark = daily_all[daily_all['ticker'] == self._config.benchmark_ticker][['candle_date', 'close']].copy()
        if benchmark.empty:
            logger.warning('Benchmark ticker {} not found, using market-close mean fallback', self._config.benchmark_ticker)
            benchmark = daily_eq.groupby('candle_date', as_index=False)['close'].mean()

        benchmark = benchmark.rename(columns={'close': 'benchmark_close'})
        frame = frame.merge(benchmark, on='candle_date', how='left', validate='many_to_one')

        sector = daily_eq.groupby(['sector', 'candle_date'], as_index=False)['close'].mean().rename(columns={'close': 'sector_close'})
        frame = frame.merge(sector, on=['sector', 'candle_date'], how='left', validate='many_to_one')

        if self._config.benchmark_universe_tickers:
            universe_base = daily_all[daily_all['ticker'].isin(self._config.benchmark_universe_tickers)]
            universe = universe_base.groupby('candle_date', as_index=False)['close'].mean()
        else:
            universe = daily_eq.groupby('candle_date', as_index=False)['close'].mean()

        universe = universe.rename(columns={'close': 'universe_close'})
        frame = frame.merge(universe, on='candle_date', how='left', validate='many_to_one')
        return frame

    def _join_timeframes(self, daily: pd.DataFrame, weekly: pd.DataFrame, monthly: pd.DataFrame) -> pd.DataFrame:
        """Backward as-of join weekly/monthly series into daily rows by security."""
        frame = self._asof_join_by_security(daily, weekly, 'w_')
        frame = self._asof_join_by_security(frame, monthly, 'm_')
        return frame

    def _asof_join_by_security(self, left: pd.DataFrame, right: pd.DataFrame, prefix: str) -> pd.DataFrame:
        """Perform leakage-safe as-of joins separately per security."""
        right_cols = ['security_id', 'candle_date', 'open', 'high', 'low', 'close', 'volume']
        right_small = right[right_cols].copy()
        right_small = right_small.rename(
            columns={
                'open': f'{prefix}open',
                'high': f'{prefix}high',
                'low': f'{prefix}low',
                'close': f'{prefix}close',
                'volume': f'{prefix}volume',
            }
        )

        joined_frames: list[pd.DataFrame] = []
        for security_id, left_group in left.groupby('security_id'):
            left_group = left_group.sort_values('candle_date')
            right_group = right_small[right_small['security_id'] == security_id].sort_values('candle_date')

            if right_group.empty:
                enriched = left_group.copy()
                enriched[f'{prefix}open'] = np.nan
                enriched[f'{prefix}high'] = np.nan
                enriched[f'{prefix}low'] = np.nan
                enriched[f'{prefix}close'] = np.nan
                enriched[f'{prefix}volume'] = np.nan
                joined_frames.append(enriched)
                continue

            merged = pd.merge_asof(
                left_group,
                right_group.drop(columns=['security_id']),
                on='candle_date',
                direction='backward',
            )
            joined_frames.append(merged)

        return pd.concat(joined_frames, axis=0, ignore_index=True)

    def _post_process(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Apply chronology, missing-data policy, and minimum-history constraints."""
        frame = frame.sort_values(['security_id', 'candle_date']).reset_index(drop=True)
        frame['timestamp'] = frame['candle_date']

        feature_columns = self._feature_columns(frame)
        if feature_columns:
            missing_ratio = frame[feature_columns].isna().mean()
            keep_features = missing_ratio[missing_ratio <= self._config.dataset.dropna_feature_threshold].index.tolist()
            drop_features = sorted(set(feature_columns) - set(keep_features))
            if drop_features:
                logger.info('Dropping {} sparse feature columns', len(drop_features))
                frame = frame.drop(columns=drop_features)

        frame['history_index'] = frame.groupby('security_id').cumcount()
        frame = frame[frame['history_index'] >= self._config.dataset.min_history_rows].copy()
        frame = frame.drop(columns=['history_index', 'type'])

        return frame

    def _feature_columns(self, frame: pd.DataFrame) -> list[str]:
        """Infer engineered feature columns excluding base and target fields."""
        target_columns = {column for column in frame.columns if column.startswith('target_')}
        excluded = self.BASE_COLUMNS.union(target_columns).union({'market_regime'})
        feature_columns = [
            column
            for column in frame.columns
            if column not in excluded and frame[column].dtype != object
        ]
        return sorted(feature_columns)

    def _export(self, frame: pd.DataFrame) -> dict[str, str]:
        """Export dataset to configured output formats."""
        output_dir = Path(self._config.dataset.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        exports: dict[str, str] = {}
        prefix = self._config.dataset.output_prefix

        if self._config.dataset.export_csv:
            csv_path = output_dir / f'{prefix}.csv'
            frame.to_csv(csv_path, index=False)
            exports['csv'] = str(csv_path)

        if self._config.dataset.export_parquet:
            parquet_path = output_dir / f'{prefix}.parquet'
            frame.to_parquet(parquet_path, index=False)
            exports['parquet'] = str(parquet_path)

        return exports
