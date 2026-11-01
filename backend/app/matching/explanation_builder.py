from typing import List
from app.matching.models import (
    EligibilityStatus,
    ProductCompatibilityResult,
    StorageCompatibilityResult,
    QuantityCompatibilityResult,
)


class ExplanationBuilder:
    """
    Deterministic explanation builder for candidate match evaluations.
    Translates mathematical evaluation results, compatibility assessments, and
    geospatial feasibility into clear, actionable human-readable explanations.
    """

    @classmethod
    def build(
        cls,
        eligibility: EligibilityStatus,
        is_eligible: bool,
        rejection_reasons: List[str],
        product: ProductCompatibilityResult,
        storage: StorageCompatibilityResult,
        quantity: QuantityCompatibilityResult,
        perishability_urgency: str,
        remaining_hours: float,
        transit_feasibility: str,
        road_distance_km: float,
        estimated_transit_minutes: float,
        is_route_fallback: bool,
        total_score: float,
    ) -> str:
        if not is_eligible or eligibility == "INELIGIBLE":
            count = len(rejection_reasons)
            reasons_summary = "; ".join(rejection_reasons)
            return (
                f"Candidate INELIGIBLE due to {count} failed constraint(s): {reasons_summary}."
            )

        if eligibility == "REVIEW_REQUIRED":
            reasons_summary = "; ".join(rejection_reasons) if rejection_reasons else "Data ambiguity detected"
            return (
                f"Candidate REQUIRES HUMAN REVIEW: {reasons_summary}. "
                f"Preliminary feasibility: {road_distance_km} km distance ({estimated_transit_minutes} mins), "
                f"with {quantity.matched_quantity_kg} kg matched quantity."
            )

        # ELIGIBLE CANDIDATE
        route_mode = "fallback approximation" if is_route_fallback else "OSRM driving route"
        sat_text = (
            f"fully fulfills {quantity.demand_outstanding_kg} kg requested"
            if not quantity.is_partial
            else f"partially fulfills {quantity.matched_quantity_kg} kg of {quantity.demand_outstanding_kg} kg requested ({quantity.fulfillment_ratio * 100:.1f}%)"
        )

        return (
            f"ELIGIBLE candidate (Score: {total_score}/100): Product and storage compatible. "
            f"Logistics feasible via {route_mode} ({road_distance_km} km, ~{estimated_transit_minutes} mins transit). "
            f"Surplus {sat_text} with {remaining_hours:.1f} hrs of usable shelf life remaining ({perishability_urgency} urgency)."
        )
