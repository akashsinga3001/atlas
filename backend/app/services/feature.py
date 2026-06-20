# app/services/feature.py

from sqlalchemy.orm import Session

from app.repositories.ohlcv import OHLCVRepository
from app.repositories.features import SecurityFeatureRepository
from app.enums.ohlcv import OHLCVTimeFrame

from app.features.pipeline import FeaturePipeline


class FeatureService:
    """Service for managing feature extraction and storage."""

    def __init__(self, db: Session):
        self.db = db
        self.ohlcv_repo = OHLCVRepository(db)
        self.security_feature_repo = SecurityFeatureRepository(db)

    def generate_security_features(self, timeframe: OHLCVTimeFrame) -> int:
        """Generate and store features for all securities based on the specified timeframe."""
