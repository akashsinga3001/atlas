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

    def build_training_dataset(self, horizon_days: int, threshold_pct: float) -> DatasetBuildResult:
        """Construct supervised training rows for long/short binary targets."""
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

                weekly_row = self._aggregate_from_daily_rows(daily_rows, index, self.TIMEFRAME_1WEEK)
                monthly_row = self._aggregate_from_daily_rows(daily_rows, index, self.TIMEFRAME_1MONTH)
                if weekly_row is None or monthly_row is None:
                    continue

                label_info = self._resolve_labels(daily_rows, index, horizon_days, threshold)
                if label_info['ambiguous']:
                    continue

                feature_payload = self._combine_features(
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

    def build_inference_dataset(self) -> DatasetBuildResult:
        """Construct most-recent inference rows for each active EQ ticker."""
        daily = self._load_rows_by_security(self.TIMEFRAME_1DAY)

        records: list[dict[str, Any]] = []
        feature_keys: set[str] = set()

        for security_id, daily_rows in daily.items():
            if not daily_rows:
                continue

            current_index = len(daily_rows) - 1
            current = daily_rows[current_index]
            prediction_date = current['candle_date']

            weekly_row = self._aggregate_from_daily_rows(daily_rows, current_index, self.TIMEFRAME_1WEEK)
            monthly_row = self._aggregate_from_daily_rows(daily_rows, current_index, self.TIMEFRAME_1MONTH)
            if weekly_row is None or monthly_row is None:
                continue

            feature_payload = self._combine_features(
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

    def _combine_features(self, daily_row: dict[str, Any], weekly_row: dict[str, Any], monthly_row: dict[str, Any]) -> dict[str, Any]:
        """Flatten aligned multi-timeframe rows into model features."""
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
            features[f'{prefix}_high_low_pct'] = 0.0 if open_price == 0 else ((candle_range) / open_price) * 100.0
            features[f'{prefix}_close_low_position_pct'] = 0.0 if candle_range == 0 else ((close_price - low_price) / candle_range) * 100.0
            features[f'{prefix}_volume_log'] = self._volume_log(row['volume'])

        features['dw_close_ratio'] = self._safe_ratio(daily_row['close'], weekly_row['close'])
        features['dm_close_ratio'] = self._safe_ratio(daily_row['close'], monthly_row['close'])
        features['wm_close_ratio'] = self._safe_ratio(weekly_row['close'], monthly_row['close'])

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
