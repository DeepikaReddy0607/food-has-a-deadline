import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.user import User
from app.models.food import SurplusListing, DemandRequest
from app.repositories.profile_repo import SupplierProfileRepository, ReceiverProfileRepository
from app.intelligence.perishability_engine import PerishabilityEngine
from app.geospatial.routing_service import routing_service
from app.matching.matching_service import MatchingService
from app.optimization.allocation_service import AllocationService
from app.optimization.models import OptimizationRunRequest
from app.agent.tool_registry import ToolRegistry


class ToolExecutor:
    """
    Safely executes registered deterministic tools under the authenticated user's security context.
    Strictly wraps existing backend services; never invents synthetic responses or overrides RBAC.
    """

    @classmethod
    def execute(
        cls,
        db: Session,
        current_user: User,
        tool_name: str,
        arguments: Dict[str, Any],
        call_id: str = "",
    ):
        """
        Wrapper that executes a tool and packages output as a ToolResultRecord.
        """
        from app.agent.models import ToolResultRecord

        res = cls.execute_tool(
            tool_name=tool_name,
            arguments=arguments,
            db=db,
            current_user=current_user,
        )

        if isinstance(res, dict) and "error" in res:
            return ToolResultRecord(
                call_id=call_id,
                tool_name=tool_name,
                output={},
                success=False,
                error=res["error"],
            )

        return ToolResultRecord(
            call_id=call_id,
            tool_name=tool_name,
            output=res if isinstance(res, dict) else {"result": res},
            success=True,
            error=None,
        )

    @classmethod
    def execute_tool(
        cls,
        tool_name: str,
        arguments: Dict[str, Any],
        db: Session,
        current_user: User,
    ) -> Dict[str, Any]:
        """
        Executes a registered tool after verifying authorization.
        Returns a structured dictionary representing the tool output.
        """
        # 1. Verify Tool Existence
        meta = ToolRegistry.get_tool_metadata(tool_name)
        if not meta:
            return {"error": f"Unknown tool '{tool_name}'."}

        # 2. Enforce Role-Based Access Control (RBAC)
        if not ToolRegistry.is_authorized(tool_name, current_user.role):
            return {
                "error": f"Authorization Denied: Role '{current_user.role}' is not permitted to execute tool '{tool_name}'."
            }

        # 3. Dispatch to Specific Service Wrapper
        try:
            handler = getattr(cls, f"_tool_{tool_name}", None)
            if not handler:
                return {"error": f"Execution handler for tool '{tool_name}' is not implemented."}
            return handler(arguments=arguments, db=db, current_user=current_user)
        except Exception as ex:
            return {"error": f"Tool execution failed: {str(ex)}"}

    # -------------------------------------------------------------------------
    # Tool 1: get_available_surplus
    # -------------------------------------------------------------------------
    @classmethod
    def _tool_get_available_surplus(
        cls, arguments: Dict[str, Any], db: Session, current_user: User
    ) -> Dict[str, Any]:
        category = arguments.get("category")
        limit = min(int(arguments.get("limit", 20)), 100)

        query = (
            select(SurplusListing)
            .where(SurplusListing.status.in_(("ACTIVE", "AVAILABLE")))
            .where(SurplusListing.remaining_quantity_kg > Decimal("0.00"))
        )

        # Tenant isolation for SUPPLIERS
        if current_user.role == "SUPPLIER":
            profile = SupplierProfileRepository.get_by_user_id(db, current_user.id)
            if not profile:
                return {"total_found": 0, "listings": [], "notice": "Supplier profile incomplete."}
            query = query.where(SurplusListing.supplier_id == profile.id)

        if category:
            query = query.where(SurplusListing.food_category == category.upper())

        query = query.order_by(SurplusListing.estimated_deadline.asc()).limit(limit)
        listings = list(db.scalars(query).all())

        items_list = [
            {
                "id": str(it.id),
                "supplier_id": str(it.supplier_id),
                "food_category": it.food_category,
                "item_name": it.item_name,
                "title": it.item_name,
                "remaining_quantity_kg": float(it.remaining_quantity_kg),
                "quantity_kg": float(it.remaining_quantity_kg),
                "storage_condition": it.storage_condition,
                "food_condition": it.food_condition,
                "estimated_deadline": it.estimated_deadline.isoformat(),
                "urgency_classification": it.urgency_classification,
                "pickup_address": it.pickup_address,
            }
            for it in listings
        ]

        return {
            "total_found": len(listings),
            "total_count": len(listings),
            "listings": items_list,
            "items": items_list,
        }

    # -------------------------------------------------------------------------
    # Tool 2: get_active_demand
    # -------------------------------------------------------------------------
    @classmethod
    def _tool_get_active_demand(
        cls, arguments: Dict[str, Any], db: Session, current_user: User
    ) -> Dict[str, Any]:
        category = arguments.get("category")
        min_prio = arguments.get("min_priority")
        limit = min(int(arguments.get("limit", 20)), 100)

        query = (
            select(DemandRequest)
            .where(DemandRequest.status.in_(("OPEN", "ACTIVE", "PARTIALLY_FULFILLED")))
            .where((DemandRequest.requested_quantity_kg - DemandRequest.fulfilled_quantity_kg) > Decimal("0.00"))
        )

        # Tenant isolation for RECEIVERS
        if current_user.role == "RECEIVER":
            profile = ReceiverProfileRepository.get_by_user_id(db, current_user.id)
            if not profile:
                return {"total_found": 0, "total_count": 0, "demands": [], "items": [], "notice": "Receiver profile incomplete."}
            query = query.where(DemandRequest.receiver_id == profile.id)

        if category:
            query = query.where(DemandRequest.food_category == category.upper())
        if min_prio is not None:
            query = query.where(DemandRequest.priority_weight >= int(min_prio))

        query = query.order_by(DemandRequest.required_by.asc()).limit(limit)
        demands = list(db.scalars(query).all())

        demand_items = [
            {
                "id": str(d.id),
                "receiver_id": str(d.receiver_id),
                "food_category": d.food_category,
                "item_name": d.item_name,
                "title": d.item_name or d.food_category,
                "requested_quantity_kg": float(d.requested_quantity_kg),
                "unfulfilled_quantity_kg": float(d.remaining_requirement_kg),
                "quantity_kg": float(d.remaining_requirement_kg),
                "storage_capability": d.storage_capability,
                "required_by": d.required_by.isoformat(),
                "priority_weight": d.priority_weight,
                "priority": d.priority_weight,
                "dietary_requirements": d.dietary_requirements or [],
            }
            for d in demands
        ]

        return {
            "total_found": len(demands),
            "total_count": len(demands),
            "demands": demand_items,
            "items": demand_items,
        }

    # -------------------------------------------------------------------------
    # Tool 3: calculate_urgency
    # -------------------------------------------------------------------------
    @classmethod
    def _tool_calculate_urgency(
        cls, arguments: Dict[str, Any], db: Session, current_user: User
    ) -> Dict[str, Any]:
        deadline_str = arguments.get("estimated_deadline")
        if not deadline_str:
            return {"error": "Parameter 'estimated_deadline' is required."}

        try:
            deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
        except Exception:
            return {"error": "Invalid ISO 8601 timestamp in 'estimated_deadline'."}

        prep_date = None
        prep_str = arguments.get("harvest_or_prep_date")
        if prep_str:
            try:
                prep_date = datetime.fromisoformat(prep_str.replace("Z", "+00:00"))
            except Exception:
                pass

        eval_result = PerishabilityEngine.evaluate(
            estimated_deadline=deadline,
            harvest_or_prep_date=prep_date,
            food_condition=arguments.get("food_condition", "GOOD"),
            storage_condition=arguments.get("storage_condition", "AMBIENT"),
        )

        return {
            "urgency_classification": eval_result.urgency,
            "remaining_hours": round(eval_result.remaining_hours, 2),
            "effective_usable_hours": round(eval_result.remaining_hours, 2),
            "remaining_seconds": eval_result.remaining_seconds,
            "data_quality": eval_result.data_quality,
            "data_confidence": eval_result.data_quality,
            "warnings": eval_result.warnings,
            "warning_flags": eval_result.warnings,
            "explanation": eval_result.explanation,
            "factors": eval_result.factors,
        }

    # -------------------------------------------------------------------------
    # Tool 4: find_compatible_receivers
    # -------------------------------------------------------------------------
    @classmethod
    def _tool_find_compatible_receivers(
        cls, arguments: Dict[str, Any], db: Session, current_user: User
    ) -> Dict[str, Any]:
        listing_id_str = arguments.get("listing_id")
        if not listing_id_str:
            return {"error": "Parameter 'listing_id' is required."}

        try:
            listing_id = uuid.UUID(listing_id_str)
        except Exception:
            return {"error": "Invalid UUID for 'listing_id'."}

        include_ineligible = bool(arguments.get("include_ineligible", False))

        res = MatchingService.find_candidates_for_listing(
            db=db,
            listing_id=listing_id,
            current_user=current_user,
            page=1,
            page_size=20,
            include_ineligible=include_ineligible,
        )

        return {
            "source_id": str(res.source_id),
            "source_name": res.source_name,
            "total_candidates": res.total_candidates,
            "eligible_count": res.eligible_count,
            "ineligible_count": res.ineligible_count,
            "candidates": [
                {
                    "receiver_id": str(c.receiver_id),
                    "receiver_name": c.receiver_name,
                    "eligibility": c.eligibility,
                    "is_eligible": c.is_eligible,
                    "score": c.score,
                    "rejection_reasons": c.rejection_reasons,
                    "road_distance_km": c.road_distance_km,
                    "estimated_transit_minutes": c.estimated_transit_minutes,
                    "transit_feasibility": c.transit_feasibility,
                    "explanation": c.explanation,
                }
                for c in res.candidates
            ],
        }

    # -------------------------------------------------------------------------
    # Tool 5: find_compatible_surplus
    # -------------------------------------------------------------------------
    @classmethod
    def _tool_find_compatible_surplus(
        cls, arguments: Dict[str, Any], db: Session, current_user: User
    ) -> Dict[str, Any]:
        demand_id_str = arguments.get("demand_id")
        if not demand_id_str:
            return {"error": "Parameter 'demand_id' is required."}

        try:
            demand_id = uuid.UUID(demand_id_str)
        except Exception:
            return {"error": "Invalid UUID for 'demand_id'."}

        include_ineligible = bool(arguments.get("include_ineligible", False))

        res = MatchingService.find_candidates_for_demand(
            db=db,
            demand_id=demand_id,
            current_user=current_user,
            page=1,
            page_size=20,
            include_ineligible=include_ineligible,
        )

        return {
            "source_id": str(res.source_id),
            "source_name": res.source_name,
            "total_candidates": res.total_candidates,
            "eligible_count": res.eligible_count,
            "ineligible_count": res.ineligible_count,
            "candidates": [
                {
                    "surplus_listing_id": str(c.surplus_listing_id),
                    "supplier_name": c.supplier_name,
                    "item_name": c.item_name,
                    "eligibility": c.eligibility,
                    "is_eligible": c.is_eligible,
                    "score": c.score,
                    "rejection_reasons": c.rejection_reasons,
                    "road_distance_km": c.road_distance_km,
                    "estimated_transit_minutes": c.estimated_transit_minutes,
                    "transit_feasibility": c.transit_feasibility,
                    "explanation": c.explanation,
                }
                for c in res.candidates
            ],
        }

    # -------------------------------------------------------------------------
    # Tool 6: calculate_route
    # -------------------------------------------------------------------------
    @classmethod
    def _tool_calculate_route(
        cls, arguments: Dict[str, Any], db: Session, current_user: User
    ) -> Dict[str, Any]:
        try:
            s_lat = float(arguments.get("supplier_lat") or arguments.get("origin_lat"))
            s_lon = float(arguments.get("supplier_lon") or arguments.get("origin_lon"))
            r_lat = float(arguments.get("receiver_lat") or arguments.get("dest_lat"))
            r_lon = float(arguments.get("receiver_lon") or arguments.get("dest_lon"))
        except (TypeError, KeyError, ValueError):
            return {"error": "Valid supplier and receiver latitude/longitude coordinates are required."}

        deadline = None
        dl_str = arguments.get("usable_deadline")
        if dl_str:
            try:
                deadline = datetime.fromisoformat(dl_str.replace("Z", "+00:00"))
            except Exception:
                pass

        sup_id = None
        if arguments.get("supplier_id"):
            try:
                sup_id = uuid.UUID(str(arguments["supplier_id"]))
            except Exception:
                pass

        rec_id = None
        if arguments.get("receiver_id"):
            try:
                rec_id = uuid.UUID(str(arguments["receiver_id"]))
            except Exception:
                pass

        route = routing_service.estimate_route(
            supplier_id=sup_id or uuid.uuid4(),
            receiver_id=rec_id or uuid.uuid4(),
            supplier_lat=s_lat,
            supplier_lon=s_lon,
            dest_lat=r_lat,
            dest_lon=r_lon,
            estimated_usable_deadline=deadline,
            handling_buffer_minutes=int(arguments.get("handling_buffer_minutes", 30)),
        )

        return {
            "straight_line_distance_km": route.straight_line_distance_km,
            "road_distance_km": route.road_distance_km,
            "estimated_travel_minutes": route.estimated_travel_minutes,
            "estimated_duration_minutes": route.estimated_travel_minutes,
            "routing_provider": route.routing_provider,
            "is_fallback": route.is_fallback,
            "feasibility": route.feasibility,
            "available_minutes": route.available_minutes,
            "required_minutes": route.required_minutes,
            "warnings": route.warnings,
        }

    # -------------------------------------------------------------------------
    # Tool 7 & 10: run_allocation_optimizer & prepare_redistribution_proposal
    # -------------------------------------------------------------------------
    @classmethod
    def _tool_run_allocation_optimizer(
        cls, arguments: Dict[str, Any], db: Session, current_user: User
    ) -> Dict[str, Any]:
        s_ids = None
        if arguments.get("surplus_listing_ids"):
            try:
                s_ids = [uuid.UUID(x) for x in arguments["surplus_listing_ids"]]
            except Exception:
                return {"error": "Invalid UUID in surplus_listing_ids."}

        d_ids = None
        if arguments.get("demand_request_ids"):
            try:
                d_ids = [uuid.UUID(x) for x in arguments["demand_request_ids"]]
            except Exception:
                return {"error": "Invalid UUID in demand_request_ids."}

        req = OptimizationRunRequest(
            surplus_listing_ids=s_ids,
            demand_request_ids=d_ids,
            timeout_seconds=float(arguments.get("timeout_seconds", 5.0)),
            max_distance_km=float(arguments["max_distance_km"]) if arguments.get("max_distance_km") else None,
        )

        proposal = AllocationService.generate_proposal(
            db=db,
            request=req,
            current_user=current_user,
        )

        return {
            "proposal_id": str(proposal.proposal_id) if proposal.proposal_id else None,
            "status": proposal.status,
            "banner": "DRAFT PROPOSAL — AWAITING HUMAN APPROVAL",
            "solver_status": proposal.solver_status,
            "total_allocated_kg": proposal.total_allocated_kg,
            "total_unallocated_kg": proposal.total_unallocated_kg,
            "total_unmet_demand_kg": proposal.total_unmet_demand_kg,
            "estimated_total_transit_km": proposal.estimated_total_transit_km,
            "solve_time_ms": proposal.solve_time_ms,
            "justification": proposal.ai_justification,
            "items_count": len(proposal.items),
            "unfulfilled_demands_count": len(proposal.unfulfilled_demands),
            "summary": {
                "solver_status": proposal.solver_status,
                "total_allocated_kg": proposal.total_allocated_kg,
                "total_unallocated_kg": proposal.total_unallocated_kg,
                "total_unmet_demand_kg": proposal.total_unmet_demand_kg,
                "total_allocation_count": len(proposal.items),
            },
            "allocations": [
                {
                    "surplus_listing_id": str(item.surplus_listing_id),
                    "demand_request_id": str(item.demand_request_id),
                    "allocated_quantity_kg": item.allocated_quantity_kg,
                }
                for item in proposal.items
            ],
            "notice": "This is a draft proposal only. Human coordinator authorization is required to commit redistribution.",
        }

    @classmethod
    def _tool_prepare_redistribution_proposal(
        cls, arguments: Dict[str, Any], db: Session, current_user: User
    ) -> Dict[str, Any]:
        return cls._tool_run_allocation_optimizer(arguments, db, current_user)

    # -------------------------------------------------------------------------
    # Tool 8: explain_allocation
    # -------------------------------------------------------------------------
    @classmethod
    def _tool_explain_allocation(
        cls, arguments: Dict[str, Any], db: Session, current_user: User
    ) -> Dict[str, Any]:
        p_id_str = arguments.get("proposal_id")
        if not p_id_str:
            return {"error": "Parameter 'proposal_id' is required."}

        try:
            proposal_id = uuid.UUID(p_id_str)
        except Exception:
            return {"error": "Invalid UUID in proposal_id."}

        proposal = AllocationService.get_proposal_by_id(
            db=db,
            proposal_id=proposal_id,
            current_user=current_user,
        )

        return {
            "proposal_id": str(proposal.proposal_id),
            "solver_status": proposal.solver_status,
            "total_allocated_kg": proposal.total_allocated_kg,
            "ai_justification": proposal.ai_justification,
            "items": [
                {
                    "item_name": it.item_name,
                    "category": it.food_category,
                    "allocated_kg": it.allocated_quantity_kg,
                    "supplier": it.supplier_name,
                    "receiver": it.receiver_name,
                    "urgency": it.urgency_at_allocation,
                    "distance_km": it.estimated_distance_km,
                    "explanation": it.explanation,
                }
                for it in proposal.items
            ],
        }

    # -------------------------------------------------------------------------
    # Tool 9: get_allocation_proposal
    # -------------------------------------------------------------------------
    @classmethod
    def _tool_get_allocation_proposal(
        cls, arguments: Dict[str, Any], db: Session, current_user: User
    ) -> Dict[str, Any]:
        p_id_str = arguments.get("proposal_id")
        if not p_id_str:
            return {"error": "Parameter 'proposal_id' is required."}

        try:
            proposal_id = uuid.UUID(p_id_str)
        except Exception:
            return {"error": "Invalid UUID in proposal_id."}

        proposal = AllocationService.get_proposal_by_id(
            db=db,
            proposal_id=proposal_id,
            current_user=current_user,
        )

        return {
            "proposal_id": str(proposal.proposal_id),
            "status": proposal.status,
            "banner": "DRAFT PROPOSAL — AWAITING HUMAN APPROVAL",
            "solver_status": proposal.solver_status,
            "total_allocated_kg": proposal.total_allocated_kg,
            "total_unallocated_kg": proposal.total_unallocated_kg,
            "total_unmet_demand_kg": proposal.total_unmet_demand_kg,
            "estimated_total_transit_km": proposal.estimated_total_transit_km,
            "items": [
                {
                    "item_name": it.item_name,
                    "food_category": it.food_category,
                    "allocated_quantity_kg": it.allocated_quantity_kg,
                    "supplier_name": it.supplier_name,
                    "receiver_name": it.receiver_name,
                    "urgency_at_allocation": it.urgency_at_allocation,
                    "estimated_distance_km": it.estimated_distance_km,
                    "estimated_transit_minutes": it.estimated_transit_minutes,
                }
                for it in proposal.items
            ],
            "justification": proposal.ai_justification,
        }
