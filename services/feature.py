"""Feature engineering service for OHLCV candles."""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import math
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker

from config import settings
from models.feature import Feature
from models.ohlcv import Ohlcv


class FeatureService:
    """Service class for computing and upserting derived candle features."""

    FOUR_DP = Decimal('0.0001')
    TIMEFRAMES = ('1DAY', '1WEEK', '1MONTH')

    def __init__(self) -> None:
        self._engine = create_engine(settings.DATABASE_URL, echo=settings.DB_ECHO, future=True)
        self._session_factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, future=True)

    def upsert_features(self, lookback_days: int = 90, backfill: bool = False) -> dict[str, Any]:
        """Compute and upsert candle features for each timeframe.
        
        Args:
            lookback_days: Days to lookback (ignored if backfill=True)
            backfill: If True, calculate features for ALL OHLCV records; if False, use lookback_days filter
        """
        start_date = None if backfill else date.today() - timedelta(days=lookback_days)
        # Pull additional warmup history so rolling features at the lookback boundary remain accurate.
        warmup_start = None if backfill else start_date - timedelta(days=400)

        with self._session_factory() as session:
            query = select(Ohlcv).where(Ohlcv.timeframe.in_(self.TIMEFRAMES))
            if warmup_start is not None:
                query = query.where(Ohlcv.candle_date >= warmup_start)

            candles = list(
                session.execute(
                    query.order_by(Ohlcv.security_id.asc(), Ohlcv.timeframe.asc(), Ohlcv.candle_date.asc(), Ohlcv.id.asc())
                ).scalars().all()
            )

        feature_rows = []
        grouped_candles: dict[tuple[int, str], list[Ohlcv]] = {}
        for candle in candles:
            grouped_candles.setdefault((int(candle.security_id), str(candle.timeframe)), []).append(candle)

        for (_, timeframe), candle_group in grouped_candles.items():
            closes: list[float] = []
            highs: list[float] = []
            lows: list[float] = []
            volumes: list[int] = []

            for candle in candle_group:
                close_value = float(candle.close)
                high_value = float(candle.high)
                low_value = float(candle.low)
                volume_value = int(candle.volume)

                closes.append(close_value)
                highs.append(high_value)
                lows.append(low_value)
                volumes.append(volume_value)

                if start_date is not None and candle.candle_date < start_date:
                    continue

                technical: dict[str, Decimal | None]
                if timeframe == '1DAY':
                    technical = self._technical_payload(closes, highs, lows, volumes)
                else:
                    technical = self._empty_technical_payload()

                body_size_pct, upper_wick_pct, lower_wick_pct, range_pct, close_position_pct, bias, candle_type = self._compute_features(candle)
                feature_rows.append(
                    {
                        'ohlcv_id': candle.id,
                        'body_size_pct': body_size_pct,
                        'upper_wick_pct': upper_wick_pct,
                        'lower_wick_pct': lower_wick_pct,
                        'range_pct': range_pct,
                        'close_position_pct': close_position_pct,
                        'bias': bias,
                        'candle_type': candle_type,
                        **technical,
                    }
                )

        upserted = self._upsert_feature_rows(feature_rows)

        return {
            'success': True,
            'candles_processed': len(candles),
            'inserted_or_updated': upserted,
            'lookback_days': lookback_days if not backfill else None,
            'backfill': backfill,
        }

    def _upsert_feature_rows(self, rows: list[dict[str, Any]]) -> int:
        """Bulk upsert feature rows using unique ohlcv_id."""
        if not rows:
            return 0

        statement = insert(Feature).values(rows)
        upsert_statement = statement.on_conflict_do_update(
            constraint='uq_features_ohlcv_id',
            set_={
                'body_size_pct': statement.excluded.body_size_pct,
                'upper_wick_pct': statement.excluded.upper_wick_pct,
                'lower_wick_pct': statement.excluded.lower_wick_pct,
                'range_pct': statement.excluded.range_pct,
                'close_position_pct': statement.excluded.close_position_pct,
                'bias': statement.excluded.bias,
                'candle_type': statement.excluded.candle_type,
                'volatility_10d': statement.excluded.volatility_10d,
                'volatility_20d': statement.excluded.volatility_20d,
                'volatility_ratio_10_20': statement.excluded.volatility_ratio_10_20,
                'close_vs_sma10_pct': statement.excluded.close_vs_sma10_pct,
                'close_vs_sma20_pct': statement.excluded.close_vs_sma20_pct,
                'close_vs_sma50_pct': statement.excluded.close_vs_sma50_pct,
                'sma10_slope': statement.excluded.sma10_slope,
                'sma20_slope': statement.excluded.sma20_slope,
                'sma50_slope': statement.excluded.sma50_slope,
                'uptrend_alignment': statement.excluded.uptrend_alignment,
                'volume_zscore_20d': statement.excluded.volume_zscore_20d,
                'volume_ratio_5_20': statement.excluded.volume_ratio_5_20,
                'roc_5d': statement.excluded.roc_5d,
                'roc_10d': statement.excluded.roc_10d,
                'roc_20d': statement.excluded.roc_20d,
                'rsi_14': statement.excluded.rsi_14,
                'stochastic_k_14': statement.excluded.stochastic_k_14,
                'dist_from_20d_high_pct': statement.excluded.dist_from_20d_high_pct,
                'dist_from_20d_low_pct': statement.excluded.dist_from_20d_low_pct,
                'dist_from_52w_high_pct': statement.excluded.dist_from_52w_high_pct,
                'dist_from_52w_low_pct': statement.excluded.dist_from_52w_low_pct,
                'updated_at': statement.excluded.updated_at,
            },
        )

        with self._session_factory() as session:
            result = session.execute(upsert_statement)
            session.commit()
            return int(result.rowcount or 0)

    def _compute_features(self, candle: Ohlcv) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, str, str]:
        """Compute percentage and type features from one candle."""
        open_price = Decimal(str(candle.open))
        high_price = Decimal(str(candle.high))
        low_price = Decimal(str(candle.low))
        close_price = Decimal(str(candle.close))

        candle_range = high_price - low_price
        body_size = abs(close_price - open_price)
        upper_wick = high_price - max(open_price, close_price)
        lower_wick = min(open_price, close_price) - low_price

        if candle_range <= 0:
            body_size_pct = Decimal('0')
            upper_wick_pct = Decimal('0')
            lower_wick_pct = Decimal('0')
            close_position_pct = Decimal('0')
        else:
            body_size_pct = (body_size / candle_range) * Decimal('100')
            upper_wick_pct = (upper_wick / candle_range) * Decimal('100')
            lower_wick_pct = (lower_wick / candle_range) * Decimal('100')
            close_position_pct = ((close_price - low_price) / candle_range) * Decimal('100')

        range_pct = Decimal('0') if open_price == 0 else ((candle_range / open_price) * Decimal('100'))

        bias = self._resolve_bias(open_price, close_price)
        candle_type = self._resolve_candle_type(body_size_pct, upper_wick_pct, lower_wick_pct, bias)

        return (self._q4(body_size_pct), self._q4(upper_wick_pct), self._q4(lower_wick_pct), self._q4(range_pct), self._q4(close_position_pct), bias, candle_type)

    def _resolve_bias(self, open_price: Decimal, close_price: Decimal) -> str:
        """Classify broad candle direction."""
        if close_price > open_price:
            return 'bullish'
        if close_price < open_price:
            return 'bearish'
        return 'doji'

    def _resolve_candle_type(self, body_pct: Decimal, upper_pct: Decimal, lower_pct: Decimal, bias: str) -> str:
        """Classify candle type with granular precision.
        
        Classification hierarchy (20+ types):
        1. Doji Family: Perfect, Gravestone, Dragonfly, Long-legged, Rickshaw, Umbrella
        2. Marubozu Family: Full/Close + Bullish/Bearish
        3. Hammer/Inversion Family: Hammer, Hanging Man, Inverted Hammer, Shooting Star
        4. Spinning Tops: Regular, Large Body
        5. Trend Candles: Strong Bullish, Strong Bearish
        """

        # Flat candle (no movement)
        if body_pct == 0 and upper_pct == 0 and lower_pct == 0:
            return 'flat'

        # ============ DOJI FAMILY (body_pct <= 10) ============
        if body_pct <= Decimal('10'):
            # Perfect Doji (body ~0, equal upper/lower wicks)
            if body_pct == 0 and upper_pct > Decimal('40') and lower_pct > Decimal('40'):
                return 'doji_perfect'

            # Gravestone Doji (upper wick dominant, little lower wick)
            if upper_pct >= Decimal('60') and lower_pct <= Decimal('10'):
                return 'doji_gravestone'

            # Dragonfly Doji (lower wick dominant, little upper wick)
            if lower_pct >= Decimal('60') and upper_pct <= Decimal('10'):
                return 'doji_dragonfly'

            # Long-legged Doji (both wicks extended)
            if upper_pct >= Decimal('35') and lower_pct >= Decimal('35'):
                return 'doji_long_legged'

            # Rickshaw Man (small body, moderate equal wicks)
            if upper_pct >= Decimal('20') and lower_pct >= Decimal('20') and upper_pct <= Decimal('50') and lower_pct <= Decimal('50'):
                return 'doji_rickshaw_man'

            # Umbrella Doji (one wick extended significantly)
            if (upper_pct >= Decimal('40') and lower_pct <= Decimal('15')) or (lower_pct >= Decimal('40') and upper_pct <= Decimal('15')):
                return 'doji_umbrella'

            # Generic small body doji
            return 'doji_small_body'

        # ============ MARUBOZU FAMILY (body >= 90, minimal wicks) ============
        if body_pct >= Decimal('90') and upper_pct <= Decimal('5') and lower_pct <= Decimal('5'):
            return 'marubozu_full_bullish' if bias == 'bullish' else 'marubozu_full_bearish'

        # Close Marubozu (body 80-90, minimal wicks)
        if body_pct >= Decimal('80') and upper_pct <= Decimal('8') and lower_pct <= Decimal('8'):
            return 'marubozu_close_bullish' if bias == 'bullish' else 'marubozu_close_bearish'

        # ============ HAMMER FAMILY (lower wick dominant) ============
        if lower_pct >= Decimal('50') and upper_pct <= Decimal('15'):
            # Hammer (lower wick + bullish close) → bullish reversal
            if bias == 'bullish':
                return 'hammer'
            # Hanging Man (lower wick + bearish close) → bearish reversal
            return 'hanging_man'

        # ============ SHOOTING STAR / INVERTED HAMMER (upper wick dominant) ============
        if upper_pct >= Decimal('50') and lower_pct <= Decimal('15'):
            # Shooting Star (upper wick + bearish close) → bearish reversal
            if bias == 'bearish':
                return 'shooting_star'
            # Inverted Hammer (upper wick + bullish close) → bullish reversal
            return 'inverted_hammer'

        # ============ SPINNING TOPS (small body, moderate wicks) ============
        if body_pct <= Decimal('30') and upper_pct >= Decimal('20') and lower_pct >= Decimal('20'):
            # Small Body Spinning Top
            if body_pct <= Decimal('15'):
                return 'spinning_top_small'
            # Large Body Spinning Top
            return 'spinning_top_large'

        # ============ STRONG TREND CANDLES ============
        # Strong Bullish (large body, minimal lower wick)
        if body_pct >= Decimal('60') and bias == 'bullish' and lower_pct <= Decimal('15'):
            return 'strong_bullish_candle'

        # Strong Bearish (large body, minimal upper wick)
        if body_pct >= Decimal('60') and bias == 'bearish' and upper_pct <= Decimal('15'):
            return 'strong_bearish_candle'

        # ============ FALLBACK: Generic Trend Candles ============
        if bias == 'bullish':
            return 'bullish_candle'
        if bias == 'bearish':
            return 'bearish_candle'
        return 'neutral_candle'

    def _q4(self, value: Decimal) -> Decimal:
        """Round a decimal value to 4 places with bankers-safe rounding."""
        return value.quantize(self.FOUR_DP, rounding=ROUND_HALF_UP)

    def _q4_float(self, value: float) -> Decimal:
        """Convert float to Decimal and quantize to 4dp."""
        return self._q4(Decimal(str(value)))

    def _empty_technical_payload(self) -> dict[str, Decimal | None]:
        """Return a null-filled payload for non-daily rows."""
        keys = [
            'volatility_10d',
            'volatility_20d',
            'volatility_ratio_10_20',
            'close_vs_sma10_pct',
            'close_vs_sma20_pct',
            'close_vs_sma50_pct',
            'sma10_slope',
            'sma20_slope',
            'sma50_slope',
            'uptrend_alignment',
            'volume_zscore_20d',
            'volume_ratio_5_20',
            'roc_5d',
            'roc_10d',
            'roc_20d',
            'rsi_14',
            'stochastic_k_14',
            'dist_from_20d_high_pct',
            'dist_from_20d_low_pct',
            'dist_from_52w_high_pct',
            'dist_from_52w_low_pct',
        ]
        return {key: None for key in keys}

    def _technical_payload(
        self,
        closes: list[float],
        highs: list[float],
        lows: list[float],
        volumes: list[int],
    ) -> dict[str, Decimal]:
        """Compute rolling technical indicators for a single candle using as-of history."""
        current_close = closes[-1] if closes else 0.0

        def volatility(window: int) -> float:
            if len(closes) < window:
                return 0.0
            window_closes = closes[-window:]
            mean = sum(window_closes) / window
            variance = sum((item - mean) ** 2 for item in window_closes) / window
            return math.sqrt(variance)

        v10 = volatility(10)
        v20 = volatility(20)
        volatility_ratio = (v10 / v20) if v20 > 0 else 1.0

        def close_vs_sma(window: int) -> float:
            if len(closes) < window:
                return 0.0
            sma = sum(closes[-window:]) / window
            return ((current_close - sma) / sma) * 100.0 if sma > 0 else 0.0

        def sma_slope(window: int) -> float:
            if len(closes) < window:
                return 0.0
            sma = sum(closes[-window:]) / window
            half = max(window // 2, 1)
            if len(closes) < window + half:
                return 0.0
            sma_prev = sum(closes[-(window + half):-half]) / window
            return ((sma - sma_prev) / sma_prev) * 100.0 if sma_prev > 0 else 0.0

        sma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else 0.0
        sma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else 0.0
        sma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else 0.0
        uptrend_alignment = float((1 if len(closes) >= 20 and sma10 > sma20 else 0) + (1 if len(closes) >= 50 and sma20 > sma50 else 0))

        if len(volumes) >= 20:
            volume_window = [float(item) for item in volumes[-20:]]
            volume_mean = sum(volume_window) / len(volume_window)
            volume_std = math.sqrt(sum((item - volume_mean) ** 2 for item in volume_window) / len(volume_window))
            volume_zscore_20d = ((float(volumes[-1]) - volume_mean) / volume_std) if volume_std > 0 else 0.0
            avg5 = sum(float(item) for item in volumes[-5:]) / 5
            avg20 = sum(float(item) for item in volumes[-20:]) / 20
            volume_ratio_5_20 = avg5 / avg20 if avg20 > 0 else 1.0
        else:
            volume_zscore_20d = 0.0
            volume_ratio_5_20 = 1.0

        def roc(period: int) -> float:
            if len(closes) <= period:
                return 0.0
            previous = closes[-(period + 1)]
            return ((closes[-1] - previous) / previous) * 100.0 if previous > 0 else 0.0

        rsi_14 = self._compute_rsi(closes, period=14)

        if len(closes) >= 14 and len(highs) >= 14 and len(lows) >= 14:
            highest_high = max(highs[-14:])
            lowest_low = min(lows[-14:])
            rng = highest_high - lowest_low
            stochastic_k_14 = ((closes[-1] - lowest_low) / rng) * 100.0 if rng > 0 else 50.0
        else:
            stochastic_k_14 = 50.0

        if len(highs) >= 20 and current_close > 0:
            recent_high = max(highs[-20:])
            recent_low = min(lows[-20:])
            dist_from_20d_high_pct = ((current_close - recent_high) / recent_high) * 100.0 if recent_high > 0 else 0.0
            dist_from_20d_low_pct = ((current_close - recent_low) / recent_low) * 100.0 if recent_low > 0 else 0.0
        else:
            dist_from_20d_high_pct = 0.0
            dist_from_20d_low_pct = 0.0

        if len(highs) >= 52 and current_close > 0:
            high_52w = max(highs[-52:])
            low_52w = min(lows[-52:])
            dist_from_52w_high_pct = ((current_close - high_52w) / high_52w) * 100.0 if high_52w > 0 else 0.0
            dist_from_52w_low_pct = ((current_close - low_52w) / low_52w) * 100.0 if low_52w > 0 else 0.0
        else:
            dist_from_52w_high_pct = 0.0
            dist_from_52w_low_pct = 0.0

        return {
            'volatility_10d': self._q4_float(v10),
            'volatility_20d': self._q4_float(v20),
            'volatility_ratio_10_20': self._q4_float(volatility_ratio),
            'close_vs_sma10_pct': self._q4_float(close_vs_sma(10)),
            'close_vs_sma20_pct': self._q4_float(close_vs_sma(20)),
            'close_vs_sma50_pct': self._q4_float(close_vs_sma(50)),
            'sma10_slope': self._q4_float(sma_slope(10)),
            'sma20_slope': self._q4_float(sma_slope(20)),
            'sma50_slope': self._q4_float(sma_slope(50)),
            'uptrend_alignment': self._q4_float(uptrend_alignment),
            'volume_zscore_20d': self._q4_float(volume_zscore_20d),
            'volume_ratio_5_20': self._q4_float(volume_ratio_5_20),
            'roc_5d': self._q4_float(roc(5)),
            'roc_10d': self._q4_float(roc(10)),
            'roc_20d': self._q4_float(roc(20)),
            'rsi_14': self._q4_float(rsi_14),
            'stochastic_k_14': self._q4_float(stochastic_k_14),
            'dist_from_20d_high_pct': self._q4_float(dist_from_20d_high_pct),
            'dist_from_20d_low_pct': self._q4_float(dist_from_20d_low_pct),
            'dist_from_52w_high_pct': self._q4_float(dist_from_52w_high_pct),
            'dist_from_52w_low_pct': self._q4_float(dist_from_52w_low_pct),
        }

    def _compute_rsi(self, closes: list[float], period: int = 14) -> float:
        """Compute RSI indicator using period-length trailing gains and losses."""
        if len(closes) < period + 1:
            return 50.0

        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [max(delta, 0.0) for delta in deltas]
        losses = [abs(min(delta, 0.0)) for delta in deltas]

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))
