import math
from typing import Optional
from app.matching.models import ScoreBreakdown


class CandidateRanker:
    """
    Deterministic scoring and ranking engine for candidate matches.
    Normalizes multi-factor criteria into transparent, weighted component scores (0 to 100).
    Enforces the core architectural invariant: Ineligible candidates receive 0.0 total score
    and can NEVER become eligible through soft ranking factors.
    """

    W_URGENCY = 0.25
    W_PROXIMITY = 0.25
    W_SLACK = 0.20
    W_QUANTITY = 0.15
    W_PRIORITY = 0.15

    @classmethod
    def calculate_score(
        cls,
        is_eligible: bool,
        urgency: str,
        remaining_hours: float,
        road_distance_km: float,
        transit_feasibility: str,
        available_minutes: Optional[float],
        required_minutes: Optional[float],
        surplus_available_kg: float,
        demand_outstanding_kg: float,
        receiver_priority: int,
    ) -> ScoreBreakdown:
        # If candidate fails hard constraints, total score is strictly 0.0
        if not is_eligible:
            return ScoreBreakdown(
                urgency_score=0.0,
                proximity_score=0.0,
                shelf_life_margin_score=0.0,
                quantity_fit_score=0.0,
                priority_score=0.0,
                total_score=0.0,
            )

        # 1. Urgency Score (0 - 100)
        # Prioritizes expiring food before it spoils
        if remaining_hours is None or math.isnan(remaining_hours) or remaining_hours <= 0:
            urgency_score = 20.0
        elif remaining_hours <= 2.0:
            urgency_score = 100.0
        elif remaining_hours <= 6.0:
            urgency_score = 90.0 + (6.0 - remaining_hours) * 2.5
        elif remaining_hours <= 24.0:
            urgency_score = 70.0 + (24.0 - remaining_hours) * 1.0
        elif remaining_hours <= 72.0:
            urgency_score = 40.0 + (72.0 - remaining_hours) * 0.6
        else:
            urgency_score = 30.0

        urgency_score = max(0.0, min(100.0, urgency_score))

        # 2. Proximity Score (0 - 100)
        # Continuous exponential decay: 0 km -> 100, 15 km -> ~55, 30 km -> ~30
        dist = max(0.0, road_distance_km)
        proximity_score = max(0.0, min(100.0, 100.0 * math.exp(-dist / 25.0)))

        # 3. Shelf-life Margin / Slack Score (0 - 100)
        if (
            transit_feasibility != "FEASIBLE"
            or available_minutes is None
            or required_minutes is None
        ):
            slack_score = 10.0
        else:
            slack = available_minutes - required_minutes
            if slack >= 180.0:
                slack_score = 100.0
            elif slack >= 60.0:
                slack_score = 70.0 + ((slack - 60.0) / 120.0) * 30.0
            elif slack >= 30.0:
                slack_score = 40.0 + ((slack - 30.0) / 30.0) * 30.0
            elif slack > 0:
                slack_score = max(5.0, (slack / 30.0) * 40.0)
            else:
                slack_score = 0.0

        # 4. Quantity Fit Score (0 - 100)
        s_qty = max(0.0, surplus_available_kg)
        d_qty = max(0.0, demand_outstanding_kg)
        if s_qty <= 0 or d_qty <= 0:
            quantity_score = 0.0
        else:
            ratio = min(s_qty, d_qty) / max(s_qty, d_qty)
            # Base 40 points for having positive matching inventory, up to 100 for exact alignment
            quantity_score = 40.0 + 60.0 * ratio

        # 5. Receiver Priority Score (0 - 100)
        priority_map = {5: 100.0, 4: 85.0, 3: 70.0, 2: 50.0, 1: 30.0}
        priority_score = priority_map.get(receiver_priority, 60.0)

        # Weighted Composite
        total_score = (
            cls.W_URGENCY * urgency_score
            + cls.W_PROXIMITY * proximity_score
            + cls.W_SLACK * slack_score
            + cls.W_QUANTITY * quantity_score
            + cls.W_PRIORITY * priority_score
        )

        return ScoreBreakdown(
            urgency_score=round(urgency_score, 1),
            proximity_score=round(proximity_score, 1),
            shelf_life_margin_score=round(slack_score, 1),
            quantity_fit_score=round(quantity_score, 1),
            priority_score=round(priority_score, 1),
            total_score=round(total_score, 1),
        )
