from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from app.geospatial.models import FeasibilityStatus


class FeasibilityChecker:
    """
    Deterministic transportation feasibility evaluator.
    Determines whether a proposed food redistribution route can physically be executed
    before the food's estimated usable shelf-life expires.
    """

    @staticmethod
    def check_feasibility(
        estimated_usable_deadline: Optional[datetime],
        estimated_travel_minutes: Optional[float],
        handling_buffer_minutes: int = 30,
        evaluation_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        warnings: List[str] = []

        if estimated_usable_deadline is None or estimated_travel_minutes is None:
            warnings.append(
                "DATA QUALITY WARNING: Missing usable deadline or travel time duration; "
                "temporal transportation feasibility cannot be confirmed."
            )
            return {
                "feasibility": "UNKNOWN",
                "available_minutes": None,
                "required_minutes": None,
                "handling_buffer_minutes": handling_buffer_minutes,
                "warnings": warnings,
            }

        now = evaluation_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        deadline = estimated_usable_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
            warnings.append("Usable deadline timestamp was naive UTC; normalized to timezone-aware UTC.")

        available_seconds = (deadline - now).total_seconds()
        available_minutes = round(available_seconds / 60.0, 1)
        required_minutes = round(estimated_travel_minutes + float(handling_buffer_minutes), 1)

        feasibility: FeasibilityStatus

        if available_minutes <= 0:
            feasibility = "INFEASIBLE"
            warnings.append(
                f"TEMPORALLY INFEASIBLE: Usable deadline passed {abs(available_minutes):.1f} minutes ago."
            )
        elif required_minutes > available_minutes:
            feasibility = "INFEASIBLE"
            deficit = round(required_minutes - available_minutes, 1)
            warnings.append(
                f"TEMPORALLY INFEASIBLE: Required delivery time ({required_minutes}m = "
                f"{estimated_travel_minutes}m transit + {handling_buffer_minutes}m buffer) "
                f"exceeds remaining shelf life ({available_minutes}m) by {deficit} minutes."
            )
        else:
            feasibility = "FEASIBLE"
            slack = round(available_minutes - required_minutes, 1)
            if slack < 60.0:
                warnings.append(
                    f"TIGHT MARGIN: Feasible with only {slack} minutes of spare buffer remaining."
                )

        return {
            "feasibility": feasibility,
            "available_minutes": available_minutes,
            "required_minutes": required_minutes,
            "handling_buffer_minutes": handling_buffer_minutes,
            "warnings": warnings,
        }
