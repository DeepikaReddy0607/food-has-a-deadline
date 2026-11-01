import math
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from app.intelligence.models import (
    PerishabilityEvaluation,
    BatchEvaluationResponse,
    UrgencyLevel,
    DataQualityLevel,
)
from app.intelligence.urgency_classifier import UrgencyClassifier
from app.intelligence.condition_assessor import ConditionAssessor
from app.intelligence.storage_assessor import StorageAssessor
from app.intelligence.reference_data import FOOD_SAFETY_DISCLAIMER


class PerishabilityEngine:
    """
    Deterministic Perishability Intelligence Engine.
    Converts surplus inventory data into actionable operational urgency classifications
    and logistics guidance without relying on opaque ML models or external network calls.
    """

    @classmethod
    def evaluate(
        cls,
        estimated_deadline: Optional[datetime],
        harvest_or_prep_date: Optional[datetime] = None,
        food_condition: Optional[str] = None,
        storage_condition: Optional[str] = None,
        listing_id: Optional[uuid.UUID] = None,
        evaluation_time: Optional[datetime] = None,
    ) -> PerishabilityEvaluation:
        """
        Evaluate perishability intelligence from raw parameters.
        Accepts an optional controllable `evaluation_time` for deterministic testing.
        """
        now = evaluation_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        warnings: List[str] = []
        data_quality: DataQualityLevel = "COMPLETE"

        # 1. Temporal Evaluation
        if estimated_deadline is None:
            return PerishabilityEvaluation(
                listing_id=listing_id,
                remaining_seconds=float("nan"),
                remaining_hours=float("nan"),
                urgency="PENDING",
                condition=food_condition or "UNKNOWN",
                storage_condition=storage_condition or "UNKNOWN",
                warnings=["DATA QUALITY CRITICAL: Usable deadline is missing."],
                explanation="No usable deadline was provided. Urgency cannot be computed and remains PENDING.",
                data_quality="INVALID",
                evaluated_at=now,
                factors={"error": "missing_estimated_deadline"},
                disclaimer=FOOD_SAFETY_DISCLAIMER,
            )

        deadline = estimated_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
            warnings.append("Timestamp was naive UTC; normalized to timezone-aware UTC.")

        remaining_seconds = (deadline - now).total_seconds()
        remaining_hours = round(remaining_seconds / 3600.0, 2)

        if remaining_seconds <= 0:
            warnings.append(
                "CUT-OFF PASSED: The estimated usable deadline has expired. Food must be re-inspected before any handover."
            )

        # Harvest / Prep validation
        if harvest_or_prep_date is not None:
            prep = harvest_or_prep_date
            if prep.tzinfo is None:
                prep = prep.replace(tzinfo=timezone.utc)
            if deadline <= prep:
                warnings.append(
                    "DATA QUALITY INCONSISTENCY: Estimated deadline is prior to or identical to harvest/prep date."
                )
                data_quality = "SUSPECT"
        else:
            warnings.append("Harvest or preparation date was not specified.")
            if data_quality == "COMPLETE":
                data_quality = "PARTIAL"

        # 2. Condition Assessment
        cond_assessment = ConditionAssessor.assess(food_condition)
        warnings.extend(cond_assessment["warnings"])
        if not cond_assessment["is_valid"] and data_quality == "COMPLETE":
            data_quality = "PARTIAL"

        # 3. Storage Assessment
        stor_assessment = StorageAssessor.assess(storage_condition)
        warnings.extend(stor_assessment["warnings"])
        if not stor_assessment["is_valid"] and data_quality == "COMPLETE":
            data_quality = "PARTIAL"

        # 4. Urgency Classification
        urgency: UrgencyLevel = UrgencyClassifier.classify(remaining_seconds)
        explanation = UrgencyClassifier.explain(urgency, remaining_seconds)

        # If data was completely invalid, keep as PENDING
        if math.isnan(remaining_seconds):
            urgency = "PENDING"
            data_quality = "INVALID"

        factors: Dict[str, Any] = {
            "remaining_seconds": remaining_seconds,
            "remaining_hours": remaining_hours,
            "condition_factor": cond_assessment["notes"],
            "requires_immediate_action": cond_assessment["requires_immediate_action"],
            "storage_factor": stor_assessment["notes"],
            "requires_cold_chain": stor_assessment["requires_cold_chain"],
        }

        return PerishabilityEvaluation(
            listing_id=listing_id,
            remaining_seconds=round(remaining_seconds, 1),
            remaining_hours=remaining_hours,
            urgency=urgency,
            condition=cond_assessment["condition"],
            storage_condition=stor_assessment["storage_condition"],
            warnings=warnings,
            explanation=explanation,
            data_quality=data_quality,
            evaluated_at=now,
            factors=factors,
            disclaimer=FOOD_SAFETY_DISCLAIMER,
        )

    @classmethod
    def evaluate_listing(
        cls, listing: Any, evaluation_time: Optional[datetime] = None
    ) -> PerishabilityEvaluation:
        """
        Evaluate a SurplusListing ORM model or compatible object.
        """
        return cls.evaluate(
            estimated_deadline=getattr(listing, "estimated_deadline", None),
            harvest_or_prep_date=getattr(listing, "harvest_or_prep_date", None),
            food_condition=getattr(listing, "food_condition", None),
            storage_condition=getattr(listing, "storage_condition", None),
            listing_id=getattr(listing, "id", None),
            evaluation_time=evaluation_time,
        )

    @classmethod
    def batch_evaluate(
        cls, listings: List[Any], evaluation_time: Optional[datetime] = None
    ) -> BatchEvaluationResponse:
        """
        Evaluate multiple listings and return aggregated summary and detailed evaluations.
        """
        counts = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MODERATE": 0,
            "LOW": 0,
            "PENDING": 0,
        }
        evaluations: List[PerishabilityEvaluation] = []

        for item in listings:
            ev = cls.evaluate_listing(item, evaluation_time=evaluation_time)
            evaluations.append(ev)
            if ev.urgency in counts:
                counts[ev.urgency] += 1
            else:
                counts["PENDING"] += 1

        return BatchEvaluationResponse(
            total_evaluated=len(evaluations),
            counts_by_urgency=counts,
            items=evaluations,
        )
