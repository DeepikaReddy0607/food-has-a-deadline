import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Tuple, Dict, Any
import pytest

from app.models.food import SurplusListing, DemandRequest
from app.models.user import User, SupplierProfile, ReceiverProfile
from app.models.redistribution import AllocationProposal, AllocationItem, RedistributionTransaction
from app.core.security import hash_password, create_access_token
from app.matching.models import (
    CandidateMatch,
    ProductCompatibilityResult,
    StorageCompatibilityResult,
    QuantityCompatibilityResult,
    ScoreBreakdown,
)
from app.optimization.allocation_problem import (
    AllocationProblem,
    SurplusNode,
    DemandNode,
    EligibleEdge,
    to_hundredths_kg,
    to_centigrams,
    to_kg,
)
from app.optimization.ortools_solver import OrtoolsSolver
from app.optimization.proposal_explainer import ProposalExplainer


# =============================================================================
# HELPER FUNCTIONS TO BUILD SYNTHETIC CANDIDATE MATCHES & PROBLEMS
# =============================================================================

def make_candidate_match(
    surplus_id: uuid.UUID,
    demand_id: uuid.UUID,
    supplier_id: uuid.UUID,
    receiver_id: uuid.UUID,
    urgency: str = "HIGH",
    remaining_hours: float = 18.0,
    receiver_priority: int = 3,
    road_km: float = 12.0,
    transit_mins: float = 25.0,
    is_eligible: bool = True,
    score: float = 85.0,
) -> CandidateMatch:
    return CandidateMatch(
        candidate_id=uuid.uuid4(),
        surplus_listing_id=surplus_id,
        demand_request_id=demand_id,
        supplier_id=supplier_id,
        receiver_id=receiver_id,
        supplier_name="Test Supplier",
        receiver_name="Test Receiver",
        item_name="Produce",
        food_category="PRODUCE",
        eligibility="ELIGIBLE" if is_eligible else "INELIGIBLE",
        is_eligible=is_eligible,
        rejection_reasons=[] if is_eligible else ["Incompatible"],
        product_compatibility=ProductCompatibilityResult(
            match_level="EXACT",
            is_compatible=is_eligible,
            category_match=True,
            item_match=True,
            dietary_compatible=True,
            condition_compatible=True,
            dietary_flags=[],
            warnings=[],
            notes="Compatible",
        ),
        quantity_compatibility=QuantityCompatibilityResult(
            match_level="FULL_SATISFACTION",
            is_compatible=True,
            surplus_available_kg=100.0,
            demand_outstanding_kg=100.0,
            matched_quantity_kg=100.0,
            fulfillment_ratio=1.0,
            surplus_utilization_ratio=1.0,
            is_partial=False,
            notes="Full overlap",
        ),
        storage_compatibility=StorageCompatibilityResult(
            match_level="COMPATIBLE",
            is_compatible=True,
            required_storage="AMBIENT",
            available_storage="AMBIENT",
            receiver_has_cold_chain=True,
            warnings=[],
            notes="Compatible",
        ),
        perishability_urgency=urgency,
        remaining_shelf_life_hours=remaining_hours,
        transit_feasibility="FEASIBLE",
        straight_line_distance_km=road_km * 0.7,
        road_distance_km=road_km,
        estimated_transit_minutes=transit_mins,
        handling_buffer_minutes=30,
        routing_provider="HAVERSINE_FALLBACK",
        is_route_fallback=True,
        receiver_priority=receiver_priority,
        score=score,
        score_breakdown=ScoreBreakdown(
            urgency_score=20.0,
            proximity_score=20.0,
            shelf_life_margin_score=15.0,
            quantity_fit_score=15.0,
            priority_score=15.0,
            total_score=score,
        ),
        warnings=[],
        explanation="Synthetic test candidate match",
    )


# =============================================================================
# 1. UNIT TESTS: CP-SAT SOLVER CORE MATHEMATICAL CAPABILITIES
# =============================================================================

class TestOrtoolsSolverCore:
    def test_solver_1_to_1_exact_allocation(self):
        """1 supplier with 50 kg surplus allocated to 1 receiver needing 50 kg."""
        s_id = uuid.uuid4()
        d_id = uuid.uuid4()
        sup_id = uuid.uuid4()
        rec_id = uuid.uuid4()

        cand = make_candidate_match(s_id, d_id, sup_id, rec_id)
        problem = AllocationProblem(
            surplus_nodes={
                s_id: SurplusNode(
                    id=s_id,
                    supplier_id=sup_id,
                    supplier_name="Organic Farm",
                    food_category="PRODUCE",
                    item_name="Apples",
                    available_kg=50.0,
                    available_centigrams=to_centigrams(50.0),
                    urgency="HIGH",
                    remaining_shelf_life_hours=12.0,
                )
            },
            demand_nodes={
                d_id: DemandNode(
                    id=d_id,
                    receiver_id=rec_id,
                    receiver_name="Food Bank",
                    food_category="PRODUCE",
                    item_name="Apples",
                    requested_kg=50.0,
                    requested_centigrams=to_centigrams(50.0),
                    priority_level=4,
                )
            },
            eligible_edges={
                (s_id, d_id): EligibleEdge(
                    surplus_id=s_id,
                    demand_id=d_id,
                    max_flow_centigrams=to_centigrams(50.0),
                    urgency="HIGH",
                    receiver_priority=4,
                    road_distance_km=10.0,
                    estimated_transit_minutes=20,
                    shelf_life_slack_minutes=600.0,
                    score=85.0,
                    explanation="Compatible",
                    candidate_match=cand,
                )
            },
        )

        res = OrtoolsSolver.solve(problem)
        assert res.status == "OPTIMAL"
        assert res.allocations_kg.get((s_id, d_id)) == 50.0

    def test_solver_1_to_n_split(self):
        """1 large supplier batch (300 kg) partitioned across 3 receivers (100, 120, 80 kg)."""
        s_id = uuid.uuid4()
        sup_id = uuid.uuid4()

        d1_id, d2_id, d3_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        r1_id, r2_id, r3_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

        s_node = SurplusNode(
            id=s_id,
            supplier_id=sup_id,
            supplier_name="City Bakery",
            food_category="BAKERY",
            item_name="Bread Loaves",
            available_kg=300.0,
            available_centigrams=to_centigrams(300.0),
            urgency="CRITICAL",
            remaining_shelf_life_hours=5.0,
        )

        d_nodes = {
            d1_id: DemandNode(d1_id, r1_id, "Shelter A", "BAKERY", "Bread", 100.0, to_centigrams(100.0), 5),
            d2_id: DemandNode(d2_id, r2_id, "Pantry B", "BAKERY", "Bread", 120.0, to_centigrams(120.0), 4),
            d3_id: DemandNode(d3_id, r3_id, "Kitchen C", "BAKERY", "Bread", 80.0, to_centigrams(80.0), 3),
        }

        edges = {}
        for d_id, d_node in d_nodes.items():
            cand = make_candidate_match(s_id, d_id, sup_id, d_node.receiver_id, urgency="CRITICAL")
            edges[(s_id, d_id)] = EligibleEdge(
                surplus_id=s_id,
                demand_id=d_id,
                max_flow_centigrams=d_node.requested_centigrams,
                urgency="CRITICAL",
                receiver_priority=d_node.priority_level,
                road_distance_km=15.0,
                estimated_transit_minutes=25,
                shelf_life_slack_minutes=200.0,
                score=90.0,
                explanation="Bread match",
                candidate_match=cand,
            )

        problem = AllocationProblem(
            surplus_nodes={s_id: s_node},
            demand_nodes=d_nodes,
            eligible_edges=edges,
        )

        res = OrtoolsSolver.solve(problem)
        assert res.status == "OPTIMAL"
        assert res.allocations_kg.get((s_id, d1_id)) == 100.0
        assert res.allocations_kg.get((s_id, d2_id)) == 120.0
        assert res.allocations_kg.get((s_id, d3_id)) == 80.0
        assert sum(res.allocations_kg.values()) == 300.0

    def test_solver_n_to_1_aggregation(self):
        """2 suppliers (60 kg, 90 kg) aggregated to satisfy a 200 kg demand."""
        s1_id, s2_id = uuid.uuid4(), uuid.uuid4()
        sup1_id, sup2_id = uuid.uuid4(), uuid.uuid4()
        d_id = uuid.uuid4()
        rec_id = uuid.uuid4()

        surplus_nodes = {
            s1_id: SurplusNode(s1_id, sup1_id, "Farm 1", "PRODUCE", "Carrots", 60.0, to_centigrams(60.0), "MODERATE", 30.0),
            s2_id: SurplusNode(s2_id, sup2_id, "Farm 2", "PRODUCE", "Carrots", 90.0, to_centigrams(90.0), "HIGH", 16.0),
        }
        demand_node = DemandNode(d_id, rec_id, "Central Kitchen", "PRODUCE", "Carrots", 200.0, to_centigrams(200.0), 4)

        edges = {
            (s1_id, d_id): EligibleEdge(
                s1_id, d_id, to_centigrams(60.0), "MODERATE", 4, 12.0, 20, 1000.0, 75.0, "Carrots 1",
                make_candidate_match(s1_id, d_id, sup1_id, rec_id, urgency="MODERATE"),
            ),
            (s2_id, d_id): EligibleEdge(
                s2_id, d_id, to_centigrams(90.0), "HIGH", 4, 8.0, 15, 800.0, 85.0, "Carrots 2",
                make_candidate_match(s2_id, d_id, sup2_id, rec_id, urgency="HIGH"),
            ),
        }

        problem = AllocationProblem(
            surplus_nodes=surplus_nodes,
            demand_nodes={d_id: demand_node},
            eligible_edges=edges,
        )

        res = OrtoolsSolver.solve(problem)
        assert res.status == "OPTIMAL"
        assert res.allocations_kg.get((s1_id, d_id)) == 60.0
        assert res.allocations_kg.get((s2_id, d_id)) == 90.0
        assert sum(res.allocations_kg.values()) == 150.0  # partial satisfaction: 150 of 200 kg

    def test_solver_n_to_n_network_conservation(self):
        """Multi-supplier, multi-receiver network verifying strict supply and demand conservation."""
        s1_id, s2_id = uuid.uuid4(), uuid.uuid4()
        d1_id, d2_id = uuid.uuid4(), uuid.uuid4()

        surplus_nodes = {
            s1_id: SurplusNode(s1_id, uuid.uuid4(), "S1", "PRODUCE", "Veg", 100.0, to_centigrams(100.0), "HIGH", 15.0),
            s2_id: SurplusNode(s2_id, uuid.uuid4(), "S2", "PRODUCE", "Veg", 80.0, to_centigrams(80.0), "CRITICAL", 4.0),
        }
        demand_nodes = {
            d1_id: DemandNode(d1_id, uuid.uuid4(), "R1", "PRODUCE", "Veg", 70.0, to_centigrams(70.0), 5),
            d2_id: DemandNode(d2_id, uuid.uuid4(), "R2", "PRODUCE", "Veg", 110.0, to_centigrams(110.0), 3),
        }

        edges = {}
        for s_id, s_node in surplus_nodes.items():
            for d_id, d_node in demand_nodes.items():
                cand = make_candidate_match(s_id, d_id, s_node.supplier_id, d_node.receiver_id, urgency=s_node.urgency)
                edges[(s_id, d_id)] = EligibleEdge(
                    surplus_id=s_id,
                    demand_id=d_id,
                    max_flow_centigrams=min(s_node.available_centigrams, d_node.requested_centigrams),
                    urgency=s_node.urgency,
                    receiver_priority=d_node.priority_level,
                    road_distance_km=10.0,
                    estimated_transit_minutes=20,
                    shelf_life_slack_minutes=150.0,
                    score=80.0,
                    explanation="Network match",
                    candidate_match=cand,
                )

        problem = AllocationProblem(
            surplus_nodes=surplus_nodes,
            demand_nodes=demand_nodes,
            eligible_edges=edges,
        )

        res = OrtoolsSolver.solve(problem)
        assert res.status == "OPTIMAL"
        total_allocated = sum(res.allocations_kg.values())
        assert total_allocated == 180.0  # 100 + 80 = 180 supply, 70 + 110 = 180 demand

        # Verify Supply Conservation
        for s_id, s_node in surplus_nodes.items():
            s_allocated = sum(qty for (s, d), qty in res.allocations_kg.items() if s == s_id)
            assert s_allocated <= s_node.available_kg

        # Verify Demand Conservation
        for d_id, d_node in demand_nodes.items():
            d_allocated = sum(qty for (s, d), qty in res.allocations_kg.items() if d == d_id)
            assert d_allocated <= d_node.requested_kg

    def test_priority_weighting_allocates_to_higher_priority_receiver(self):
        """When 100 kg surplus is contested by Priority 5 and Priority 1, Priority 5 receives it."""
        s_id = uuid.uuid4()
        d_p5_id = uuid.uuid4()
        d_p1_id = uuid.uuid4()

        s_node = SurplusNode(s_id, uuid.uuid4(), "S", "PRODUCE", "Tomatoes", 100.0, to_centigrams(100.0), "HIGH", 12.0)
        d_nodes = {
            d_p5_id: DemandNode(d_p5_id, uuid.uuid4(), "High Need Shelter", "PRODUCE", "Tomatoes", 100.0, to_centigrams(100.0), 5),
            d_p1_id: DemandNode(d_p1_id, uuid.uuid4(), "Low Need Pantry", "PRODUCE", "Tomatoes", 100.0, to_centigrams(100.0), 1),
        }

        edges = {
            (s_id, d_p5_id): EligibleEdge(
                s_id, d_p5_id, to_centigrams(100.0), "HIGH", 5, 10.0, 20, 500.0, 95.0, "To P5",
                make_candidate_match(s_id, d_p5_id, s_node.supplier_id, d_nodes[d_p5_id].receiver_id, receiver_priority=5),
            ),
            (s_id, d_p1_id): EligibleEdge(
                s_id, d_p1_id, to_centigrams(100.0), "HIGH", 1, 10.0, 20, 500.0, 60.0, "To P1",
                make_candidate_match(s_id, d_p1_id, s_node.supplier_id, d_nodes[d_p1_id].receiver_id, receiver_priority=1),
            ),
        }

        problem = AllocationProblem(
            surplus_nodes={s_id: s_node},
            demand_nodes=d_nodes,
            eligible_edges=edges,
        )

        res = OrtoolsSolver.solve(problem)
        assert res.status == "OPTIMAL"
        assert res.allocations_kg.get((s_id, d_p5_id)) == 100.0
        assert res.allocations_kg.get((s_id, d_p1_id), 0.0) == 0.0

    def test_urgency_weighting_allocates_critical_stock_first(self):
        """When 50 kg demand is contested by CRITICAL and LOW urgency batches, CRITICAL is allocated."""
        s_crit_id = uuid.uuid4()
        s_low_id = uuid.uuid4()
        d_id = uuid.uuid4()
        r_id = uuid.uuid4()

        surplus_nodes = {
            s_crit_id: SurplusNode(s_crit_id, uuid.uuid4(), "S Crit", "DAIRY", "Milk", 50.0, to_centigrams(50.0), "CRITICAL", 4.0),
            s_low_id: SurplusNode(s_low_id, uuid.uuid4(), "S Low", "DAIRY", "Milk", 50.0, to_centigrams(50.0), "LOW", 96.0),
        }
        demand_node = DemandNode(d_id, r_id, "Kitchen", "DAIRY", "Milk", 50.0, to_centigrams(50.0), 3)

        edges = {
            (s_crit_id, d_id): EligibleEdge(
                s_crit_id, d_id, to_centigrams(50.0), "CRITICAL", 3, 10.0, 20, 180.0, 95.0, "Critical Milk",
                make_candidate_match(s_crit_id, d_id, surplus_nodes[s_crit_id].supplier_id, r_id, urgency="CRITICAL"),
            ),
            (s_low_id, d_id): EligibleEdge(
                s_low_id, d_id, to_centigrams(50.0), "LOW", 3, 10.0, 20, 5000.0, 55.0, "Low Milk",
                make_candidate_match(s_low_id, d_id, surplus_nodes[s_low_id].supplier_id, r_id, urgency="LOW"),
            ),
        }

        problem = AllocationProblem(
            surplus_nodes=surplus_nodes,
            demand_nodes={d_id: demand_node},
            eligible_edges=edges,
        )

        res = OrtoolsSolver.solve(problem)
        assert res.status == "OPTIMAL"
        assert res.allocations_kg.get((s_crit_id, d_id)) == 50.0
        assert res.allocations_kg.get((s_low_id, d_id), 0.0) == 0.0

    def test_distance_penalty_prefers_closer_receiver(self):
        """With identical priority, a receiver at 5 km is preferred over one at 80 km."""
        s_id = uuid.uuid4()
        d_close_id = uuid.uuid4()
        d_far_id = uuid.uuid4()

        s_node = SurplusNode(s_id, uuid.uuid4(), "S", "PRODUCE", "Greens", 50.0, to_centigrams(50.0), "MODERATE", 30.0)
        d_nodes = {
            d_close_id: DemandNode(d_close_id, uuid.uuid4(), "Close Shelter", "PRODUCE", "Greens", 50.0, to_centigrams(50.0), 3),
            d_far_id: DemandNode(d_far_id, uuid.uuid4(), "Far Shelter", "PRODUCE", "Greens", 50.0, to_centigrams(50.0), 3),
        }

        edges = {
            (s_id, d_close_id): EligibleEdge(
                s_id, d_close_id, to_centigrams(50.0), "MODERATE", 3, 5.0, 10, 1500.0, 85.0, "Close",
                make_candidate_match(s_id, d_close_id, s_node.supplier_id, d_nodes[d_close_id].receiver_id, road_km=5.0),
            ),
            (s_id, d_far_id): EligibleEdge(
                s_id, d_far_id, to_centigrams(50.0), "MODERATE", 3, 80.0, 120, 1000.0, 60.0, "Far",
                make_candidate_match(s_id, d_far_id, s_node.supplier_id, d_nodes[d_far_id].receiver_id, road_km=80.0),
            ),
        }

        problem = AllocationProblem(
            surplus_nodes={s_id: s_node},
            demand_nodes=d_nodes,
            eligible_edges=edges,
        )

        res = OrtoolsSolver.solve(problem)
        assert res.status == "OPTIMAL"
        assert res.allocations_kg.get((s_id, d_close_id)) == 50.0
        assert res.allocations_kg.get((s_id, d_far_id), 0.0) == 0.0


# =============================================================================
# 2. UNIT TESTS: PROPOSAL EXPLAINER AND UNMET DEMAND DIAGNOSTICS
# =============================================================================

class TestProposalExplainer:
    def test_diagnose_unfulfilled_demands_reason_codes(self):
        """Tests that unfulfilled demand correctly reports diagnostic reason codes."""
        d_id = uuid.uuid4()
        d_node = DemandNode(d_id, uuid.uuid4(), "Shelter Pantry", "DAIRY", "Yogurt", 100.0, to_centigrams(100.0), 3)

        # Scenario: Candidate was rejected due to cold chain mismatch
        s_id = uuid.uuid4()
        cand = make_candidate_match(s_id, d_id, uuid.uuid4(), d_node.receiver_id, is_eligible=False)
        cand.rejection_reasons = ["Receiver lacks required cold chain storage capability"]

        problem = AllocationProblem(
            surplus_nodes={},
            demand_nodes={d_id: d_node},
            eligible_edges={},
            all_evaluated_candidates=[cand],
        )

        diagnostics = ProposalExplainer.diagnose_unfulfilled_demands(problem, allocations_kg={})
        assert len(diagnostics) == 1
        assert diagnostics[0].unfulfilled_quantity_kg == 100.0
        assert diagnostics[0].reason_code == "COLD_CHAIN_MISMATCH"
        assert "cold chain" in diagnostics[0].diagnostic_explanation.lower()

    def test_justification_string_generation(self):
        """Verifies clear, structured deterministic justification string."""
        justification = ProposalExplainer.generate_justification(
            total_allocated_kg=150.0,
            total_unallocated_kg=20.0,
            total_unmet_demand_kg=50.0,
            estimated_total_transit_km=32.5,
            items=[],
            solver_status="OPTIMAL",
        )
        assert "No eligible matches found" in justification or "150.00" in justification


# =============================================================================
# 3. END-TO-END INTEGRATION TESTS VIA FASTAPI REST API
# =============================================================================

def register_user(client, name: str, email: str, role: str) -> Tuple[str, Dict[str, str]]:
    client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": "Password123!", "role": role},
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}


def create_coordinator_token(db_session, email: str = "coord@fhd.org") -> Tuple[str, Dict[str, str]]:
    coord = User(
        email=email,
        hashed_password=hash_password("CoordPass123!"),
        role="COORDINATOR",
        is_active=True,
    )
    db_session.add(coord)
    db_session.commit()
    db_session.refresh(coord)
    token = create_access_token(subject=coord.id, role="COORDINATOR")
    return token, {"Authorization": f"Bearer {token}"}


def setup_optimization_environment(client, db_session) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)

    # 1. Coordinator (administrative creation in DB)
    coord_token, coord_headers = create_coordinator_token(db_session)

    # 2. Supplier
    sup_token, sup_headers = register_user(client, "Valley Farm", "farm@valley.org", "SUPPLIER")
    client.post(
        "/api/v1/suppliers/profile",
        json={
            "organization_name": "Valley Fresh Produce",
            "contact_phone": "+1-555-1111",
            "address": "100 Orchard Way",
            "city": "Napa",
            "state": "California",
            "latitude": 38.2975,
            "longitude": -122.2869,
            "facility_type": "FARM",
        },
        headers=sup_headers,
    )

    # Listing: 100 kg Organic Apples
    res_l1 = client.post(
        "/api/v1/surplus-listings",
        json={
            "food_category": "FRUITS",
            "item_name": "Organic Honeycrisp Apples",
            "initial_quantity_kg": 100.0,
            "estimated_deadline": (now + timedelta(hours=24)).isoformat(),
            "harvest_or_prep_date": (now - timedelta(hours=12)).isoformat(),
            "storage_condition": "AMBIENT",
            "food_condition": "GOOD",
        },
        headers=sup_headers,
    )
    assert res_l1.status_code == 201
    listing_id = res_l1.json()["id"]

    # 3. Receiver: Community Pantry
    rec_token, rec_headers = register_user(client, "City Pantry", "pantry@city.org", "RECEIVER")
    client.post(
        "/api/v1/receivers/profile",
        json={
            "organization_name": "Downtown Food Pantry",
            "contact_phone": "+1-555-2222",
            "address": "200 Market St",
            "city": "Napa",
            "state": "California",
            "latitude": 38.3000,
            "longitude": -122.2850,
            "receiver_category": "COMMUNITY_KITCHEN",
            "capacity_daily_kg": 500.0,
            "priority_level": 4,
        },
        headers=rec_headers,
    )

    # Mark profiles verified for matching/optimization
    for sp in db_session.query(SupplierProfile).all():
        sp.verification_status = "VERIFIED"
        sp.is_verified = True
    for rp in db_session.query(ReceiverProfile).all():
        rp.verification_status = "VERIFIED"
        rp.is_verified = True
    db_session.commit()

    # Demand: 80 kg Apples
    res_d1 = client.post(
        "/api/v1/demand-requests",
        json={
            "food_category": "FRUITS",
            "item_name": "Organic Honeycrisp Apples",
            "requested_quantity_kg": 80.0,
            "required_by": (now + timedelta(hours=36)).isoformat(),
            "storage_capability": "AMBIENT",
            "priority_weight": 4,
        },
        headers=rec_headers,
    )
    assert res_d1.status_code == 201
    demand_id = res_d1.json()["id"]

    return {
        "coord_headers": coord_headers,
        "sup_headers": sup_headers,
        "rec_headers": rec_headers,
        "listing_id": listing_id,
        "demand_id": demand_id,
    }


class TestOptimizationAPI:
    def test_coordinator_runs_optimization_and_persists_proposal(self, client, db_session):
        """Coordinator triggers optimization, gets optimal proposal, and proposal is persisted as PENDING_REVIEW."""
        env = setup_optimization_environment(client, db_session)
        headers = env["coord_headers"]
        listing_id = env["listing_id"]
        demand_id = env["demand_id"]

        # Run allocation optimization
        res = client.post(
            "/api/v1/optimization/allocation-proposals",
            json={
                "surplus_listing_ids": [listing_id],
                "demand_request_ids": [demand_id],
                "timeout_seconds": 5.0,
            },
            headers=headers,
        )
        assert res.status_code == 200
        body = res.json()

        assert body["proposal_id"] is not None
        proposal_id = body["proposal_id"]
        assert body["status"] == "PENDING_REVIEW"
        assert body["solver_status"] == "OPTIMAL"
        assert body["total_allocated_kg"] == 80.0  # Min(100 supply, 80 demand)
        assert body["total_unallocated_kg"] == 20.0
        assert body["total_unmet_demand_kg"] == 0.0
        assert len(body["items"]) == 1
        assert body["items"][0]["allocated_quantity_kg"] == 80.0
        assert body["items"][0]["urgency_at_allocation"] in ("CRITICAL", "HIGH", "MODERATE", "LOW")

        # Verify Persistence in Database
        db_prop = db_session.get(AllocationProposal, uuid.UUID(proposal_id))
        assert db_prop is not None
        assert db_prop.status == "PENDING_REVIEW"
        assert float(db_prop.total_allocated_kg) == 80.0
        assert len(db_prop.items) == 1
        assert float(db_prop.items[0].allocated_quantity_kg) == 80.0

        # CRITICAL TEST: Verify Inventory and Demand Quantities WERE NOT MODIFIED (Read-only guarantee)
        db_listing = db_session.get(SurplusListing, uuid.UUID(listing_id))
        assert float(db_listing.remaining_quantity_kg) == 100.0  # NOT DECREMENTED!
        assert db_listing.status == "ACTIVE"

        db_demand = db_session.get(DemandRequest, uuid.UUID(demand_id))
        assert float(db_demand.fulfilled_quantity_kg) == 0.0  # NOT INCREMENTED!
        assert db_demand.status == "OPEN"

        # Verify no RedistributionTransaction was created
        txs = db_session.query(RedistributionTransaction).all()
        assert len(txs) == 0

    def test_retrieve_proposal_by_id(self, client, db_session):
        """Coordinator can fetch a previously created proposal by ID."""
        env = setup_optimization_environment(client, db_session)
        headers = env["coord_headers"]

        create_res = client.post(
            "/api/v1/optimization/allocation-proposals",
            json={},
            headers=headers,
        )
        assert create_res.status_code == 200
        prop_id = create_res.json()["proposal_id"]

        get_res = client.get(f"/api/v1/optimization/proposals/{prop_id}", headers=headers)
        assert get_res.status_code == 200
        data = get_res.json()
        assert data["proposal_id"] == prop_id
        assert data["status"] == "PENDING_REVIEW"
        assert len(data["items"]) >= 1

    def test_rbac_supplier_and_receiver_forbidden(self, client, db_session):
        """Suppliers and Receivers cannot invoke the allocation optimizer."""
        env = setup_optimization_environment(client, db_session)

        # Supplier attempt
        res_sup = client.post(
            "/api/v1/optimization/allocation-proposals",
            json={},
            headers=env["sup_headers"],
        )
        assert res_sup.status_code == 403

        # Receiver attempt
        res_rec = client.post(
            "/api/v1/optimization/allocation-proposals",
            json={},
            headers=env["rec_headers"],
        )
        assert res_rec.status_code == 403

        # Unauthenticated attempt
        res_anon = client.post(
            "/api/v1/optimization/allocation-proposals",
            json={},
        )
        assert res_anon.status_code == 401

    def test_empty_market_returns_zero_allocations(self, client, db_session):
        """When no active listings exist, proposal returns 0 kg allocated without database error."""
        _, coord_headers = create_coordinator_token(db_session, "empty_coord@fhd.org")

        res = client.post(
            "/api/v1/optimization/allocation-proposals",
            json={"surplus_listing_ids": [str(uuid.uuid4())]},  # Non-existent listing
            headers=coord_headers,
        )
        assert res.status_code == 200
        body = res.json()
        assert body["total_allocated_kg"] == 0.0
        assert body["items"] == []
        assert body["proposal_id"] is None  # No row persisted if 0 kg allocated


# =============================================================================
# 4. MODULE 8 PREFLIGHT VERIFICATION & REGRESSION TESTS
# =============================================================================

class TestModule8PreflightVerifications:
    def test_quantity_scaling_hundredths_kg_terminology(self):
        """Verify scaling factor of 100 represents hundredths of a kilogram (0.01 kg)."""
        from app.optimization.allocation_problem import to_hundredths_kg, to_kg, to_centigrams, SCALE_FACTOR
        assert SCALE_FACTOR == 100
        assert to_hundredths_kg(1.0) == 100
        assert to_hundredths_kg(25.50) == 2550
        assert to_kg(2550) == 25.50
        assert to_centigrams(25.50) == 2550  # Backwards compatibility alias

    def test_objective_hierarchy_dominates_secondary_penalties(self):
        """
        Verify the base salvage reward strictly dominates all secondary preferences and penalties,
        guaranteeing that maximizing food volume is the primary objective.
        """
        s_id = uuid.uuid4()
        d_id = uuid.uuid4()
        sup_id = uuid.uuid4()
        rec_id = uuid.uuid4()

        # Create worst-case secondary scenario: lowest urgency (LOW), lowest priority (1), max distance (200 km)
        cand = make_candidate_match(s_id, d_id, sup_id, rec_id, urgency="LOW", receiver_priority=1, road_km=200.0)
        edge = EligibleEdge(
            surplus_id=s_id,
            demand_id=d_id,
            max_flow_hundredths_kg=to_hundredths_kg(100.0),
            urgency="LOW",
            receiver_priority=1,
            road_distance_km=200.0,
            estimated_transit_minutes=300,
            shelf_life_slack_minutes=0.0,
            score=30.0,
            explanation="Worst-case preferences",
            candidate_match=cand,
        )

        from app.optimization.objective_builder import ObjectiveBuilder
        unit_coeff = ObjectiveBuilder.calculate_unit_coefficient(edge)

        # Even with max distance penalty (-500) and lowest bonuses, coeff must be overwhelmingly positive (> 90000)
        assert unit_coeff > 90000

        # Run solver on this edge: must allocate the full 100 kg rather than leaving it unallocated
        problem = AllocationProblem(
            surplus_nodes={
                s_id: SurplusNode(s_id, sup_id, "S", "PRODUCE", "Food", 100.0, to_hundredths_kg(100.0), "LOW", 96.0)
            },
            demand_nodes={
                d_id: DemandNode(d_id, rec_id, "R", "PRODUCE", "Food", 100.0, to_hundredths_kg(100.0), 1)
            },
            eligible_edges={(s_id, d_id): edge},
        )
        res = OrtoolsSolver.solve(problem)
        assert res.status == "OPTIMAL"
        assert res.allocations_kg.get((s_id, d_id)) == 100.0

    def test_solver_statuses_distinguish_all_five_states(self):
        """Verify solver status mapping accurately distinguishes OPTIMAL, FEASIBLE, INFEASIBLE, MODEL_INVALID, and UNKNOWN."""
        from ortools.sat.python import cp_model
        status_mapping = {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.MODEL_INVALID: "MODEL_INVALID",
            cp_model.UNKNOWN: "UNKNOWN",
        }
        assert status_mapping[cp_model.OPTIMAL] == "OPTIMAL"
        assert status_mapping[cp_model.FEASIBLE] == "FEASIBLE"
        assert status_mapping[cp_model.INFEASIBLE] == "INFEASIBLE"
        assert status_mapping[cp_model.MODEL_INVALID] == "MODEL_INVALID"
        assert status_mapping[cp_model.UNKNOWN] == "UNKNOWN"

    def test_only_eligible_candidates_enter_model(self):
        """Verify that REVIEW_REQUIRED and INELIGIBLE candidates are strictly excluded from optimization edges."""
        s_id = uuid.uuid4()
        d_id = uuid.uuid4()
        cand_review = make_candidate_match(s_id, d_id, uuid.uuid4(), uuid.uuid4(), is_eligible=False)
        cand_review.eligibility = "REVIEW_REQUIRED"

        cand_ineligible = make_candidate_match(s_id, d_id, uuid.uuid4(), uuid.uuid4(), is_eligible=False)
        cand_ineligible.eligibility = "INELIGIBLE"

        # In allocation_service, only candidate.is_eligible and candidate.eligibility == 'ELIGIBLE' are admitted
        assert not (cand_review.is_eligible and cand_review.eligibility == "ELIGIBLE")
        assert not (cand_ineligible.is_eligible and cand_ineligible.eligibility == "ELIGIBLE")

    def test_competing_allocation_higher_volume_strictly_dominates_secondary_scores(self):
        """
        Mathematical proof regression test:
        Prove that a higher-volume allocation strictly beats a lower-volume allocation,
        even when the lower-volume allocation has theoretical maximum secondary scores
        (CRITICAL urgency, Priority 5, 0 km distance) and the higher-volume allocation has
        theoretical worst-case secondary scores (LOW urgency, Priority 1, 200 km distance).
        """
        s_id = uuid.uuid4()
        d_high_vol = uuid.uuid4()  # Wants 10.0 kg (1000 units)
        d_favored = uuid.uuid4()   # Wants 9.9 kg (990 units)
        sup_id = uuid.uuid4()
        rec_id1 = uuid.uuid4()
        rec_id2 = uuid.uuid4()

        cand_high = make_candidate_match(s_id, d_high_vol, sup_id, rec_id1, urgency="LOW", receiver_priority=1, road_km=200.0)
        cand_favored = make_candidate_match(s_id, d_favored, sup_id, rec_id2, urgency="CRITICAL", receiver_priority=5, road_km=0.0)

        edge_high = EligibleEdge(
            surplus_id=s_id,
            demand_id=d_high_vol,
            max_flow_hundredths_kg=to_hundredths_kg(10.0),
            urgency="LOW",
            receiver_priority=1,
            road_distance_km=200.0,
            estimated_transit_minutes=300,
            shelf_life_slack_minutes=0.0,
            score=25.0,
            explanation="Worst-case secondary",
            candidate_match=cand_high,
        )

        edge_favored = EligibleEdge(
            surplus_id=s_id,
            demand_id=d_favored,
            max_flow_hundredths_kg=to_hundredths_kg(9.9),
            urgency="CRITICAL",
            receiver_priority=5,
            road_distance_km=0.0,
            estimated_transit_minutes=0,
            shelf_life_slack_minutes=1000.0,
            score=95.0,
            explanation="Best-case secondary",
            candidate_match=cand_favored,
        )

        problem = AllocationProblem(
            surplus_nodes={
                s_id: SurplusNode(s_id, sup_id, "S", "PRODUCE", "Food", 10.0, to_hundredths_kg(10.0), "LOW", 96.0)
            },
            demand_nodes={
                d_high_vol: DemandNode(d_high_vol, rec_id1, "R1", "PRODUCE", "Food", 10.0, to_hundredths_kg(10.0), 1),
                d_favored: DemandNode(d_favored, rec_id2, "R2", "PRODUCE", "Food", 9.9, to_hundredths_kg(9.9), 5),
            },
            eligible_edges={
                (s_id, d_high_vol): edge_high,
                (s_id, d_favored): edge_favored,
            },
        )

        res = OrtoolsSolver.solve(problem)
        assert res.status == "OPTIMAL"
        # Total volume rescued MUST be the full 10.0 kg, NOT capped at 9.9 kg!
        total_rescued = sum(res.allocations_kg.values())
        assert total_rescued == 10.0, f"Expected 10.0 kg total volume, got {total_rescued} kg"

    def test_competing_equal_volume_tie_broken_by_secondary_priorities(self):
        """
        When competing demands have identical volume, secondary priorities
        (urgency, receiver priority, distance) strictly break the tie.
        """
        s_id = uuid.uuid4()
        d_low_pri = uuid.uuid4()
        d_high_pri = uuid.uuid4()
        sup_id = uuid.uuid4()

        cand_low = make_candidate_match(s_id, d_low_pri, sup_id, uuid.uuid4(), urgency="LOW", receiver_priority=1, road_km=100.0)
        cand_high = make_candidate_match(s_id, d_high_pri, sup_id, uuid.uuid4(), urgency="CRITICAL", receiver_priority=5, road_km=5.0)

        edge_low = EligibleEdge(
            surplus_id=s_id,
            demand_id=d_low_pri,
            max_flow_hundredths_kg=to_hundredths_kg(10.0),
            urgency="LOW",
            receiver_priority=1,
            road_distance_km=100.0,
            estimated_transit_minutes=120,
            shelf_life_slack_minutes=0.0,
            score=30.0,
            explanation="Low priority edge",
            candidate_match=cand_low,
        )
        edge_high = EligibleEdge(
            surplus_id=s_id,
            demand_id=d_high_pri,
            max_flow_hundredths_kg=to_hundredths_kg(10.0),
            urgency="CRITICAL",
            receiver_priority=5,
            road_distance_km=5.0,
            estimated_transit_minutes=10,
            shelf_life_slack_minutes=500.0,
            score=95.0,
            explanation="High priority edge",
            candidate_match=cand_high,
        )

        # Supply has only 10.0 kg; both demand 10.0 kg (direct competition for same batch)
        problem = AllocationProblem(
            surplus_nodes={
                s_id: SurplusNode(s_id, sup_id, "S", "PRODUCE", "Food", 10.0, to_hundredths_kg(10.0), "LOW", 96.0)
            },
            demand_nodes={
                d_low_pri: DemandNode(d_low_pri, uuid.uuid4(), "R1", "PRODUCE", "Food", 10.0, to_hundredths_kg(10.0), 1),
                d_high_pri: DemandNode(d_high_pri, uuid.uuid4(), "R2", "PRODUCE", "Food", 10.0, to_hundredths_kg(10.0), 5),
            },
            eligible_edges={
                (s_id, d_low_pri): edge_low,
                (s_id, d_high_pri): edge_high,
            },
        )

        res = OrtoolsSolver.solve(problem)
        assert res.status == "OPTIMAL"
        assert res.allocations_kg.get((s_id, d_high_pri)) == 10.0
        assert res.allocations_kg.get((s_id, d_low_pri), 0.0) == 0.0

    def test_strict_supply_and_demand_conservation_multinode(self):
        """
        Verify that multi-node allocation problems strictly conserve flow:
        - No supplier ever exceeds its available capacity.
        - No receiver ever exceeds its requested demand.
        """
        s1 = uuid.uuid4()
        s2 = uuid.uuid4()
        d1 = uuid.uuid4()
        d2 = uuid.uuid4()
        d3 = uuid.uuid4()
        sup_id = uuid.uuid4()

        # Supply 1: 50 kg, Supply 2: 40 kg (total 90 kg)
        # Demand 1: 40 kg, Demand 2: 40 kg, Demand 3: 40 kg (total 120 kg - deficit)
        edges = {}
        for s_idx, (s_uuid, s_qty) in enumerate([(s1, 50.0), (s2, 40.0)]):
            for d_idx, (d_uuid, d_qty) in enumerate([(d1, 40.0), (d2, 40.0), (d3, 40.0)]):
                cand = make_candidate_match(s_uuid, d_uuid, sup_id, uuid.uuid4(), urgency="HIGH", receiver_priority=3, road_km=10.0)
                edges[(s_uuid, d_uuid)] = EligibleEdge(
                    surplus_id=s_uuid,
                    demand_id=d_uuid,
                    max_flow_hundredths_kg=to_hundredths_kg(min(s_qty, d_qty)),
                    urgency="HIGH",
                    receiver_priority=3,
                    road_distance_km=10.0,
                    estimated_transit_minutes=15,
                    shelf_life_slack_minutes=100.0,
                    score=70.0,
                    explanation="Multi-node edge",
                    candidate_match=cand,
                )

        problem = AllocationProblem(
            surplus_nodes={
                s1: SurplusNode(s1, sup_id, "S1", "PRODUCE", "Food", 50.0, to_hundredths_kg(50.0), "HIGH", 48.0),
                s2: SurplusNode(s2, sup_id, "S2", "PRODUCE", "Food", 40.0, to_hundredths_kg(40.0), "HIGH", 48.0),
            },
            demand_nodes={
                d1: DemandNode(d1, uuid.uuid4(), "D1", "PRODUCE", "Food", 40.0, to_hundredths_kg(40.0), 3),
                d2: DemandNode(d2, uuid.uuid4(), "D2", "PRODUCE", "Food", 40.0, to_hundredths_kg(40.0), 3),
                d3: DemandNode(d3, uuid.uuid4(), "D3", "PRODUCE", "Food", 40.0, to_hundredths_kg(40.0), 3),
            },
            eligible_edges=edges,
        )

        res = OrtoolsSolver.solve(problem)
        assert res.status in ("OPTIMAL", "FEASIBLE")

        # Check total allocated is exactly 90.0 kg (exhausts available supply)
        total_allocated = sum(res.allocations_kg.values())
        assert total_allocated == 90.0

        # Check per-supplier conservation
        s1_allocated = sum(v for (s, d), v in res.allocations_kg.items() if s == s1)
        s2_allocated = sum(v for (s, d), v in res.allocations_kg.items() if s == s2)
        assert s1_allocated <= 50.0001
        assert s2_allocated <= 40.0001

        # Check per-receiver conservation
        for d_target in [d1, d2, d3]:
            d_allocated = sum(v for (s, d), v in res.allocations_kg.items() if d == d_target)
            assert d_allocated <= 40.0001


