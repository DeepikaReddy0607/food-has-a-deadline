import uuid
import math
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Tuple, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from app.models.user import User, SupplierProfile, ReceiverProfile
from app.models.food import SurplusListing, DemandRequest
from app.repositories.surplus_repo import SurplusRepository
from app.repositories.demand_repo import DemandRepository
from app.repositories.profile_repo import SupplierProfileRepository, ReceiverProfileRepository
from app.intelligence.perishability_engine import PerishabilityEngine
from app.core.config import settings
from app.geospatial.distance_calculator import (
    haversine_distance,
    approximate_road_distance,
    approximate_travel_duration_minutes,
)
from app.geospatial.routing_service import routing_service
from app.matching.models import (
    CandidateMatch,
    MatchingQueryResponse,
    EligibilityStatus,
)
from app.matching.product_compatibility import ProductCompatibilityEvaluator
from app.matching.storage_compatibility import StorageCompatibilityEvaluator
from app.matching.quantity_compatibility import QuantityCompatibilityEvaluator
from app.matching.candidate_ranker import CandidateRanker
from app.matching.explanation_builder import ExplanationBuilder


class MatchingService:
    """
    Deterministic, explainable Multi-Factor Matching Engine.
    Evaluates compatibility between surplus food listings and receiver demand requests
    using PostgreSQL records, perishability intelligence, and geospatial routing.
    Strictly read-only: never reserves quantities, modifies inventory, or commits transactions.
    """

    @classmethod
    def evaluate_candidate_pair(
        cls,
        listing: SurplusListing,
        supplier: SupplierProfile,
        demand: DemandRequest,
        receiver: ReceiverProfile,
        evaluation_time: Optional[datetime] = None,
        perish_eval: Optional[Any] = None,
        handling_buffer_minutes: int = 30,
    ) -> CandidateMatch:
        """
        Deterministically evaluates compatibility, perishability, route viability,
        eligibility status, scoring, and explanations for a single (surplus, demand) pair.
        """
        now = evaluation_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # 1. Perishability
        if perish_eval is None:
            perish_eval = PerishabilityEngine.evaluate(
                estimated_deadline=listing.estimated_deadline,
                harvest_or_prep_date=listing.harvest_or_prep_date,
                food_condition=listing.food_condition,
                storage_condition=listing.storage_condition,
                listing_id=listing.id,
                evaluation_time=now,
            )

        remaining_hours = (
            0.0 if math.isnan(perish_eval.remaining_hours) else max(0.0, perish_eval.remaining_hours)
        )
        is_food_expired = perish_eval.remaining_seconds <= 0 or remaining_hours <= 0

        rejection_reasons: List[str] = []
        warnings: List[str] = []

        # Check Hard Constraint 1: Food Not Expired
        if is_food_expired:
            rejection_reasons.append("Food has passed its usable cut-off deadline")

        # Check Hard Constraint 2: Surplus Listing Active with Stock
        if listing.status not in ("ACTIVE", "AVAILABLE"):
            rejection_reasons.append(f"Listing status '{listing.status}' is not active")
        if listing.remaining_quantity_kg <= Decimal("0.00"):
            rejection_reasons.append("Surplus inventory has zero remaining quantity")

        # Check Hard Constraint 3: Demand Open
        d_out = float(demand.remaining_requirement_kg)
        if d_out <= 0:
            rejection_reasons.append("Demand request has zero outstanding requirement")

        # Check Hard Constraint: Verified Organization
        s_ver = getattr(supplier, "verification_status", "VERIFIED")
        if s_ver != "VERIFIED":
            rejection_reasons.append(f"Supplier organization is not verified (status: '{s_ver}')")
        r_ver = getattr(receiver, "verification_status", "VERIFIED")
        if r_ver != "VERIFIED":
            rejection_reasons.append(f"Receiver organization is not verified (status: '{r_ver}')")

        # Check Hard Constraint 4: Product Compatibility
        prod_comp = ProductCompatibilityEvaluator.evaluate(
            surplus_category=listing.food_category,
            surplus_item_name=listing.item_name,
            surplus_condition=listing.food_condition,
            surplus_description=listing.description,
            demand_category=demand.food_category,
            demand_item_name=demand.item_name,
            acceptable_condition=demand.acceptable_food_condition,
            dietary_requirements=demand.dietary_requirements,
        )
        warnings.extend(prod_comp.warnings)
        if not prod_comp.is_compatible:
            rejection_reasons.append(f"Product mismatch: {prod_comp.notes}")

        # Check Hard Constraint 5: Storage Compatibility
        stor_comp = StorageCompatibilityEvaluator.evaluate(
            surplus_storage=listing.storage_condition,
            demand_storage=demand.storage_capability,
            receiver_cold_storage=receiver.cold_storage_capabilities,
        )
        warnings.extend(stor_comp.warnings)
        if not stor_comp.is_compatible:
            rejection_reasons.append(f"Storage mismatch: {stor_comp.notes}")

        # Check Hard Constraint 6: Quantity Compatibility
        qty_comp = QuantityCompatibilityEvaluator.evaluate(
            surplus_remaining_kg=listing.remaining_quantity_kg,
            demand_requested_kg=demand.requested_quantity_kg,
            demand_fulfilled_kg=demand.fulfilled_quantity_kg,
        )
        if not qty_comp.is_compatible:
            rejection_reasons.append(f"Quantity issue: {qty_comp.notes}")

        # Check Hard Constraint 7: Geospatial Feasibility & Route
        has_supplier_coords = supplier.latitude is not None and supplier.longitude is not None
        s_lat = float(supplier.latitude) if has_supplier_coords else None
        s_lon = float(supplier.longitude) if has_supplier_coords else None

        has_receiver_coords = receiver.latitude is not None and receiver.longitude is not None
        r_lat = float(receiver.latitude) if has_receiver_coords else None
        r_lon = float(receiver.longitude) if has_receiver_coords else None

        straight_km = 0.0
        road_km = 0.0
        transit_mins = 0.0
        routing_provider = "HAVERSINE_FALLBACK"
        is_route_fallback = True
        transit_feasibility = "UNKNOWN"
        avail_mins: Optional[float] = None
        req_mins: Optional[float] = None

        if not has_supplier_coords or not has_receiver_coords:
            warnings.append("Facility location coordinates missing; geospatial feasibility cannot be evaluated.")
            transit_feasibility = "UNKNOWN"
        elif len(rejection_reasons) > 0:
            # DEF-FE-002: Cheap compatibility filters failed (category, storage, condition, quantity, or deadline).
            # Avoid sequential OSRM requests for ineligible pairs; calculate deterministic Haversine approximation.
            straight_km = haversine_distance(s_lat, s_lon, r_lat, r_lon)
            road_km = approximate_road_distance(straight_km, settings.DEFAULT_CIRCUITY_FACTOR)
            transit_mins = approximate_travel_duration_minutes(road_km, settings.DEFAULT_AVERAGE_SPEED_KMH)
            routing_provider = "HAVERSINE_FALLBACK"
            is_route_fallback = True
            transit_feasibility = "UNKNOWN"
            warnings.append("Road routing query skipped: candidate rejected by deterministic compatibility filters.")
        else:
            route_res = routing_service.estimate_route(
                supplier_id=supplier.id,
                receiver_id=receiver.id,
                supplier_lat=s_lat,
                supplier_lon=s_lon,
                dest_lat=r_lat,
                dest_lon=r_lon,
                estimated_usable_deadline=listing.estimated_deadline,
                handling_buffer_minutes=handling_buffer_minutes,
                supplier_name=supplier.organization_name,
                receiver_name=receiver.organization_name,
                evaluation_time=now,
            )
            straight_km = route_res.straight_line_distance_km
            road_km = route_res.road_distance_km
            transit_mins = route_res.estimated_travel_minutes
            routing_provider = route_res.routing_provider
            is_route_fallback = route_res.is_fallback
            transit_feasibility = route_res.feasibility
            avail_mins = route_res.available_minutes
            req_mins = route_res.required_minutes
            warnings.extend(route_res.warnings)

            if transit_feasibility == "INFEASIBLE":
                rejection_reasons.append(
                    f"Temporally infeasible: transit duration + buffer ({req_mins}m) exceeds remaining shelf life ({avail_mins}m)"
                )

        # Determine Overall Eligibility
        eligibility: EligibilityStatus
        is_eligible: bool

        if len(rejection_reasons) > 0:
            eligibility = "INELIGIBLE"
            is_eligible = False
        elif prod_comp.match_level == "AMBIGUOUS" or stor_comp.match_level == "UNKNOWN" or transit_feasibility == "UNKNOWN":
            eligibility = "REVIEW_REQUIRED"
            is_eligible = False
            rejection_reasons.append("Data uncertainty or product ambiguity requires coordinator review")
        else:
            eligibility = "ELIGIBLE"
            is_eligible = True

        # Calculate Deterministic Score Breakdown
        score_breakdown = CandidateRanker.calculate_score(
            is_eligible=is_eligible,
            urgency=perish_eval.urgency,
            remaining_hours=remaining_hours,
            road_distance_km=road_km,
            transit_feasibility=transit_feasibility,
            available_minutes=avail_mins,
            required_minutes=req_mins,
            surplus_available_kg=float(listing.remaining_quantity_kg),
            demand_outstanding_kg=d_out,
            receiver_priority=receiver.priority_level or 3,
        )

        # Build Deterministic Explanation
        explanation = ExplanationBuilder.build(
            eligibility=eligibility,
            is_eligible=is_eligible,
            rejection_reasons=rejection_reasons,
            product=prod_comp,
            storage=stor_comp,
            quantity=qty_comp,
            perishability_urgency=perish_eval.urgency,
            remaining_hours=remaining_hours,
            transit_feasibility=transit_feasibility,
            road_distance_km=road_km,
            estimated_transit_minutes=transit_mins,
            is_route_fallback=is_route_fallback,
            total_score=score_breakdown.total_score,
        )

        return CandidateMatch(
            surplus_listing_id=listing.id,
            demand_request_id=demand.id,
            supplier_id=supplier.id,
            receiver_id=receiver.id,
            supplier_name=supplier.organization_name,
            receiver_name=receiver.organization_name,
            item_name=demand.item_name or demand.food_category,
            food_category=demand.food_category,
            eligibility=eligibility,
            is_eligible=is_eligible,
            rejection_reasons=rejection_reasons,
            product_compatibility=prod_comp,
            quantity_compatibility=qty_comp,
            storage_compatibility=stor_comp,
            perishability_urgency=perish_eval.urgency,
            remaining_shelf_life_hours=remaining_hours,
            transit_feasibility=transit_feasibility,
            straight_line_distance_km=straight_km,
            road_distance_km=road_km,
            estimated_transit_minutes=transit_mins,
            handling_buffer_minutes=handling_buffer_minutes,
            routing_provider=routing_provider,
            is_route_fallback=is_route_fallback,
            receiver_priority=receiver.priority_level or 3,
            receiver_category=receiver.receiver_category,
            score=score_breakdown.total_score,
            score_breakdown=score_breakdown,
            warnings=list(set(warnings)),
            explanation=explanation,
            evaluated_at=now,
        )

    @classmethod
    def find_candidates_for_listing(
        cls,
        db: Session,
        listing_id: uuid.UUID,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
        include_ineligible: bool = False,
        evaluation_time: Optional[datetime] = None,
    ) -> MatchingQueryResponse:
        now = evaluation_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # 1. Fetch Surplus Listing
        listing = SurplusRepository.get_by_id(db, listing_id)
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surplus listing not found.",
            )

        # 2. Authorization & Tenant Isolation
        if current_user.role == "SUPPLIER":
            supplier_profile = SupplierProfileRepository.get_by_user_id(db, current_user.id)
            if not supplier_profile or listing.supplier_id != supplier_profile.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Surplus listing not found.",
                )
        elif current_user.role not in ("COORDINATOR", "ADMIN"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Receivers cannot query surplus candidate matches directly; browse active listings instead.",
            )

        # 3. Fetch Supplier Profile & Facility Coordinates
        supplier = SupplierProfileRepository.get_by_id(db, listing.supplier_id)
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supplier profile for this listing does not exist.",
            )

        has_supplier_coords = supplier.latitude is not None and supplier.longitude is not None
        s_lat = float(supplier.latitude) if has_supplier_coords else None
        s_lon = float(supplier.longitude) if has_supplier_coords else None

        # 4. Perishability Evaluation
        perish_eval = PerishabilityEngine.evaluate(
            estimated_deadline=listing.estimated_deadline,
            harvest_or_prep_date=listing.harvest_or_prep_date,
            food_condition=listing.food_condition,
            storage_condition=listing.storage_condition,
            listing_id=listing.id,
            evaluation_time=now,
        )

        remaining_hours = (
            0.0 if math.isnan(perish_eval.remaining_hours) else max(0.0, perish_eval.remaining_hours)
        )
        is_food_expired = perish_eval.remaining_seconds <= 0 or remaining_hours <= 0

        # 5. Query Active / Open Demands from PostgreSQL
        demands_query = (
            select(DemandRequest)
            .options(joinedload(DemandRequest.receiver))
            .where(DemandRequest.status.in_(("OPEN", "ACTIVE", "PARTIALLY_FULFILLED")))
            .where((DemandRequest.requested_quantity_kg - DemandRequest.fulfilled_quantity_kg) > Decimal("0.00"))
        )
        demands = list(db.scalars(demands_query).unique().all())

        candidates: List[CandidateMatch] = []

        # 6. Evaluate Each Demand
        for demand in demands:
            receiver = demand.receiver or ReceiverProfileRepository.get_by_id(db, demand.receiver_id)
            if not receiver:
                continue

            candidate = cls.evaluate_candidate_pair(
                listing=listing,
                supplier=supplier,
                demand=demand,
                receiver=receiver,
                evaluation_time=now,
                perish_eval=perish_eval,
                handling_buffer_minutes=30,
            )
            candidates.append(candidate)

        # 7. Sorting & Ranking
        # Priority order: ELIGIBLE (sorted by score desc) -> REVIEW_REQUIRED -> INELIGIBLE
        eligible_candidates = sorted(
            [c for c in candidates if c.eligibility == "ELIGIBLE"],
            key=lambda c: c.score,
            reverse=True,
        )
        review_candidates = sorted(
            [c for c in candidates if c.eligibility == "REVIEW_REQUIRED"],
            key=lambda c: (c.score_breakdown.urgency_score + c.score_breakdown.proximity_score),
            reverse=True,
        )
        ineligible_candidates = [c for c in candidates if c.eligibility == "INELIGIBLE"]

        all_ranked = eligible_candidates + review_candidates + ineligible_candidates

        # Filter if include_ineligible is False
        if not include_ineligible:
            final_list = eligible_candidates + review_candidates
        else:
            final_list = all_ranked

        total_count = len(final_list)
        offset = (page - 1) * page_size
        paginated_candidates = final_list[offset : offset + page_size]

        return MatchingQueryResponse(
            source_type="SURPLUS_LISTING",
            source_id=listing.id,
            source_name=listing.item_name,
            total_candidates=total_count,
            eligible_count=len(eligible_candidates),
            ineligible_count=len(ineligible_candidates),
            review_required_count=len(review_candidates),
            page=page,
            page_size=page_size,
            candidates=paginated_candidates,
        )

    @classmethod
    def find_candidates_for_demand(
        cls,
        db: Session,
        demand_id: uuid.UUID,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
        include_ineligible: bool = False,
        evaluation_time: Optional[datetime] = None,
    ) -> MatchingQueryResponse:
        now = evaluation_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # 1. Fetch Demand Request
        demand = DemandRepository.get_by_id(db, demand_id)
        if not demand:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Demand request not found.",
            )

        # 2. Authorization & Tenant Isolation
        if current_user.role == "RECEIVER":
            receiver_profile = ReceiverProfileRepository.get_by_user_id(db, current_user.id)
            if not receiver_profile or demand.receiver_id != receiver_profile.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Demand request not found.",
                )
        elif current_user.role not in ("COORDINATOR", "ADMIN"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Suppliers cannot query demand candidate matches directly; view surplus candidates instead.",
            )

        # 3. Fetch Receiver Profile & Coordinates
        receiver = ReceiverProfileRepository.get_by_id(db, demand.receiver_id)
        if not receiver:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Receiver profile for this demand does not exist.",
            )

        has_receiver_coords = receiver.latitude is not None and receiver.longitude is not None
        r_lat = float(receiver.latitude) if has_receiver_coords else None
        r_lon = float(receiver.longitude) if has_receiver_coords else None

        # 4. Check Demand Status
        d_out = float(demand.remaining_requirement_kg)
        is_demand_closed = demand.status not in ("OPEN", "ACTIVE", "PARTIALLY_FULFILLED") or d_out <= 0

        # 5. Query Active Surplus Listings from PostgreSQL
        listings_query = (
            select(SurplusListing)
            .options(joinedload(SurplusListing.supplier))
            .where(SurplusListing.status.in_(("ACTIVE", "AVAILABLE")))
            .where(SurplusListing.remaining_quantity_kg > Decimal("0.00"))
        )
        listings = list(db.scalars(listings_query).unique().all())

        candidates: List[CandidateMatch] = []

        # 6. Evaluate Each Listing
        for listing in listings:
            supplier = listing.supplier or SupplierProfileRepository.get_by_id(db, listing.supplier_id)
            if not supplier:
                continue

            rejection_reasons: List[str] = []
            warnings: List[str] = []

            # Check Hard Constraint 1: Demand Active with Outstanding Need
            if is_demand_closed:
                rejection_reasons.append("Demand request is already closed or fully fulfilled")

            # Check Hard Constraint 2: Listing Active with Stock
            if listing.status not in ("ACTIVE", "AVAILABLE"):
                rejection_reasons.append(f"Listing status '{listing.status}' is not active")
            if listing.remaining_quantity_kg <= Decimal("0.00"):
                rejection_reasons.append("Surplus inventory has zero remaining quantity")

            # Perishability Evaluation of Listing
            perish_eval = PerishabilityEngine.evaluate(
                estimated_deadline=listing.estimated_deadline,
                harvest_or_prep_date=listing.harvest_or_prep_date,
                food_condition=listing.food_condition,
                storage_condition=listing.storage_condition,
                listing_id=listing.id,
                evaluation_time=now,
            )
            remaining_hours = (
                0.0 if math.isnan(perish_eval.remaining_hours) else max(0.0, perish_eval.remaining_hours)
            )
            is_food_expired = perish_eval.remaining_seconds <= 0 or remaining_hours <= 0
            if is_food_expired:
                rejection_reasons.append("Food has passed its usable cut-off deadline")

            # Check Hard Constraint 3: Product Compatibility
            prod_comp = ProductCompatibilityEvaluator.evaluate(
                surplus_category=listing.food_category,
                surplus_item_name=listing.item_name,
                surplus_condition=listing.food_condition,
                surplus_description=listing.description,
                demand_category=demand.food_category,
                demand_item_name=demand.item_name,
                acceptable_condition=demand.acceptable_food_condition,
                dietary_requirements=demand.dietary_requirements,
            )
            warnings.extend(prod_comp.warnings)
            if not prod_comp.is_compatible:
                rejection_reasons.append(f"Product mismatch: {prod_comp.notes}")

            # Check Hard Constraint 4: Storage Compatibility
            stor_comp = StorageCompatibilityEvaluator.evaluate(
                surplus_storage=listing.storage_condition,
                demand_storage=demand.storage_capability,
                receiver_cold_storage=receiver.cold_storage_capabilities,
            )
            warnings.extend(stor_comp.warnings)
            if not stor_comp.is_compatible:
                rejection_reasons.append(f"Storage mismatch: {stor_comp.notes}")

            # Check Hard Constraint 5: Quantity Compatibility
            qty_comp = QuantityCompatibilityEvaluator.evaluate(
                surplus_remaining_kg=listing.remaining_quantity_kg,
                demand_requested_kg=demand.requested_quantity_kg,
                demand_fulfilled_kg=demand.fulfilled_quantity_kg,
            )
            if not qty_comp.is_compatible:
                rejection_reasons.append(f"Quantity issue: {qty_comp.notes}")

            # Check Hard Constraint 6: Geospatial Feasibility & Route
            has_supplier_coords = supplier.latitude is not None and supplier.longitude is not None
            s_lat = float(supplier.latitude) if has_supplier_coords else None
            s_lon = float(supplier.longitude) if has_supplier_coords else None

            straight_km = 0.0
            road_km = 0.0
            transit_mins = 0.0
            routing_provider = "HAVERSINE_FALLBACK"
            is_route_fallback = True
            transit_feasibility = "UNKNOWN"
            avail_mins: Optional[float] = None
            req_mins: Optional[float] = None

            if not has_supplier_coords or not has_receiver_coords:
                warnings.append("Facility location coordinates missing; geospatial feasibility cannot be evaluated.")
                transit_feasibility = "UNKNOWN"
            elif len(rejection_reasons) > 0:
                # DEF-FE-002: Cheap compatibility filters failed (category, storage, condition, quantity, or deadline).
                # Avoid sequential OSRM requests for ineligible pairs; calculate deterministic Haversine approximation.
                straight_km = haversine_distance(s_lat, s_lon, r_lat, r_lon)
                road_km = approximate_road_distance(straight_km, settings.DEFAULT_CIRCUITY_FACTOR)
                transit_mins = approximate_travel_duration_minutes(road_km, settings.DEFAULT_AVERAGE_SPEED_KMH)
                routing_provider = "HAVERSINE_FALLBACK"
                is_route_fallback = True
                transit_feasibility = "UNKNOWN"
                warnings.append("Road routing query skipped: candidate rejected by deterministic compatibility filters.")
            else:
                route_res = routing_service.estimate_route(
                    supplier_id=supplier.id,
                    receiver_id=receiver.id,
                    supplier_lat=s_lat,
                    supplier_lon=s_lon,
                    dest_lat=r_lat,
                    dest_lon=r_lon,
                    estimated_usable_deadline=listing.estimated_deadline,
                    handling_buffer_minutes=30,
                    supplier_name=supplier.organization_name,
                    receiver_name=receiver.organization_name,
                    evaluation_time=now,
                )
                straight_km = route_res.straight_line_distance_km
                road_km = route_res.road_distance_km
                transit_mins = route_res.estimated_travel_minutes
                routing_provider = route_res.routing_provider
                is_route_fallback = route_res.is_fallback
                transit_feasibility = route_res.feasibility
                avail_mins = route_res.available_minutes
                req_mins = route_res.required_minutes
                warnings.extend(route_res.warnings)

                if transit_feasibility == "INFEASIBLE":
                    rejection_reasons.append(
                        f"Temporally infeasible: transit duration + buffer ({req_mins}m) exceeds remaining shelf life ({avail_mins}m)"
                    )

            # Determine Overall Eligibility
            eligibility: EligibilityStatus
            is_eligible: bool

            if len(rejection_reasons) > 0:
                eligibility = "INELIGIBLE"
                is_eligible = False
            elif prod_comp.match_level == "AMBIGUOUS" or stor_comp.match_level == "UNKNOWN" or transit_feasibility == "UNKNOWN":
                eligibility = "REVIEW_REQUIRED"
                is_eligible = False
                rejection_reasons.append("Data uncertainty or product ambiguity requires coordinator review")
            else:
                eligibility = "ELIGIBLE"
                is_eligible = True

            # Calculate Deterministic Score Breakdown
            score_breakdown = CandidateRanker.calculate_score(
                is_eligible=is_eligible,
                urgency=perish_eval.urgency,
                remaining_hours=remaining_hours,
                road_distance_km=road_km,
                transit_feasibility=transit_feasibility,
                available_minutes=avail_mins,
                required_minutes=req_mins,
                surplus_available_kg=float(listing.remaining_quantity_kg),
                demand_outstanding_kg=d_out,
                receiver_priority=receiver.priority_level or 3,
            )

            # Build Deterministic Explanation
            explanation = ExplanationBuilder.build(
                eligibility=eligibility,
                is_eligible=is_eligible,
                rejection_reasons=rejection_reasons,
                product=prod_comp,
                storage=stor_comp,
                quantity=qty_comp,
                perishability_urgency=perish_eval.urgency,
                remaining_hours=remaining_hours,
                transit_feasibility=transit_feasibility,
                road_distance_km=road_km,
                estimated_transit_minutes=transit_mins,
                is_route_fallback=is_route_fallback,
                total_score=score_breakdown.total_score,
            )

            candidate = CandidateMatch(
                surplus_listing_id=listing.id,
                demand_request_id=demand.id,
                supplier_id=supplier.id,
                receiver_id=receiver.id,
                supplier_name=supplier.organization_name,
                receiver_name=receiver.organization_name,
                item_name=listing.item_name,
                food_category=listing.food_category,
                eligibility=eligibility,
                is_eligible=is_eligible,
                rejection_reasons=rejection_reasons,
                product_compatibility=prod_comp,
                quantity_compatibility=qty_comp,
                storage_compatibility=stor_comp,
                perishability_urgency=perish_eval.urgency,
                remaining_shelf_life_hours=remaining_hours,
                transit_feasibility=transit_feasibility,
                straight_line_distance_km=straight_km,
                road_distance_km=road_km,
                estimated_transit_minutes=transit_mins,
                handling_buffer_minutes=30,
                routing_provider=routing_provider,
                is_route_fallback=is_route_fallback,
                receiver_priority=receiver.priority_level or 3,
                receiver_category=receiver.receiver_category,
                score=score_breakdown.total_score,
                score_breakdown=score_breakdown,
                warnings=list(set(warnings)),
                explanation=explanation,
                evaluated_at=now,
            )
            candidates.append(candidate)

        # 7. Sorting & Ranking
        eligible_candidates = sorted(
            [c for c in candidates if c.eligibility == "ELIGIBLE"],
            key=lambda c: c.score,
            reverse=True,
        )
        review_candidates = sorted(
            [c for c in candidates if c.eligibility == "REVIEW_REQUIRED"],
            key=lambda c: (c.score_breakdown.urgency_score + c.score_breakdown.proximity_score),
            reverse=True,
        )
        ineligible_candidates = [c for c in candidates if c.eligibility == "INELIGIBLE"]

        all_ranked = eligible_candidates + review_candidates + ineligible_candidates

        if not include_ineligible:
            final_list = eligible_candidates + review_candidates
        else:
            final_list = all_ranked

        total_count = len(final_list)
        offset = (page - 1) * page_size
        paginated_candidates = final_list[offset : offset + page_size]

        return MatchingQueryResponse(
            source_type="DEMAND_REQUEST",
            source_id=demand.id,
            source_name=demand.item_name or demand.food_category,
            total_candidates=total_count,
            eligible_count=len(eligible_candidates),
            ineligible_count=len(ineligible_candidates),
            review_required_count=len(review_candidates),
            page=page,
            page_size=page_size,
            candidates=paginated_candidates,
        )
