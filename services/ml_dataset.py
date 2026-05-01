"""Dataset construction for ML training and daily inference."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
import math
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from config import settings
from models.feature import Feature
from models.ohlcv import Ohlcv
from models.security import Security


@dataclass
class DatasetBuildResult:
    """Container for feature rows and metadata returned by dataset builder."""

    records: list[dict[str, Any]]
    feature_keys: list[str]


class MlDatasetService:
    """Build leakage-safe feature rows from 1DAY/1WEEK/1MONTH OHLCV + engineered features."""

    TIMEFRAME_1DAY = '1DAY'
    TIMEFRAME_1WEEK = '1WEEK'
    TIMEFRAME_1MONTH = '1MONTH'

    def __init__(self) -> None:
        self._engine = create_engine(settings.DATABASE_URL, echo=settings.DB_ECHO, future=True)
        self._session_factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, future=True)

    def build_training_dataset(
        self,
        horizon_days: int,
        threshold_pct: float,
        train_start_date: date | None = None,
        train_end_date: date | None = None,
    ) -> DatasetBuildResult:
        """Construct supervised training rows for long/short binary targets.

        Args:
            horizon_days: Number of future days in which the target move must occur.
            threshold_pct: Minimum % move required to label a row as long/short.
            train_start_date: Optional lower-bound on prediction_date (inclusive).
            train_end_date: Optional upper-bound on prediction_date (inclusive).

        Returns:
            DatasetBuildResult containing labeled feature rows and sorted feature keys.
        """
        daily = self._load_rows_by_security(self.TIMEFRAME_1DAY)

        records: list[dict[str, Any]] = []
        feature_keys: set[str] = set()
        threshold = float(threshold_pct) / 100.0

        for security_id, daily_rows in daily.items():
            if len(daily_rows) <= horizon_days:
                continue

            for index in range(len(daily_rows) - horizon_days):
                current = daily_rows[index]
                prediction_date = current['candle_date']

                if train_start_date is not None and prediction_date < train_start_date:
                    continue
                if train_end_date is not None and prediction_date > train_end_date:
                    continue

                weekly_row = self._aggregate_from_daily_rows(daily_rows, index, self.TIMEFRAME_1WEEK)
                monthly_row = self._aggregate_from_daily_rows(daily_rows, index, self.TIMEFRAME_1MONTH)
                if weekly_row is None or monthly_row is None:
                    continue

                label_info = self._resolve_labels(daily_rows, index, horizon_days, threshold)
                if label_info['ambiguous']:
                    continue

                feature_payload = self._combine_features(
                    daily_rows=daily_rows,
                    current_index=index,
                    daily_row=current,
                    weekly_row=weekly_row,
                    monthly_row=monthly_row,
                )

                feature_keys.update(feature_payload.keys())
                records.append(
                    {
                        'prediction_date': prediction_date,
                        'security_id': security_id,
                        'ticker': current['ticker'],
                        'features': feature_payload,
                        'long_label': int(label_info['long_label']),
                        'short_label': int(label_info['short_label']),
                    }
                )

        return DatasetBuildResult(records=records, feature_keys=sorted(feature_keys))

    def build_inference_dataset(self, as_of_date: date | None = None) -> DatasetBuildResult:
        """Construct most-recent inference rows for each active EQ ticker.

        Args:
            as_of_date: If given, use the last available row on or before this date.
                        Defaults to using the absolute latest row per security.

        Returns:
            DatasetBuildResult with one feature row per security.
        """
        daily = self._load_rows_by_security(self.TIMEFRAME_1DAY)

        records: list[dict[str, Any]] = []
        feature_keys: set[str] = set()

        for security_id, daily_rows in daily.items():
            if not daily_rows:
                continue

            if as_of_date is not None:
                current_index = -1
                for i, r in enumerate(daily_rows):
                    if r['candle_date'] <= as_of_date:
                        current_index = i
                if current_index == -1:
                    continue
            else:
                current_index = len(daily_rows) - 1

            current = daily_rows[current_index]
            prediction_date = current['candle_date']

            weekly_row = self._aggregate_from_daily_rows(daily_rows, current_index, self.TIMEFRAME_1WEEK)
            monthly_row = self._aggregate_from_daily_rows(daily_rows, current_index, self.TIMEFRAME_1MONTH)
            if weekly_row is None or monthly_row is None:
                continue

            feature_payload = self._combine_features(
                daily_rows=daily_rows,
                current_index=current_index,
                daily_row=current,
                weekly_row=weekly_row,
                monthly_row=monthly_row,
            )

            feature_keys.update(feature_payload.keys())
            records.append(
                {
                    'prediction_date': prediction_date,
                    'security_id': security_id,
                    'ticker': current['ticker'],
                    'features': feature_payload,
                }
            )

        return DatasetBuildResult(records=records, feature_keys=sorted(feature_keys))

    def _load_rows_by_security(self, timeframe: str) -> dict[int, list[dict[str, Any]]]:
        """Load OHLCV + Feature rows for active EQ securities by timeframe."""
        with self._session_factory() as session:
            query = (
                select(Ohlcv, Feature, Security)
                .join(Security, Security.id == Ohlcv.security_id)
                .outerjoin(Feature, Feature.ohlcv_id == Ohlcv.id)
                .where(Security.is_active.is_(True), Security.type == 'EQ', Ohlcv.timeframe == timeframe)
                .order_by(Ohlcv.security_id.asc(), Ohlcv.candle_date.asc(), Ohlcv.id.asc())
            )
            rows = list(session.execute(query).all())

        payload: dict[int, list[dict[str, Any]]] = {}
        for ohlcv, feature, security in rows:
            payload.setdefault(ohlcv.security_id, []).append(
                {
                    'security_id': ohlcv.security_id,
                    'ticker': security.ticker,
                    'candle_date': ohlcv.candle_date,
                    'open': self._as_float(ohlcv.open),
                    'high': self._as_float(ohlcv.high),
                    'low': self._as_float(ohlcv.low),
                    'close': self._as_float(ohlcv.close),
                    'volume': int(ohlcv.volume),
                    'body_size_pct': self._as_feature_float(feature, 'body_size_pct'),
                    'upper_wick_pct': self._as_feature_float(feature, 'upper_wick_pct'),
                    'lower_wick_pct': self._as_feature_float(feature, 'lower_wick_pct'),
                    'range_pct': self._as_feature_float(feature, 'range_pct'),
                    'close_position_pct': self._as_feature_float(feature, 'close_position_pct'),
                    'bias': feature.bias if feature is not None else 'unknown',
                    'candle_type': feature.candle_type if feature is not None else 'unknown',
                }
            )

        return payload

    def _combine_features(
        self,
        daily_rows: list[dict[str, Any]],
        current_index: int,
        daily_row: dict[str, Any],
        weekly_row: dict[str, Any],
        monthly_row: dict[str, Any],
    ) -> dict[str, Any]:
        """Flatten aligned multi-timeframe rows into model features including technical indicators."""
        features: dict[str, Any] = {}

        for prefix, row in (('d', daily_row), ('w', weekly_row), ('m', monthly_row)):
            open_price = row['open']
            close_price = row['close']
            high_price = row['high']
            low_price = row['low']
            candle_range = max(high_price - low_price, 0.0)

            features[f'{prefix}_body_size_pct'] = row['body_size_pct']
            features[f'{prefix}_upper_wick_pct'] = row['upper_wick_pct']
            features[f'{prefix}_lower_wick_pct'] = row['lower_wick_pct']
            features[f'{prefix}_range_pct'] = row['range_pct']
            features[f'{prefix}_close_position_pct'] = row['close_position_pct']
            features[f'{prefix}_bias'] = row['bias']
            features[f'{prefix}_candle_type'] = row['candle_type']

            features[f'{prefix}_close_open_pct'] = 0.0 if open_price == 0 else ((close_price - open_price) / open_price) * 100.0
            features[f'{prefix}_high_low_pct'] = 0.0 if open_price == 0 else (candle_range / open_price) * 100.0
            features[f'{prefix}_close_low_position_pct'] = 0.0 if candle_range == 0 else ((close_price - low_price) / candle_range) * 100.0
            features[f'{prefix}_volume_log'] = self._volume_log(row['volume'])

        features['dw_close_ratio'] = self._safe_ratio(daily_row['close'], weekly_row['close'])
        features['dm_close_ratio'] = self._safe_ratio(daily_row['close'], monthly_row['close'])
        features['wm_close_ratio'] = self._safe_ratio(weekly_row['close'], monthly_row['close'])

        # Enhanced technical features computed from the full history up to current_index
        closes = [r['close'] for r in daily_rows[:current_index + 1]]
        highs = [r['high'] for r in daily_rows[:current_index + 1]]
        lows = [r['low'] for r in daily_rows[:current_index + 1]]
        volumes = [r['volume'] for r in daily_rows[:current_index + 1]]

        features.update(self._volatility_features(closes))
        features.update(self._trend_features(closes))
        features.update(self._volume_features(volumes))
        features.update(self._momentum_features(closes, highs, lows))
        features.update(self._support_resistance_features(closes, highs, lows, current_index, daily_rows))

        return features

    def _resolve_labels(self, daily_rows: list[dict[str, Any]], index: int, horizon_days: int, threshold: float) -> dict[str, bool]:
        """Compute binary targets with deterministic tie resolution."""
        current_close = daily_rows[index]['close']
        up_target = current_close * (1.0 + threshold)
        down_target = current_close * (1.0 - threshold)

        long_hit_step: int | None = None
        short_hit_step: int | None = None

        for step in range(1, horizon_days + 1):
            future_row = daily_rows[index + step]
            if long_hit_step is None and future_row['high'] >= up_target:
                long_hit_step = step
            if short_hit_step is None and future_row['low'] <= down_target:
                short_hit_step = step
            if long_hit_step is not None and short_hit_step is not None:
                break

        if long_hit_step is None and short_hit_step is None:
            return {'long_label': False, 'short_label': False, 'ambiguous': False}

        if long_hit_step is not None and short_hit_step is not None:
            if long_hit_step == short_hit_step:
                return {'long_label': False, 'short_label': False, 'ambiguous': True}
            if long_hit_step < short_hit_step:
                return {'long_label': True, 'short_label': False, 'ambiguous': False}
            return {'long_label': False, 'short_label': True, 'ambiguous': False}

        if long_hit_step is not None:
            return {'long_label': True, 'short_label': False, 'ambiguous': False}

        return {'long_label': False, 'short_label': True, 'ambiguous': False}

    def _aggregate_from_daily_rows(self, daily_rows: list[dict[str, Any]], end_index: int, timeframe: str) -> dict[str, Any] | None:
        """Build an as-of aggregate row from daily candles to prevent timeframe leakage."""
        if timeframe not in {self.TIMEFRAME_1WEEK, self.TIMEFRAME_1MONTH}:
            return None

        end_date = daily_rows[end_index]['candle_date']
        bucket_start = self._bucket_start_date(end_date, timeframe)

        bucket_rows: list[dict[str, Any]] = []
        pointer = end_index
        while pointer >= 0 and daily_rows[pointer]['candle_date'] >= bucket_start:
            bucket_rows.append(daily_rows[pointer])
            pointer -= 1

        if not bucket_rows:
            return None

        bucket_rows.sort(key=lambda row: row['candle_date'])
        open_price = bucket_rows[0]['open']
        close_price = bucket_rows[-1]['close']
        high_price = max(row['high'] for row in bucket_rows)
        low_price = min(row['low'] for row in bucket_rows)
        volume = int(sum(int(row['volume']) for row in bucket_rows))

        body_size_pct, upper_wick_pct, lower_wick_pct, range_pct, close_position_pct = self._derive_candle_percentages(
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
        )
        bias = self._resolve_bias(open_price, close_price)

        return {
            'candle_date': bucket_start,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume,
            'body_size_pct': body_size_pct,
            'upper_wick_pct': upper_wick_pct,
            'lower_wick_pct': lower_wick_pct,
            'range_pct': range_pct,
            'close_position_pct': close_position_pct,
            'bias': bias,
            'candle_type': 'aggregate_' + bias,
        }

    def _bucket_start_date(self, candle_date: date, timeframe: str) -> date:
        """Normalize a date to start of week/month for as-of aggregation."""
        if timeframe == self.TIMEFRAME_1WEEK:
            return candle_date - timedelta(days=candle_date.weekday())
        if timeframe == self.TIMEFRAME_1MONTH:
            return candle_date.replace(day=1)
        return candle_date

    def _derive_candle_percentages(self, open_price: float, high_price: float, low_price: float, close_price: float) -> tuple[float, float, float, float, float]:
        """Compute candle shape percentages from OHLC values."""
        candle_range = max(high_price - low_price, 0.0)
        body_size = abs(close_price - open_price)
        upper_wick = max(high_price - max(open_price, close_price), 0.0)
        lower_wick = max(min(open_price, close_price) - low_price, 0.0)

        if candle_range <= 0:
            body_size_pct = 0.0
            upper_wick_pct = 0.0
            lower_wick_pct = 0.0
            close_position_pct = 0.0
        else:
            body_size_pct = (body_size / candle_range) * 100.0
            upper_wick_pct = (upper_wick / candle_range) * 100.0
            lower_wick_pct = (lower_wick / candle_range) * 100.0
            close_position_pct = ((close_price - low_price) / candle_range) * 100.0

        range_pct = 0.0 if open_price == 0 else (candle_range / open_price) * 100.0
        return body_size_pct, upper_wick_pct, lower_wick_pct, range_pct, close_position_pct

    def _resolve_bias(self, open_price: float, close_price: float) -> str:
        """Classify candle bias for categorical model features."""
        if close_price > open_price:
            return 'bullish'
        if close_price < open_price:
            return 'bearish'
        return 'doji'

    def _as_float(self, value: Decimal | float | int) -> float:
        """Convert Decimal-compatible value to float."""
        return float(value)

    def _as_feature_float(self, feature: Feature | None, attribute: str) -> float:
        """Read feature numeric safely for missing feature rows."""
        if feature is None:
            return 0.0
        return float(getattr(feature, attribute))

    def _safe_ratio(self, numerator: float, denominator: float) -> float:
        """Compute safe ratio minus 1 for relative difference features."""
        if denominator == 0:
            return 0.0
        return (numerator / denominator) - 1.0

    def _volume_log(self, volume: int) -> float:
        """Compute stable log-like volume transform without extra dependencies."""
        if volume <= 0:
            return 0.0
        return float(math.log1p(volume))

    # ── Enhanced Technical Features ──────────────────────────────────────────

    def _volatility_features(self, closes: list[float]) -> dict[str, float]:
        """Compute rolling volatility regime features from recent close prices.

        Args:
            closes: Ordered list of close prices up to and including current day.

        Returns:
            Dictionary of volatility-related feature values.
        """
        features: dict[str, float] = {}
        for window in (10, 20):
            key = f'volatility_{window}d'
            if len(closes) >= window:
                window_closes = closes[-window:]
                mean = sum(window_closes) / window
                variance = sum((c - mean) ** 2 for c in window_closes) / window
                features[key] = math.sqrt(variance)
            else:
                features[key] = 0.0

        # Volatility ratio: short-term vs long-term (regime detection)
        v10 = features['volatility_10d']
        v20 = features['volatility_20d']
        features['volatility_ratio_10_20'] = (v10 / v20) if v20 > 0 else 1.0

        return features

    def _trend_features(self, closes: list[float]) -> dict[str, float]:
        """Compute SMA-based trend strength and direction features.

        Args:
            closes: Ordered list of close prices up to and including current day.

        Returns:
            Dictionary of trend-related feature values.
        """
        features: dict[str, float] = {}
        current_close = closes[-1] if closes else 0.0

        for window in (10, 20, 50):
            key_pos = f'close_vs_sma{window}_pct'
            key_slope = f'sma{window}_slope'
            if len(closes) >= window:
                sma = sum(closes[-window:]) / window
                features[key_pos] = ((current_close - sma) / sma) * 100.0 if sma > 0 else 0.0
                # Slope: percentage change of the SMA itself over half the window
                half = max(window // 2, 1)
                sma_prev = sum(closes[-(window + half):-half]) / window if len(closes) >= window + half else sma
                features[key_slope] = ((sma - sma_prev) / sma_prev) * 100.0 if sma_prev > 0 else 0.0
            else:
                features[key_pos] = 0.0
                features[key_slope] = 0.0

        # Whether price is in uptrend (SMA10 > SMA20 > SMA50)
        sma10_above_sma20 = 1 if (len(closes) >= 20 and sum(closes[-10:]) / 10 > sum(closes[-20:]) / 20) else 0
        sma20_above_sma50 = 1 if (len(closes) >= 50 and sum(closes[-20:]) / 20 > sum(closes[-50:]) / 50) else 0
        features['uptrend_alignment'] = float(sma10_above_sma20 + sma20_above_sma50)  # 0, 1, or 2

        return features

    def _volume_features(self, volumes: list[int]) -> dict[str, float]:
        """Compute volume spike and trend features.

        Args:
            volumes: Ordered list of volumes up to and including current day.

        Returns:
            Dictionary of volume-related feature values.
        """
        features: dict[str, float] = {}
        if not volumes:
            return {'volume_zscore_20d': 0.0, 'volume_ratio_5_20': 1.0}

        current_vol = float(volumes[-1])

        # Z-score of current volume vs 20-day mean/std
        if len(volumes) >= 20:
            window = [float(v) for v in volumes[-20:]]
            mean = sum(window) / len(window)
            std = math.sqrt(sum((v - mean) ** 2 for v in window) / len(window))
            features['volume_zscore_20d'] = (current_vol - mean) / std if std > 0 else 0.0
        else:
            features['volume_zscore_20d'] = 0.0

        # Volume acceleration: recent 5d average vs 20d average
        if len(volumes) >= 20:
            avg5 = sum(float(v) for v in volumes[-5:]) / 5
            avg20 = sum(float(v) for v in volumes[-20:]) / 20
            features['volume_ratio_5_20'] = avg5 / avg20 if avg20 > 0 else 1.0
        else:
            features['volume_ratio_5_20'] = 1.0

        return features

    def _momentum_features(self, closes: list[float], highs: list[float], lows: list[float]) -> dict[str, float]:
        """Compute RSI and rate-of-change momentum indicators.

        Args:
            closes: Ordered close prices.
            highs: Ordered high prices.
            lows: Ordered low prices.

        Returns:
            Dictionary of momentum feature values.
        """
        features: dict[str, float] = {}

        # Rate of change over multiple periods
        for period in (5, 10, 20):
            key = f'roc_{period}d'
            if len(closes) > period:
                prev = closes[-(period + 1)]
                features[key] = ((closes[-1] - prev) / prev) * 100.0 if prev > 0 else 0.0
            else:
                features[key] = 0.0

        # RSI-14: (avg gain / (avg gain + avg loss)) * 100
        features['rsi_14'] = self._compute_rsi(closes, period=14)

        # Stochastic %K: (close - lowest_low) / (highest_high - lowest_low) for 14 days
        if len(closes) >= 14 and len(highs) >= 14 and len(lows) >= 14:
            highest_high = max(highs[-14:])
            lowest_low = min(lows[-14:])
            rng = highest_high - lowest_low
            features['stochastic_k_14'] = ((closes[-1] - lowest_low) / rng) * 100.0 if rng > 0 else 50.0
        else:
            features['stochastic_k_14'] = 50.0

        return features

    def _support_resistance_features(
        self,
        closes: list[float],
        highs: list[float],
        lows: list[float],
        current_index: int,
        daily_rows: list[dict[str, Any]],
    ) -> dict[str, float]:
        """Compute distance from recent swing high/low support and resistance.

        Args:
            closes: Close prices up to current_index.
            highs: High prices up to current_index.
            lows: Low prices up to current_index.
            current_index: Index of current candle in daily_rows.
            daily_rows: Full list of daily OHLCV rows.

        Returns:
            Dictionary with support/resistance distance features.
        """
        features: dict[str, float] = {}
        current_close = closes[-1] if closes else 0.0

        if len(highs) >= 20 and current_close > 0:
            recent_high = max(highs[-20:])
            recent_low = min(lows[-20:])
            features['dist_from_20d_high_pct'] = ((current_close - recent_high) / recent_high) * 100.0
            features['dist_from_20d_low_pct'] = ((current_close - recent_low) / recent_low) * 100.0
        else:
            features['dist_from_20d_high_pct'] = 0.0
            features['dist_from_20d_low_pct'] = 0.0

        if len(highs) >= 52 and current_close > 0:
            high_52w = max(highs[-52:])
            low_52w = min(lows[-52:])
            features['dist_from_52w_high_pct'] = ((current_close - high_52w) / high_52w) * 100.0
            features['dist_from_52w_low_pct'] = ((current_close - low_52w) / low_52w) * 100.0
        else:
            features['dist_from_52w_high_pct'] = 0.0
            features['dist_from_52w_low_pct'] = 0.0

        return features

    def _compute_rsi(self, closes: list[float], period: int = 14) -> float:
        """Compute RSI indicator using Wilder's smoothing.

        Args:
            closes: Ordered list of close prices.
            period: RSI lookback period (default 14).

        Returns:
            RSI value between 0 and 100. Returns 50.0 if insufficient data.
        """
        if len(closes) < period + 1:
            return 50.0

        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [max(d, 0.0) for d in deltas]
        losses = [abs(min(d, 0.0)) for d in deltas]

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))
