from decimal import Decimal
from typing import Union
from app.matching.models import QuantityCompatibilityResult, QuantityMatchLevel


class QuantityCompatibilityEvaluator:
    """
    Deterministic quantity compatibility evaluator.
    Evaluates volume alignment, partial fulfillment feasibility, and utilization ratios.
    Never modifies database state or locks inventory.
    """

    @classmethod
    def evaluate(
        cls,
        surplus_remaining_kg: Union[Decimal, float],
        demand_requested_kg: Union[Decimal, float],
        demand_fulfilled_kg: Union[Decimal, float] = 0.0,
    ) -> QuantityCompatibilityResult:
        s_qty = max(0.0, float(surplus_remaining_kg or 0.0))
        d_req = max(0.0, float(demand_requested_kg or 0.0))
        d_ful = max(0.0, float(demand_fulfilled_kg or 0.0))
        d_out = max(0.0, round(d_req - d_ful, 2))

        if s_qty <= 0.0:
            return QuantityCompatibilityResult(
                match_level="ZERO_SURPLUS",
                is_compatible=False,
                surplus_available_kg=0.0,
                demand_outstanding_kg=d_out,
                matched_quantity_kg=0.0,
                fulfillment_ratio=0.0,
                surplus_utilization_ratio=0.0,
                is_partial=False,
                notes="Surplus batch has zero remaining inventory available for redistribution.",
            )

        if d_out <= 0.0:
            return QuantityCompatibilityResult(
                match_level="ZERO_DEMAND",
                is_compatible=False,
                surplus_available_kg=s_qty,
                demand_outstanding_kg=0.0,
                matched_quantity_kg=0.0,
                fulfillment_ratio=0.0,
                surplus_utilization_ratio=0.0,
                is_partial=False,
                notes="Demand request is already fully fulfilled; no outstanding requirement.",
            )

        matched_qty = round(min(s_qty, d_out), 2)
        fulfillment_ratio = round(matched_qty / d_out, 4) if d_out > 0 else 0.0
        utilization_ratio = round(matched_qty / s_qty, 4) if s_qty > 0 else 0.0

        if s_qty >= d_out:
            match_level: QuantityMatchLevel = "FULL_SATISFACTION"
            is_partial = False
            notes = (
                f"Surplus batch ({s_qty} kg) can completely fulfill the outstanding receiver requirement ({d_out} kg)."
            )
        else:
            match_level = "PARTIAL_SATISFACTION"
            is_partial = True
            notes = (
                f"Surplus batch provides {s_qty} kg, partially satisfying {d_out} kg requested "
                f"({fulfillment_ratio * 100:.1f}% fulfillment)."
            )

        return QuantityCompatibilityResult(
            match_level=match_level,
            is_compatible=True,
            surplus_available_kg=s_qty,
            demand_outstanding_kg=d_out,
            matched_quantity_kg=matched_qty,
            fulfillment_ratio=fulfillment_ratio,
            surplus_utilization_ratio=utilization_ratio,
            is_partial=is_partial,
            notes=notes,
        )
