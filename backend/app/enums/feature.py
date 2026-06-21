# backend/app/enums/feature.py

from enum import Enum as PythonEnum


class FeatureCalculationType(PythonEnum):
    """Enum for different types of feature calculations."""
    COMPLETE = "complete"
    INCREMENTAL = "incremental"
