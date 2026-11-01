import uuid
from typing import Dict, List, Tuple
from app.optimization.allocation_problem import AllocationProblem
from app.optimization.models import (
    AllocationItemDetail,
    UnfulfilledDemandDetail,
    UnallocatedSurplusDetail,
)


class ProposalExplainer:
    """
    Generates deterministic, transparent, and auditable operational justifications
    and unmet demand / unallocated surplus diagnostic explanations.
    """

    @classmethod
    def generate_justification(
        cls,
        total_allocated_kg: float,
        total_unallocated_kg: float,
        total_unmet_demand_kg: float,
        estimated_total_transit_km: float,
        items: List[AllocationItemDetail],
        solver_status: str,
    ) -> str:
        if solver_status in ("INFEASIBLE", "MODEL_INVALID"):
            return f"Mathematical optimization failed with status '{solver_status}'. No compatible or feasible redistribution flows could be formed."

        if not items or total_allocated_kg <= 0:
            return "No eligible matches found between active surplus listings and open receiver demands. Zero food could be allocated."

        # Count urgency breakdown
        urgency_counts: Dict[str, float] = {}
        for it in items:
            urgency_counts[it.urgency_at_allocation] = urgency_counts.get(it.urgency_at_allocation, 0.0) + it.allocated_quantity_kg

        urgency_desc_parts = [
            f"{qty:.2f} kg ({urgency})" for urgency, qty in urgency_counts.items()
        ]
        urgency_str = ", ".join(urgency_desc_parts)

        distinct_suppliers = len(set(it.supplier_id for it in items))
        distinct_receivers = len(set(it.receiver_id for it in items))

        justification = (
            f"Google OR-Tools CP-SAT ({solver_status}) successfully proposed redistribution of {total_allocated_kg:.2f} kg "
            f"across {len(items)} allocation flows connecting {distinct_suppliers} supplier facilities to {distinct_receivers} receiver organizations. "
            f"Prioritized urgent perishables: {urgency_str}. "
            f"Estimated cumulative road network transit is {estimated_total_transit_km:.2f} km. "
            f"Remaining unallocated surplus: {total_unallocated_kg:.2f} kg. Remaining unmet demand: {total_unmet_demand_kg:.2f} kg."
        )
        return justification

    @classmethod
    def diagnose_unfulfilled_demands(
        cls,
        problem: AllocationProblem,
        allocations_kg: Dict[Tuple[uuid.UUID, uuid.UUID], float],
    ) -> List[UnfulfilledDemandDetail]:
        details: List[UnfulfilledDemandDetail] = []

        for d_id, d_node in problem.demand_nodes.items():
            fulfilled_kg = round(
                sum(
                    alloc_qty
                    for (s_id, target_d_id), alloc_qty in allocations_kg.items()
                    if target_d_id == d_id
                ),
                2,
            )
            unfulfilled_kg = round(max(0.0, d_node.requested_kg - fulfilled_kg), 2)

            if unfulfilled_kg <= 0:
                continue

            # Analyze reasons
            # Check all candidates evaluated for this demand
            demand_candidates = [
                c for c in problem.all_evaluated_candidates if c.demand_request_id == d_id
            ]

            eligible_candidates = [c for c in demand_candidates if c.is_eligible]
            ineligible_candidates = [c for c in demand_candidates if not c.is_eligible]

            reason_code: str
            diagnostic_explanation: str

            if not demand_candidates:
                reason_code = "NO_COMPATIBLE_SUPPLY"
                diagnostic_explanation = (
                    f"No active surplus listings in category '{d_node.food_category}' were available in the network."
                )
            elif not eligible_candidates:
                # Inspect rejection reasons from ineligible candidates
                reasons = []
                for c in ineligible_candidates:
                    reasons.extend(c.rejection_reasons)
                reasons_text = " | ".join(set(reasons)) if reasons else "Incompatible with available inventory"

                if "cold storage" in reasons_text.lower() or "cold chain" in reasons_text.lower():
                    reason_code = "COLD_CHAIN_MISMATCH"
                elif "transit" in reasons_text.lower() or "temporally infeasible" in reasons_text.lower():
                    reason_code = "TRANSIT_INFEASIBLE"
                elif "expired" in reasons_text.lower() or "deadline" in reasons_text.lower():
                    reason_code = "EXPIRED_SUPPLY"
                else:
                    reason_code = "INELIGIBLE_CANDIDATES"

                diagnostic_explanation = (
                    f"All candidate surplus listings ({len(ineligible_candidates)}) were disqualified during pre-filtering: {reasons_text}."
                )
            else:
                # Eligible candidates existed, but why wasn't demand met?
                # Check total available supply from those candidates
                total_cand_supply = sum(
                    problem.surplus_nodes[c.surplus_listing_id].available_kg
                    for c in eligible_candidates
                    if c.surplus_listing_id in problem.surplus_nodes
                )
                if total_cand_supply < d_node.requested_kg:
                    reason_code = "INSUFFICIENT_SUPPLY"
                    diagnostic_explanation = (
                        f"Eligible compatible surplus ({total_cand_supply:.2f} kg) was lower than requested intake ({d_node.requested_kg:.2f} kg)."
                    )
                else:
                    reason_code = "SUPPLY_ALLOCATED_TO_HIGHER_PRIORITY"
                    diagnostic_explanation = (
                        f"Compatible surplus inventory was routed to higher-urgency or higher-priority receiver facilities to maximize overall network impact."
                    )

            details.append(
                UnfulfilledDemandDetail(
                    demand_request_id=d_id,
                    receiver_id=d_node.receiver_id,
                    receiver_name=d_node.receiver_name,
                    food_category=d_node.food_category,
                    item_name=d_node.item_name,
                    requested_quantity_kg=d_node.requested_kg,
                    fulfilled_in_proposal_kg=fulfilled_kg,
                    unfulfilled_quantity_kg=unfulfilled_kg,
                    reason_code=reason_code,
                    diagnostic_explanation=diagnostic_explanation,
                )
            )

        return details

    @classmethod
    def diagnose_unallocated_surplus(
        cls,
        problem: AllocationProblem,
        allocations_kg: Dict[Tuple[uuid.UUID, uuid.UUID], float],
    ) -> List[UnallocatedSurplusDetail]:
        details: List[UnallocatedSurplusDetail] = []

        for s_id, s_node in problem.surplus_nodes.items():
            allocated_kg = round(
                sum(
                    alloc_qty
                    for (source_s_id, d_id), alloc_qty in allocations_kg.items()
                    if source_s_id == s_id
                ),
                2,
            )
            unallocated_kg = round(max(0.0, s_node.available_kg - allocated_kg), 2)

            if unallocated_kg <= 0:
                continue

            surplus_candidates = [
                c for c in problem.all_evaluated_candidates if c.surplus_listing_id == s_id
            ]
            eligible_candidates = [c for c in surplus_candidates if c.is_eligible]
            ineligible_candidates = [c for c in surplus_candidates if not c.is_eligible]

            reason_code: str
            diagnostic_explanation: str

            if not surplus_candidates:
                reason_code = "NO_COMPATIBLE_DEMAND"
                diagnostic_explanation = (
                    f"No open receiver demands requesting category '{s_node.food_category}' were found."
                )
            elif not eligible_candidates:
                reasons = []
                for c in ineligible_candidates:
                    reasons.extend(c.rejection_reasons)
                reasons_text = " | ".join(set(reasons)) if reasons else "Incompatible with candidate demands"
                reason_code = "INELIGIBLE_DEMANDS"
                diagnostic_explanation = f"Candidate demands were disqualified: {reasons_text}."
            else:
                reason_code = "ALL_DEMANDS_FULFILLED"
                diagnostic_explanation = (
                    "Compatible local receiver demands were already satisfied or reached capacity limits."
                )

            details.append(
                UnallocatedSurplusDetail(
                    surplus_listing_id=s_id,
                    supplier_id=s_node.supplier_id,
                    supplier_name=s_node.supplier_name,
                    food_category=s_node.food_category,
                    item_name=s_node.item_name,
                    available_quantity_kg=s_node.available_kg,
                    allocated_in_proposal_kg=allocated_kg,
                    unallocated_quantity_kg=unallocated_kg,
                    urgency=s_node.urgency,
                    reason_code=reason_code,
                    diagnostic_explanation=diagnostic_explanation,
                )
            )

        return details
