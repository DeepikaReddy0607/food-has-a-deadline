import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Tuple
from unittest.mock import patch, MagicMock
import pytest

from app.matching.models import (
    ProductCompatibilityResult,
    StorageCompatibilityResult,
    QuantityCompatibilityResult,
    ScoreBreakdown,
)
from app.matching.product_compatibility import ProductCompatibilityEvaluator
from app.matching.storage_compatibility import StorageCompatibilityEvaluator
from app.matching.quantity_compatibility import QuantityCompatibilityEvaluator
from app.matching.candidate_ranker import CandidateRanker
from app.matching.explanation_builder import ExplanationBuilder
from app.matching.matching_service import MatchingService
from app.models.food import SurplusListing, DemandRequest
from app.models.user import User, SupplierProfile, ReceiverProfile
from app.core.security import hash_password, create_access_token


# =============================================================================
# 1. UNIT TESTS: PRODUCT COMPATIBILITY EVALUATOR
# =============================================================================

class TestProductCompatibilityEvaluator:
    def test_direct_category_and_generic_item_match(self):
        """Generic demand for category matches any item in that category."""
        res = ProductCompatibilityEvaluator.evaluate(
            surplus_category="FRUITS",
            surplus_item_name="Honeycrisp Apples",
            surplus_condition="EXCELLENT",
            surplus_description="Fresh organic apples",
            demand_category="FRUITS",
            demand_item_name=None,
            acceptable_condition="FAIR",
            dietary_requirements=[],
        )
        assert res.is_compatible is True
        assert res.match_level == "CATEGORY_COMPATIBLE"
        assert res.category_match is True
        assert res.condition_compatible is True

    def test_exact_item_name_match(self):
        """Exact case-insensitive item match."""
        res = ProductCompatibilityEvaluator.evaluate(
            surplus_category="VEGETABLES",
            surplus_item_name="Organic Carrots",
            surplus_condition="GOOD",
            surplus_description=None,
            demand_category="VEGETABLES",
            demand_item_name="Organic Carrots",
            acceptable_condition="GOOD",
            dietary_requirements=["VEGAN"],
        )
        assert res.is_compatible is True
        assert res.match_level == "EXACT"
        assert res.dietary_compatible is True

    def test_category_mismatch_incompatible(self):
        """Category mismatch renders product incompatible."""
        res = ProductCompatibilityEvaluator.evaluate(
            surplus_category="DAIRY",
            surplus_item_name="Whole Milk",
            surplus_condition="GOOD",
            surplus_description=None,
            demand_category="FRUITS",
            demand_item_name=None,
            acceptable_condition="FAIR",
            dietary_requirements=[],
        )
        assert res.is_compatible is False
        assert res.match_level == "INCOMPATIBLE"
        assert res.category_match is False

    def test_dietary_vegan_violation_with_dairy(self):
        """Dairy category fails vegan dietary requirement."""
        res = ProductCompatibilityEvaluator.evaluate(
            surplus_category="DAIRY",
            surplus_item_name="Cheddar Cheese",
            surplus_condition="GOOD",
            surplus_description=None,
            demand_category="ANY",
            demand_item_name=None,
            acceptable_condition="FAIR",
            dietary_requirements=["VEGAN"],
        )
        assert res.is_compatible is False
        assert res.dietary_compatible is False
        assert any("Dairy product violates vegan" in f for f in res.dietary_flags)

    def test_condition_below_threshold_incompatible(self):
        """Food condition below receiver threshold fails condition check."""
        res = ProductCompatibilityEvaluator.evaluate(
            surplus_category="FRUITS",
            surplus_item_name="Bananas",
            surplus_condition="FAIR",  # Rank 1.0
            surplus_description=None,
            demand_category="FRUITS",
            demand_item_name=None,
            acceptable_condition="EXCELLENT",  # Rank 3.0
            dietary_requirements=[],
        )
        assert res.is_compatible is False
        assert res.condition_compatible is False
        assert any("CONDITION INCOMPATIBLE" in w for w in res.warnings)

    def test_item_disparity_triggers_ambiguous_review_required(self):
        """Different specific items within same category triggers AMBIGUOUS match."""
        res = ProductCompatibilityEvaluator.evaluate(
            surplus_category="FRUITS",
            surplus_item_name="Oranges",
            surplus_condition="GOOD",
            surplus_description=None,
            demand_category="FRUITS",
            demand_item_name="Apples",
            acceptable_condition="FAIR",
            dietary_requirements=[],
        )
        assert res.match_level == "AMBIGUOUS"
        assert any("REVIEW REQUIRED" in w for w in res.warnings)


# =============================================================================
# 2. UNIT TESTS: STORAGE COMPATIBILITY EVALUATOR
# =============================================================================

class TestStorageCompatibilityEvaluator:
    def test_ambient_surplus_compatible_with_all(self):
        """Ambient storage surplus is compatible with any facility."""
        res = StorageCompatibilityEvaluator.evaluate(
            surplus_storage="AMBIENT",
            demand_storage="AMBIENT",
            receiver_cold_storage={"refrigeration": False, "freezer": False},
        )
        assert res.is_compatible is True
        assert res.match_level == "COMPATIBLE"

    def test_refrigerated_surplus_compatible_with_refrigeration(self):
        """Refrigerated surplus compatible when receiver has refrigeration."""
        res = StorageCompatibilityEvaluator.evaluate(
            surplus_storage="REFRIGERATED",
            demand_storage="REFRIGERATED",
            receiver_cold_storage={"refrigeration": True, "freezer": False},
        )
        assert res.is_compatible is True
        assert res.match_level == "COMPATIBLE"

    def test_refrigerated_surplus_incompatible_without_refrigeration(self):
        """Refrigerated surplus fails when receiver lacks refrigeration."""
        res = StorageCompatibilityEvaluator.evaluate(
            surplus_storage="REFRIGERATED",
            demand_storage="AMBIENT",
            receiver_cold_storage={"refrigeration": False, "freezer": False},
        )
        assert res.is_compatible is False
        assert res.match_level == "INCOMPATIBLE"
        assert any("COLD CHAIN FAILURE" in w for w in res.warnings)

    def test_frozen_surplus_incompatible_with_only_refrigeration(self):
        """Frozen surplus fails if receiver only has standard refrigeration."""
        res = StorageCompatibilityEvaluator.evaluate(
            surplus_storage="FROZEN",
            demand_storage="REFRIGERATED",
            receiver_cold_storage={"refrigeration": True, "freezer": False},
        )
        assert res.is_compatible is False
        assert res.match_level == "INCOMPATIBLE"
        assert any("FREEZER DEFICIT" in w for w in res.warnings)


# =============================================================================
# 3. UNIT TESTS: QUANTITY COMPATIBILITY EVALUATOR
# =============================================================================

class TestQuantityCompatibilityEvaluator:
    def test_full_demand_satisfaction(self):
        """Surplus >= demand creates full satisfaction."""
        res = QuantityCompatibilityEvaluator.evaluate(
            surplus_remaining_kg=100.0,
            demand_requested_kg=60.0,
            demand_fulfilled_kg=10.0,  # 50.0 outstanding
        )
        assert res.is_compatible is True
        assert res.match_level == "FULL_SATISFACTION"
        assert res.is_partial is False
        assert res.matched_quantity_kg == 50.0
        assert res.fulfillment_ratio == 1.0
        assert res.surplus_utilization_ratio == 0.5

    def test_partial_demand_satisfaction(self):
        """Surplus < demand creates partial satisfaction."""
        res = QuantityCompatibilityEvaluator.evaluate(
            surplus_remaining_kg=25.0,
            demand_requested_kg=100.0,
            demand_fulfilled_kg=0.0,
        )
        assert res.is_compatible is True
        assert res.match_level == "PARTIAL_SATISFACTION"
        assert res.is_partial is True
        assert res.matched_quantity_kg == 25.0
        assert res.fulfillment_ratio == 0.25
        assert res.surplus_utilization_ratio == 1.0

    def test_zero_surplus_incompatible(self):
        """Depleted surplus returns ZERO_SURPLUS and is incompatible."""
        res = QuantityCompatibilityEvaluator.evaluate(
            surplus_remaining_kg=0.0,
            demand_requested_kg=50.0,
        )
        assert res.is_compatible is False
        assert res.match_level == "ZERO_SURPLUS"
        assert res.matched_quantity_kg == 0.0

    def test_fulfilled_demand_incompatible(self):
        """Fully fulfilled demand returns ZERO_DEMAND and is incompatible."""
        res = QuantityCompatibilityEvaluator.evaluate(
            surplus_remaining_kg=50.0,
            demand_requested_kg=50.0,
            demand_fulfilled_kg=50.0,
        )
        assert res.is_compatible is False
        assert res.match_level == "ZERO_DEMAND"
        assert res.matched_quantity_kg == 0.0


# =============================================================================
# 4. UNIT TESTS: CANDIDATE RANKER & SCORING
# =============================================================================

class TestCandidateRanker:
    def test_ineligible_candidate_strictly_receives_zero_score(self):
        """Ineligible candidate receives 0.0 score across all components."""
        score = CandidateRanker.calculate_score(
            is_eligible=False,
            urgency="CRITICAL",
            remaining_hours=2.0,
            road_distance_km=5.0,
            transit_feasibility="FEASIBLE",
            available_minutes=120.0,
            required_minutes=35.0,
            surplus_available_kg=100.0,
            demand_outstanding_kg=100.0,
            receiver_priority=5,
        )
        assert score.total_score == 0.0
        assert score.urgency_score == 0.0
        assert score.proximity_score == 0.0

    def test_eligible_candidate_scoring_breakdown(self):
        """Eligible candidate receives weighted composite score with transparent components."""
        score = CandidateRanker.calculate_score(
            is_eligible=True,
            urgency="HIGH",
            remaining_hours=12.0,
            road_distance_km=10.0,
            transit_feasibility="FEASIBLE",
            available_minutes=720.0,
            required_minutes=45.0,
            surplus_available_kg=50.0,
            demand_outstanding_kg=50.0,
            receiver_priority=4,
        )
        assert 0.0 < score.total_score <= 100.0
        assert score.urgency_score > 0.0
        assert score.proximity_score > 0.0
        assert score.shelf_life_margin_score == 100.0  # slack > 180 min
        assert score.quantity_fit_score == 100.0       # exact 1-to-1 match
        assert score.priority_score == 85.0           # priority 4

    def test_closer_distance_yields_higher_score(self):
        """Proximity score is higher for closer facilities."""
        score_close = CandidateRanker.calculate_score(
            is_eligible=True,
            urgency="MODERATE",
            remaining_hours=36.0,
            road_distance_km=5.0,
            transit_feasibility="FEASIBLE",
            available_minutes=2000.0,
            required_minutes=40.0,
            surplus_available_kg=50.0,
            demand_outstanding_kg=50.0,
            receiver_priority=3,
        )
        score_far = CandidateRanker.calculate_score(
            is_eligible=True,
            urgency="MODERATE",
            remaining_hours=36.0,
            road_distance_km=60.0,
            transit_feasibility="FEASIBLE",
            available_minutes=2000.0,
            required_minutes=120.0,
            surplus_available_kg=50.0,
            demand_outstanding_kg=50.0,
            receiver_priority=3,
        )
        assert score_close.proximity_score > score_far.proximity_score
        assert score_close.total_score > score_far.total_score


# =============================================================================
# 5. INTEGRATION & REST API TESTS
# =============================================================================

def register_user_token(client, name: str, email: str, role: str) -> Tuple[str, dict]:
    client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": "TestPassword123!", "role": role},
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "TestPassword123!"},
    )
    token = res.json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}


def setup_matching_scenario(client):
    """Sets up a real PostgreSQL scenario with 1 supplier and 2 receivers."""
    # 1. Supplier Setup
    sup_token, sup_headers = register_user_token(client, "Valley Orchard", "orchard@farm.com", "SUPPLIER")
    client.post(
        "/api/v1/suppliers/profile",
        json={
            "organization_name": "Valley Orchard Co.",
            "contact_phone": "+1-555-0101",
            "address": "100 Orchard Way",
            "city": "Santa Rosa",
            "state": "California",
            "latitude": 38.4404,
            "longitude": -122.7141,
            "facility_type": "FARM",
        },
        headers=sup_headers,
    )

    now = datetime.now(timezone.utc)
    # Active surplus batch: 100 kg Apples, 24 hours shelf life
    res_s = client.post(
        "/api/v1/surplus-listings",
        json={
            "food_category": "FRUITS",
            "item_name": "Crisp Apples",
            "initial_quantity_kg": 100.0,
            "harvest_or_prep_date": (now - timedelta(hours=4)).isoformat(),
            "estimated_deadline": (now + timedelta(hours=24)).isoformat(),
            "food_condition": "GOOD",
            "storage_condition": "AMBIENT",
        },
        headers=sup_headers,
    )
    listing_id = res_s.json()["id"]

    # 2. Receiver 1 Setup: Close Community Kitchen (Compatible demand for Fruits)
    rec1_token, rec1_headers = register_user_token(client, "Santa Rosa Kitchen", "kitchen@sr.org", "RECEIVER")
    client.post(
        "/api/v1/receivers/profile",
        json={
            "organization_name": "Santa Rosa Community Kitchen",
            "contact_phone": "+1-555-0202",
            "address": "200 Main St",
            "city": "Santa Rosa",
            "state": "California",
            "latitude": 38.4450,
            "longitude": -122.7100,
            "receiver_category": "COMMUNITY_KITCHEN",
            "capacity_daily_kg": 300.0,
            "priority_level": 4,
        },
        headers=rec1_headers,
    )
    res_d1 = client.post(
        "/api/v1/demand-requests",
        json={
            "food_category": "FRUITS",
            "item_name": "Fresh Apples",
            "requested_quantity_kg": 60.0,
            "required_by": (now + timedelta(hours=18)).isoformat(),
            "storage_capability": "AMBIENT",
            "priority_weight": 4,
        },
        headers=rec1_headers,
    )
    demand1_id = res_d1.json()["id"]

    # 3. Receiver 2 Setup: Incompatible Category Demand (Dairy request)
    rec2_token, rec2_headers = register_user_token(client, "Shelter Pantry", "shelter@pantry.org", "RECEIVER")
    client.post(
        "/api/v1/receivers/profile",
        json={
            "organization_name": "Downtown Shelter Pantry",
            "contact_phone": "+1-555-0303",
            "address": "300 Center St",
            "city": "Santa Rosa",
            "state": "California",
            "latitude": 38.4410,
            "longitude": -122.7120,
            "receiver_category": "SHELTER",
            "capacity_daily_kg": 200.0,
            "priority_level": 3,
        },
        headers=rec2_headers,
    )
    res_d2 = client.post(
        "/api/v1/demand-requests",
        json={
            "food_category": "DAIRY",
            "item_name": "Milk",
            "requested_quantity_kg": 40.0,
            "required_by": (now + timedelta(hours=12)).isoformat(),
            "storage_capability": "REFRIGERATED",
            "priority_weight": 3,
        },
        headers=rec2_headers,
    )
    demand2_id = res_d2.json()["id"]

    return {
        "sup_headers": sup_headers,
        "rec1_headers": rec1_headers,
        "rec2_headers": rec2_headers,
        "listing_id": listing_id,
        "demand1_id": demand1_id,
        "demand2_id": demand2_id,
    }


def test_supplier_finds_candidates_for_listing(client):
    """Supplier retrieves ranked compatible receiver candidates for their listing."""
    data = setup_matching_scenario(client)
    listing_id = data["listing_id"]
    headers = data["sup_headers"]

    # Include ineligible candidates to test transparency
    res = client.get(f"/api/v1/matching/listings/{listing_id}/candidates?include_ineligible=true", headers=headers)
    assert res.status_code == 200
    body = res.json()

    assert body["source_type"] == "SURPLUS_LISTING"
    assert body["source_id"] == listing_id
    assert body["total_candidates"] >= 2
    assert body["eligible_count"] >= 1
    assert body["ineligible_count"] >= 1

    # First candidate should be the eligible matching kitchen
    eligible = [c for c in body["candidates"] if c["eligibility"] == "ELIGIBLE"]
    assert len(eligible) >= 1
    top = eligible[0]
    assert top["receiver_name"] == "Santa Rosa Community Kitchen"
    assert top["is_eligible"] is True
    assert top["score"] > 0.0
    assert top["product_compatibility"]["is_compatible"] is True
    assert top["storage_compatibility"]["is_compatible"] is True
    assert top["quantity_compatibility"]["is_compatible"] is True
    assert top["transit_feasibility"] == "FEASIBLE"
    assert "ELIGIBLE candidate" in top["explanation"]


def test_receiver_finds_candidates_for_demand(client):
    """Receiver retrieves ranked compatible surplus listings for their demand."""
    data = setup_matching_scenario(client)
    demand1_id = data["demand1_id"]
    headers = data["rec1_headers"]

    res = client.get(f"/api/v1/matching/demands/{demand1_id}/candidates", headers=headers)
    assert res.status_code == 200
    body = res.json()

    assert body["source_type"] == "DEMAND_REQUEST"
    assert body["source_id"] == demand1_id
    assert len(body["candidates"]) >= 1
    candidate = body["candidates"][0]
    assert candidate["eligibility"] == "ELIGIBLE"
    assert candidate["supplier_name"] == "Valley Orchard Co."


def test_tenant_isolation_unauthorized_listing_access(client):
    """Supplier 2 cannot query candidate matches for Supplier 1's listing."""
    data = setup_matching_scenario(client)
    listing_id = data["listing_id"]

    # Register an intruder supplier
    _, intruder_headers = register_user_token(client, "Intruder Farm", "intruder@farm.com", "SUPPLIER")
    res = client.get(f"/api/v1/matching/listings/{listing_id}/candidates", headers=intruder_headers)
    assert res.status_code == 404
    assert "Surplus listing not found" in res.json()["detail"]


def test_tenant_isolation_unauthorized_demand_access(client):
    """Receiver 2 cannot query candidate matches for Receiver 1's demand."""
    data = setup_matching_scenario(client)
    demand1_id = data["demand1_id"]
    rec2_headers = data["rec2_headers"]

    res = client.get(f"/api/v1/matching/demands/{demand1_id}/candidates", headers=rec2_headers)
    assert res.status_code == 404
    assert "Demand request not found" in res.json()["detail"]


def test_unauthenticated_request_rejected(client):
    """Unauthenticated calls to matching endpoints return 401."""
    random_id = str(uuid.uuid4())
    res1 = client.get(f"/api/v1/matching/listings/{random_id}/candidates")
    res2 = client.get(f"/api/v1/matching/demands/{random_id}/candidates")
    assert res1.status_code == 401
    assert res2.status_code == 401


def test_read_only_integrity_matching_does_not_mutate_state(client, db_session):
    """Matching queries must never alter inventory quantities, demand states, or create allocations."""
    data = setup_matching_scenario(client)
    listing_id = uuid.UUID(data["listing_id"])
    demand1_id = uuid.UUID(data["demand1_id"])
    headers = data["sup_headers"]

    # Check baseline in DB
    listing_before = db_session.get(SurplusListing, listing_id)
    demand_before = db_session.get(DemandRequest, demand1_id)
    qty_before = listing_before.remaining_quantity_kg
    dem_fulfilled_before = demand_before.fulfilled_quantity_kg

    # Perform matching request
    res = client.get(f"/api/v1/matching/listings/{listing_id}/candidates", headers=headers)
    assert res.status_code == 200

    # Verify baseline in DB is identical
    db_session.expire_all()
    listing_after = db_session.get(SurplusListing, listing_id)
    demand_after = db_session.get(DemandRequest, demand1_id)

    assert listing_after.remaining_quantity_kg == qty_before
    assert demand_after.fulfilled_quantity_kg == dem_fulfilled_before
    assert listing_after.status == "ACTIVE"
    assert demand_after.status == "OPEN"


# =============================================================================
# 4. REGRESSION TESTS (DEF-FE-002 PERFORMANCE REMEDIATION)
# =============================================================================

def test_osrm_skipped_for_cheap_incompatible_candidates(client):
    """DEF-FE-002: Ensure external road routing is NOT invoked for candidates failing cheap filters."""
    data = setup_matching_scenario(client)
    listing_id = data["listing_id"]
    headers = data["sup_headers"]

    with patch("app.matching.matching_service.routing_service.estimate_route") as mock_estimate:
        # Configure mock return value for when it IS called
        from app.geospatial.models import RouteEstimateResult, Coordinates
        mock_estimate.return_value = RouteEstimateResult(
            supplier_id=uuid.uuid4(),
            receiver_id=uuid.uuid4(),
            supplier_coordinates=Coordinates(latitude=38.4404, longitude=-122.7141),
            receiver_coordinates=Coordinates(latitude=38.4450, longitude=-122.7100),
            straight_line_distance_km=1.2,
            road_distance_km=1.5,
            estimated_travel_minutes=4.0,
            routing_provider="OSRM",
            is_fallback=False,
            feasibility="FEASIBLE",
            available_minutes=1200.0,
            required_minutes=34.0,
            warnings=[],
            evaluated_at=datetime.now(timezone.utc),
        )

        res = client.get(
            f"/api/v1/matching/listings/{listing_id}/candidates?include_ineligible=true",
            headers=headers,
        )
        assert res.status_code == 200
        body = res.json()

        # In setup_matching_scenario, demand1 is FRUITS (compatible), demand2 is DAIRY (incompatible)
        # Therefore, estimate_route should be called EXACTLY once (only for demand1)
        assert mock_estimate.call_count == 1

        # Verify candidate models
        eligible = [c for c in body["candidates"] if c["is_eligible"]]
        ineligible = [c for c in body["candidates"] if not c["is_eligible"]]

        assert len(eligible) >= 1
        assert eligible[0]["routing_provider"] == "OSRM"

        # Ineligible candidates must have skipped routing
        assert len(ineligible) >= 1
        dairy_cand = next(c for c in ineligible if c["food_category"] == "DAIRY")
        assert dairy_cand["routing_provider"] == "HAVERSINE_FALLBACK"
        assert dairy_cand["transit_feasibility"] == "UNKNOWN"
        assert any("Road routing query skipped" in w for w in dairy_cand["warnings"])


def test_demand_matching_skips_osrm_for_incompatible_listings(client):
    """DEF-FE-002: Ensure find_candidates_for_demand also skips road routing for incompatible listings."""
    data = setup_matching_scenario(client)
    demand2_id = data["demand2_id"]  # DAIRY demand
    headers = data["rec2_headers"]

    with patch("app.matching.matching_service.routing_service.estimate_route") as mock_estimate:
        res = client.get(
            f"/api/v1/matching/demands/{demand2_id}/candidates?include_ineligible=true",
            headers=headers,
        )
        assert res.status_code == 200
        body = res.json()

        # The listing in setup_matching_scenario is FRUITS, which is incompatible with DAIRY demand
        # Thus, estimate_route must NEVER be called for the incompatible listing!
        assert mock_estimate.call_count == 0

        # The candidate must be returned as ineligible with fallback routing
        candidates = body["candidates"]
        assert len(candidates) >= 1
        assert candidates[0]["is_eligible"] is False
        assert candidates[0]["routing_provider"] == "HAVERSINE_FALLBACK"
        assert any("Road routing query skipped" in w for w in candidates[0]["warnings"])

