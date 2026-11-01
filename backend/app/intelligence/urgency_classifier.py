import math
from typing import Optional
from app.intelligence.models import UrgencyLevel

# Threshold constants in seconds
CRITICAL_THRESHOLD_SECONDS = 6 * 3600      # 21,600s (6 hours)
HIGH_THRESHOLD_SECONDS = 24 * 3600          # 86,400s (24 hours)
MODERATE_THRESHOLD_SECONDS = 72 * 3600      # 259,200s (72 hours)


class UrgencyClassifier:
    """
    Deterministic urgency classification based strictly on supplier-provided deadline.

    Thresholds:
    - remaining_time < 6 hours       -> CRITICAL
    - 6h <= remaining_time < 24h     -> HIGH
    - 24h <= remaining_time < 72h    -> MODERATE
    - remaining_time >= 72h          -> LOW
    - invalid or missing data        -> PENDING
    """

    @staticmethod
    def classify(remaining_seconds: Optional[float]) -> UrgencyLevel:
        if remaining_seconds is None or math.isnan(remaining_seconds):
            return "PENDING"

        if remaining_seconds < CRITICAL_THRESHOLD_SECONDS:
            return "CRITICAL"
        elif remaining_seconds < HIGH_THRESHOLD_SECONDS:
            return "HIGH"
        elif remaining_seconds < MODERATE_THRESHOLD_SECONDS:
            return "MODERATE"
        else:
            return "LOW"

    @staticmethod
    def explain(urgency: UrgencyLevel, remaining_seconds: Optional[float]) -> str:
        if remaining_seconds is None or math.isnan(remaining_seconds) or urgency == "PENDING":
            return "Usable deadline information is missing or invalid. Urgency classification is PENDING until verified."

        hours = remaining_seconds / 3600.0

        if remaining_seconds <= 0:
            return (
                f"The estimated usable cut-off passed {abs(hours):.1f} hours ago. "
                "Urgency is CRITICAL; immediate verification is required to prevent dispatch of spoiled food."
            )

        if urgency == "CRITICAL":
            return (
                f"This listing has only {hours:.1f} hours remaining ({int(remaining_seconds // 60)} minutes) "
                "before its supplier-provided usable deadline. It requires immediate same-day dispatch."
            )
        elif urgency == "HIGH":
            return (
                f"This listing has {hours:.1f} hours remaining before its deadline (less than 24 hours). "
                "It should be allocated and moved during the upcoming redistribution cycle."
            )
        elif urgency == "MODERATE":
            days = hours / 24.0
            return (
                f"This listing has {hours:.1f} hours ({days:.1f} days) remaining before its deadline. "
                "It is eligible for standard scheduled allocation and multi-stop batching."
            )
        else:  # LOW
            days = hours / 24.0
            return (
                f"This listing has {hours:.1f} hours ({days:.1f} days) remaining before its deadline. "
                "Inventory is stable and suitable for flexible regional routing or batch redistribution."
            )
