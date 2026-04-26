"""Feature engineering service for OHLCV candles."""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
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
        with self._session_factory() as session:
            query = select(Ohlcv).where(Ohlcv.timeframe.in_(self.TIMEFRAMES))

            # If not backfilling, apply date filter for recent candles only
            if not backfill:
                start_date = date.today() - timedelta(days=lookback_days)
                query = query.where(Ohlcv.candle_date >= start_date)

            candles = list(session.execute(query.order_by(Ohlcv.candle_date.asc(), Ohlcv.id.asc())).scalars().all())

        feature_rows = []
        for candle in candles:
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
