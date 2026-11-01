import uuid
import math
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Tuple, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from app.models.user import User, SupplierProfile, ReceiverProfile
from app.models.food import SurplusListing, DemandRequest
from app.models.redistribution import AllocationProposal, AllocationItem
from app.repositories.profile_repo import SupplierProfileRepository, ReceiverProfileRepository
from app.intelligence.perishability_engine import PerishabilityEngine
from app.matching.matching_service import MatchingService
from app.matching.models import CandidateMatch
from app.optimization.models import (
    OptimizationRunRequest,
    OptimizationProposalResponse,
    AllocationItemDetail,
    UnfulfilledDemandDetail,
    UnallocatedSurplusDetail,
    SolverDiagnostics,
)
from app.optimization.allocation_problem import (
    AllocationProblem,
    SurplusNode,
    DemandNode,
    EligibleEdge,
    to_hundredths_kg,
)
from app.optimization.ortools_solver import OrtoolsSolver
from app.optimization.proposal_explainer import ProposalExplainer


class AllocationService:
    """
    Orchestrates the Google OR-Tools Constrained Allocation Optimizer.
    Ingests active surplus listings and open demands from PostgreSQL, runs
    pre-filtering compatibility checks, builds mathematical CP-SAT models,
    solves for global optimal allocation, produces auditable explanations,
    and persists proposals for coordinator review.

    STRICT GUARANTEE: Never modifies surplus inventory or demand quantities.
    """

    @classmethod
    def generate_proposal(
        cls,
        db: Session,
        request: OptimizationRunRequest,
        current_user: User,
    ) -> OptimizationProposalResponse:
        # 1. Enforce RBAC: Coordinators and Admins Only
        if current_user.role not in ("COORDINATOR", "ADMIN"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only coordinators and administrators can run allocation optimization.",
            )

        now = request.evaluation_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # 2. Ingest Active Surplus Listings
        surplus_query = (
            select(SurplusListing)
            .options(joinedload(SurplusListing.supplier))
            .where(SurplusListing.status.in_(("ACTIVE", "AVAILABLE")))
            .where(SurplusListing.remaining_quantity_kg > Decimal("0.00"))
        )
        if request.surplus_listing_ids:
            surplus_query = surplus_query.where(SurplusListing.id.in_(request.surplus_listing_ids))

        listings: List[SurplusListing] = list(db.scalars(surplus_query).unique().all())

        # 3. Ingest Open Demand Requests
        demand_query = (
            select(DemandRequest)
            .options(joinedload(DemandRequest.receiver))
            .where(DemandRequest.status.in_(("OPEN", "ACTIVE", "PARTIALLY_FULFILLED")))
            .where((DemandRequest.requested_quantity_kg - DemandRequest.fulfilled_quantity_kg) > Decimal("0.00"))
        )
        if request.demand_request_ids:
            demand_query = demand_query.where(DemandRequest.id.in_(request.demand_request_ids))

        demands: List[DemandRequest] = list(db.scalars(demand_query).unique().all())

        # 4. Cache Profiles and Pre-evaluate Perishability
        suppliers_cache: Dict[uuid.UUID, SupplierProfile] = {}
        perish_eval_cache: Dict[uuid.UUID, Any] = {}
        surplus_nodes: Dict[uuid.UUID, SurplusNode] = {}

        for listing in listings:
            supplier = listing.supplier or SupplierProfileRepository.get_by_id(db, listing.supplier_id)
            if not supplier:
                continue
            suppliers_cache[listing.supplier_id] = supplier

            perish_eval = PerishabilityEngine.evaluate(
                estimated_deadline=listing.estimated_deadline,
                harvest_or_prep_date=listing.harvest_or_prep_date,
                food_condition=listing.food_condition,
                storage_condition=listing.storage_condition,
                listing_id=listing.id,
                evaluation_time=now,
            )
            perish_eval_cache[listing.id] = perish_eval

            remaining_hours = 0.0 if math.isnan(perish_eval.remaining_hours) else max(0.0, perish_eval.remaining_hours)
            is_expired = perish_eval.remaining_seconds <= 0 or remaining_hours <= 0

            # Only add to active nodes if food has not expired
            if not is_expired:
                avail_kg = float(listing.remaining_quantity_kg)
                surplus_nodes[listing.id] = SurplusNode(
                    id=listing.id,
                    supplier_id=supplier.id,
                    supplier_name=supplier.organization_name,
                    food_category=listing.food_category,
                    item_name=listing.item_name,
                    available_kg=avail_kg,
                    available_hundredths_kg=to_hundredths_kg(avail_kg),
                    urgency=perish_eval.urgency,
                    remaining_shelf_life_hours=remaining_hours,
                )

        demand_nodes: Dict[uuid.UUID, DemandNode] = {}
        receivers_cache: Dict[uuid.UUID, ReceiverProfile] = {}

        for demand in demands:
            receiver = demand.receiver or ReceiverProfileRepository.get_by_id(db, demand.receiver_id)
            if not receiver:
                continue
            receivers_cache[demand.receiver_id] = receiver

            outstanding_kg = float(demand.remaining_requirement_kg)
            if outstanding_kg > 0:
                demand_nodes[demand.id] = DemandNode(
                    id=demand.id,
                    receiver_id=receiver.id,
                    receiver_name=receiver.organization_name,
                    food_category=demand.food_category,
                    item_name=demand.item_name,
                    requested_kg=outstanding_kg,
                    requested_hundredths_kg=to_hundredths_kg(outstanding_kg),
                    priority_level=receiver.priority_level or 3,
                )

        # 5. Evaluate All Candidate Pairs
        eligible_edges: Dict[Tuple[uuid.UUID, uuid.UUID], EligibleEdge] = {}
        all_evaluated: List[CandidateMatch] = []

        for listing in listings:
            supplier = suppliers_cache.get(listing.supplier_id)
            perish_eval = perish_eval_cache.get(listing.id)
            if not supplier or not perish_eval:
                continue

            for demand in demands:
                receiver = receivers_cache.get(demand.receiver_id)
                if not receiver:
                    continue

                candidate = MatchingService.evaluate_candidate_pair(
                    listing=listing,
                    supplier=supplier,
                    demand=demand,
                    receiver=receiver,
                    evaluation_time=now,
                    perish_eval=perish_eval,
                    handling_buffer_minutes=30,
                )
                all_evaluated.append(candidate)

                # Check eligibility
                if candidate.is_eligible and candidate.eligibility == "ELIGIBLE":
                    # Check optional max distance threshold
                    if request.max_distance_km and candidate.road_distance_km > request.max_distance_km:
                        continue

                    # Ensure both nodes exist in active problem
                    if listing.id in surplus_nodes and demand.id in demand_nodes:
                        s_node = surplus_nodes[listing.id]
                        d_node = demand_nodes[demand.id]
                        max_flow = min(s_node.available_centigrams, d_node.requested_centigrams)

                        # Calculate shelf life slack in minutes
                        slack_mins = max(
                            0.0,
                            (candidate.remaining_shelf_life_hours * 60.0)
                            - (candidate.estimated_transit_minutes + candidate.handling_buffer_minutes),
                        )

                        eligible_edges[(listing.id, demand.id)] = EligibleEdge(
                            surplus_id=listing.id,
                            demand_id=demand.id,
                            max_flow_centigrams=max_flow,
                            urgency=perish_eval.urgency,
                            receiver_priority=d_node.priority_level,
                            road_distance_km=candidate.road_distance_km,
                            estimated_transit_minutes=int(round(candidate.estimated_transit_minutes)),
                            shelf_life_slack_minutes=slack_mins,
                            score=candidate.score,
                            explanation=candidate.explanation,
                            candidate_match=candidate,
                        )

        # 6. Construct Allocation Problem
        problem = AllocationProblem(
            surplus_nodes=surplus_nodes,
            demand_nodes=demand_nodes,
            eligible_edges=eligible_edges,
            all_evaluated_candidates=all_evaluated,
        )

        # 7. Solve with Google OR-Tools CP-SAT
        solver_result = OrtoolsSolver.solve(
            problem=problem,
            timeout_seconds=request.timeout_seconds,
        )

        # 8. Transform Allocations to Detailed Line Items
        allocation_items_details: List[AllocationItemDetail] = []
        for (s_id, d_id), allocated_kg in solver_result.allocations_kg.items():
            if allocated_kg > 0:
                edge = problem.eligible_edges[(s_id, d_id)]
                s_node = problem.surplus_nodes[s_id]
                d_node = problem.demand_nodes[d_id]

                item_detail = AllocationItemDetail(
                    surplus_listing_id=s_id,
                    demand_request_id=d_id,
                    supplier_id=s_node.supplier_id,
                    receiver_id=d_node.receiver_id,
                    supplier_name=s_node.supplier_name,
                    receiver_name=d_node.receiver_name,
                    item_name=s_node.item_name,
                    food_category=s_node.food_category,
                    allocated_quantity_kg=allocated_kg,
                    estimated_distance_km=edge.road_distance_km,
                    estimated_transit_minutes=edge.estimated_transit_minutes,
                    urgency_at_allocation=edge.urgency,
                    shelf_life_slack_minutes=edge.shelf_life_slack_minutes,
                    allocation_score=edge.score,
                    explanation=edge.explanation,
                )
                allocation_items_details.append(item_detail)

        # 9. Compute Summary Metrics
        total_allocated_kg = round(sum(it.allocated_quantity_kg for it in allocation_items_details), 2)
        total_unallocated_kg = round(max(0.0, problem.total_available_kg - total_allocated_kg), 2)
        total_unmet_demand_kg = round(max(0.0, problem.total_requested_kg - total_allocated_kg), 2)
        total_transit_km = round(sum(it.estimated_distance_km for it in allocation_items_details), 2)

        # 10. Generate Explanations and Unmet Demand Diagnostics
        ai_justification = ProposalExplainer.generate_justification(
            total_allocated_kg=total_allocated_kg,
            total_unallocated_kg=total_unallocated_kg,
            total_unmet_demand_kg=total_unmet_demand_kg,
            estimated_total_transit_km=total_transit_km,
            items=allocation_items_details,
            solver_status=solver_result.status,
        )

        unfulfilled_demands = ProposalExplainer.diagnose_unfulfilled_demands(
            problem=problem,
            allocations_kg=solver_result.allocations_kg,
        )

        unallocated_surplus = ProposalExplainer.diagnose_unallocated_surplus(
            problem=problem,
            allocations_kg=solver_result.allocations_kg,
        )

        diagnostics = SolverDiagnostics(
            solver_name="Google OR-Tools CP-SAT",
            solver_status=solver_result.status,
            solve_time_ms=solver_result.solve_time_ms,
            num_surplus_considered=len(listings),
            num_demands_considered=len(demands),
            num_candidate_pairs=len(all_evaluated),
            num_variables=solver_result.num_variables,
            num_constraints=solver_result.num_constraints,
            objective_value=solver_result.objective_value,
        )

        # 11. Persist AllocationProposal and AllocationItems to PostgreSQL (when total_allocated_kg > 0)
        proposal_id: Optional[uuid.UUID] = None
        created_at = datetime.now(timezone.utc)

        if total_allocated_kg > 0:
            db_proposal = AllocationProposal(
                generated_by_user_id=current_user.id,
                status="PENDING_REVIEW",
                total_allocated_kg=Decimal(str(total_allocated_kg)),
                total_unallocated_kg=Decimal(str(total_unallocated_kg)),
                total_unmet_demand_kg=Decimal(str(total_unmet_demand_kg)),
                estimated_total_transit_km=Decimal(str(total_transit_km)),
                ai_justification=ai_justification,
                solver_status=solver_result.status,
            )
            db.add(db_proposal)
            db.flush()
            proposal_id = db_proposal.id
            created_at = db_proposal.created_at or created_at

            for it in allocation_items_details:
                it.proposal_id = proposal_id
                db_item = AllocationItem(
                    proposal_id=proposal_id,
                    surplus_listing_id=it.surplus_listing_id,
                    demand_request_id=it.demand_request_id,
                    allocated_quantity_kg=Decimal(str(it.allocated_quantity_kg)),
                    estimated_distance_km=Decimal(str(it.estimated_distance_km)),
                    estimated_transit_minutes=it.estimated_transit_minutes,
                    urgency_at_allocation=it.urgency_at_allocation,
                )
                db.add(db_item)
                db.flush()
                it.item_id = db_item.id

            db.commit()

        return OptimizationProposalResponse(
            proposal_id=proposal_id,
            status="PENDING_REVIEW",
            total_allocated_kg=total_allocated_kg,
            total_unallocated_kg=total_unallocated_kg,
            total_unmet_demand_kg=total_unmet_demand_kg,
            estimated_total_transit_km=total_transit_km,
            solver_status=solver_result.status,
            solve_time_ms=solver_result.solve_time_ms,
            ai_justification=ai_justification,
            items=allocation_items_details,
            unfulfilled_demands=unfulfilled_demands,
            unallocated_surplus=unallocated_surplus,
            diagnostics=diagnostics,
            created_at=created_at,
        )

    @classmethod
    def get_proposal_by_id(
        cls,
        db: Session,
        proposal_id: uuid.UUID,
        current_user: User,
    ) -> OptimizationProposalResponse:
        """
        Retrieves a previously generated allocation proposal by ID.
        """
        if current_user.role not in ("COORDINATOR", "ADMIN"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only coordinators and administrators can view allocation proposals.",
            )

        query = (
            select(AllocationProposal)
            .options(
                joinedload(AllocationProposal.items).joinedload(AllocationItem.surplus_listing),
                joinedload(AllocationProposal.items).joinedload(AllocationItem.demand_request),
            )
            .where(AllocationProposal.id == proposal_id)
        )
        proposal = db.scalars(query).unique().first()

        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Allocation proposal not found.",
            )

        items_details: List[AllocationItemDetail] = []
        for it in proposal.items:
            s_name = it.surplus_listing.supplier_id if it.surplus_listing else "Supplier"
            d_name = it.demand_request.receiver_id if it.demand_request else "Receiver"

            items_details.append(
                AllocationItemDetail(
                    item_id=it.id,
                    proposal_id=proposal.id,
                    surplus_listing_id=it.surplus_listing_id,
                    demand_request_id=it.demand_request_id,
                    supplier_id=it.surplus_listing.supplier_id if it.surplus_listing else uuid.uuid4(),
                    receiver_id=it.demand_request.receiver_id if it.demand_request else uuid.uuid4(),
                    supplier_name=str(s_name),
                    receiver_name=str(d_name),
                    item_name=it.surplus_listing.item_name if it.surplus_listing else "Food Item",
                    food_category=it.surplus_listing.food_category if it.surplus_listing else "PRODUCE",
                    allocated_quantity_kg=float(it.allocated_quantity_kg),
                    estimated_distance_km=float(it.estimated_distance_km),
                    estimated_transit_minutes=it.estimated_transit_minutes,
                    urgency_at_allocation=it.urgency_at_allocation,
                    shelf_life_slack_minutes=None,
                    allocation_score=100.0,
                    explanation=f"Allocated {it.allocated_quantity_kg} kg via solver proposal.",
                )
            )

        diagnostics = SolverDiagnostics(
            solver_name="Google OR-Tools CP-SAT",
            solver_status=proposal.solver_status,
            solve_time_ms=0.0,
            num_surplus_considered=len(items_details),
            num_demands_considered=len(items_details),
            num_candidate_pairs=len(items_details),
            num_variables=len(items_details),
            num_constraints=len(items_details),
            objective_value=None,
        )

        return OptimizationProposalResponse(
            proposal_id=proposal.id,
            status=proposal.status,
            total_allocated_kg=float(proposal.total_allocated_kg),
            total_unallocated_kg=float(proposal.total_unallocated_kg),
            total_unmet_demand_kg=float(proposal.total_unmet_demand_kg),
            estimated_total_transit_km=float(proposal.estimated_total_transit_km or 0.0),
            solver_status=proposal.solver_status,
            solve_time_ms=0.0,
            ai_justification=proposal.ai_justification or "",
            items=items_details,
            unfulfilled_demands=[],
            unallocated_surplus=[],
            diagnostics=diagnostics,
            created_at=proposal.created_at,
        )
