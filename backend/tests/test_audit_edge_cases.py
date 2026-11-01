import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock
import pytest
from pydantic import ValidationError
from fastapi import HTTPException

from app.schemas.surplus import SurplusListingCreate
from app.schemas.demand import DemandRequestCreate
from app.geospatial.distance_calculator import validate_wgs84_coordinates
from app.geospatial.osrm_client import OSRMClient
from app.geospatial.routing_service import RoutingService
from app.intelligence.perishability_engine import PerishabilityEngine
from app.models.user import User, SupplierProfile, ReceiverProfile
from app.models.food import SurplusListing, DemandRequest
from app.models.redistribution import (
    AllocationProposal,
    AllocationItem,
    RedistributionTransaction,
)
from app.optimization.allocation_problem import (
    AllocationProblem,
    SurplusNode,
    DemandNode,
    to_hundredths_kg,
)
from app.optimization.proposal_explainer import ProposalExplainer
from app.optimization.ortools_solver import OrtoolsSolver
from app.redistribution.transaction_service import TransactionService
from app.redistribution.models import ApproveProposalRequest
from app.agent.response_builder import ResponseBuilder
from app.database.session import check_db_connection


# =============================================================================
# 1. QUANTITY VALIDATION TESTS (INVALID & NEGATIVE QUANTITIES)
# =============================================================================

class TestQuantityEdgeCases:
    def test_surplus_negative_quantity_rejected(self):
        """Negative initial_quantity_kg in surplus listing must raise ValidationError."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError) as exc:
            SurplusListingCreate(
                food_category="BAKERY",
                item_name="Artisan Bread",
                initial_quantity_kg=Decimal("-10.50"),
                harvest_or_prep_date=now - timedelta(hours=2),
                estimated_deadline=now + timedelta(hours=12),
                food_condition="GOOD",
                storage_condition="AMBIENT",
            )
        assert "greater than 0" in str(exc.value)

    def test_surplus_zero_quantity_rejected(self):
        """Zero initial_quantity_kg in surplus listing must raise ValidationError."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError) as exc:
            SurplusListingCreate(
                food_category="PRODUCE",
                item_name="Carrots",
                initial_quantity_kg=Decimal("0.00"),
                harvest_or_prep_date=now - timedelta(hours=2),
                estimated_deadline=now + timedelta(hours=12),
                food_condition="GOOD",
                storage_condition="AMBIENT",
            )
        assert "greater than 0" in str(exc.value)

    def test_demand_negative_quantity_rejected(self):
        """Negative requested_quantity_kg in demand request must raise ValidationError."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError) as exc:
            DemandRequestCreate(
                food_category="COOKED_FOOD",
                item_name="Hot Meals",
                requested_quantity_kg=Decimal("-50.0"),
                required_by=now + timedelta(hours=6),
                storage_capability="AMBIENT",
                priority_weight=4,
            )
        assert "greater than 0" in str(exc.value)

    def test_demand_zero_quantity_rejected(self):
        """Zero requested_quantity_kg in demand request must raise ValidationError."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError) as exc:
            DemandRequestCreate(
                food_category="DAIRY",
                item_name="Milk Jugs",
                requested_quantity_kg=Decimal("0.0"),
                required_by=now + timedelta(hours=6),
                storage_capability="REFRIGERATED",
                priority_weight=3,
            )
        assert "greater than 0" in str(exc.value)


# =============================================================================
# 2. EXPIRED LISTINGS EDGE CASES
# =============================================================================

class TestExpiredListingEdgeCases:
    def test_perishability_engine_expired_deadline(self):
        """Listing with deadline in the past must be classified as CRITICAL with remaining_hours <= 0."""
        past_deadline = datetime.now(timezone.utc) - timedelta(hours=3)
        res = PerishabilityEngine.evaluate(
            estimated_deadline=past_deadline,
            harvest_or_prep_date=past_deadline - timedelta(days=2),
            food_condition="FAIR",
            storage_condition="REFRIGERATED",
        )
        assert res.urgency == "CRITICAL"
        assert res.remaining_hours <= 0.0
        assert any("expired" in w.lower() for w in res.warnings)

    def test_approval_fails_for_expired_listing(self, db_session):
        """Attempting to approve a proposal containing an expired listing must fail revalidation with HTTP 409."""
        coordinator = User(email="coord_exp@fhd.org", hashed_password="pw", role="COORDINATOR")
        supplier = User(email="supp_exp@fhd.org", hashed_password="pw", role="SUPPLIER")
        receiver = User(email="recv_exp@fhd.org", hashed_password="pw", role="RECEIVER")
        db_session.add_all([coordinator, supplier, receiver])
        db_session.commit()

        sp = SupplierProfile(
            user_id=supplier.id,
            organization_name="Expired Dairy Supplier",
            contact_phone="+1-555-1000",
            latitude=Decimal("37.7749"),
            longitude=Decimal("-122.4194"),
            address="100 Market St",
            facility_type="SUPERMARKET",
        )
        rp = ReceiverProfile(
            user_id=receiver.id,
            organization_name="Expired Food Receiver",
            contact_phone="+1-555-2000",
            latitude=Decimal("37.7833"),
            longitude=Decimal("-122.4167"),
            address="200 Mission St",
            capacity_daily_kg=Decimal("500.0"),
            receiver_category="FOOD_BANK",
        )
        db_session.add_all([sp, rp])
        db_session.commit()

        now = datetime.now(timezone.utc)
        listing = SurplusListing(
            supplier_id=sp.id,
            food_category="DAIRY",
            item_name="Expired Yogurt",
            initial_quantity_kg=Decimal("20.0"),
            remaining_quantity_kg=Decimal("20.0"),
            harvest_or_prep_date=now - timedelta(days=5),
            estimated_deadline=now - timedelta(hours=1),
            food_condition="FAIR",
            storage_condition="REFRIGERATED",
            status="AVAILABLE",
        )
        demand = DemandRequest(
            receiver_id=rp.id,
            food_category="DAIRY",
            item_name="Dairy Request",
            requested_quantity_kg=Decimal("20.0"),
            fulfilled_quantity_kg=Decimal("0.0"),
            required_by=now + timedelta(hours=4),
            storage_capability="REFRIGERATED",
            status="ACTIVE",
            priority_weight=3,
        )
        db_session.add_all([listing, demand])
        db_session.commit()

        proposal = AllocationProposal(
            status="PENDING_REVIEW",
            solver_status="OPTIMAL",
            total_allocated_kg=Decimal("20.0"),
            total_unallocated_kg=Decimal("0.0"),
            total_unmet_demand_kg=Decimal("0.0"),
        )
        db_session.add(proposal)
        db_session.commit()

        item = AllocationItem(
            proposal_id=proposal.id,
            surplus_listing_id=listing.id,
            demand_request_id=demand.id,
            allocated_quantity_kg=Decimal("20.0"),
            estimated_distance_km=Decimal("5.0"),
            estimated_transit_minutes=15,
            urgency_at_allocation="CRITICAL",
        )
        db_session.add(item)
        db_session.commit()

        app_req = ApproveProposalRequest(dispatch_notes="Approve expired")
        with pytest.raises(HTTPException) as exc:
            TransactionService.approve_proposal(db_session, proposal.id, coordinator, app_req)
        assert exc.value.status_code == 409
        assert "has expired" in exc.value.detail


# =============================================================================
# 3. GEOSPATIAL COORDINATE VALIDATION & OSRM TIMEOUT EDGE CASES
# =============================================================================

class TestGeospatialEdgeCases:
    def test_invalid_and_out_of_bounds_coordinates(self):
        """Invalid coordinate numbers and bounds must raise ValueError."""
        # Latitude out of bounds (> 90 or < -90)
        with pytest.raises(ValueError, match="out of WGS84 bounds"):
            validate_wgs84_coordinates(95.0, 0.0)
        with pytest.raises(ValueError, match="out of WGS84 bounds"):
            validate_wgs84_coordinates(-90.1, 0.0)

        # Longitude out of bounds (> 180 or < -180)
        with pytest.raises(ValueError, match="out of WGS84 bounds"):
            validate_wgs84_coordinates(0.0, 185.0)
        with pytest.raises(ValueError, match="out of WGS84 bounds"):
            validate_wgs84_coordinates(0.0, -180.5)

    def test_osrm_timeout_triggers_circuity_fallback(self):
        """When OSRM router times out, routing service falls back to Haversine with 1.35x circuity."""
        mock_osrm = MagicMock(spec=OSRMClient)
        mock_osrm.get_driving_route.return_value = None  # Simulates OSRM failure/timeout

        service = RoutingService(osrm_client=mock_osrm)
        sup_id = uuid.uuid4()
        rec_id = uuid.uuid4()

        result = service.estimate_route(
            supplier_id=sup_id,
            receiver_id=rec_id,
            supplier_lat=37.7749,
            supplier_lon=-122.4194,
            dest_lat=37.8044,
            dest_lon=-122.2711,
            estimated_usable_deadline=datetime.now(timezone.utc) + timedelta(hours=5),
        )
        assert result.is_fallback is True
        assert result.routing_provider == "HAVERSINE_FALLBACK"
        assert result.road_distance_km > result.straight_line_distance_km
        assert any("fallback" in w.lower() for w in result.warnings)


# =============================================================================
# 4. MARKET MISMATCH EDGE CASES (NO COMPATIBLE SUPPLY / RECEIVERS)
# =============================================================================

class TestMarketMismatchEdgeCases:
    def test_no_compatible_supply_diagnostics(self):
        """Demand with zero available supply in its category produces NO_COMPATIBLE_SUPPLY diagnostic."""
        demand_id = uuid.uuid4()
        receiver_id = uuid.uuid4()

        problem = AllocationProblem(
            surplus_nodes={},
            demand_nodes={
                demand_id: DemandNode(
                    id=demand_id,
                    receiver_id=receiver_id,
                    receiver_name="Community Shelter",
                    food_category="COOKED_FOOD",
                    item_name="Hot Dinner",
                    requested_kg=50.0,
                    requested_hundredths_kg=to_hundredths_kg(50.0),
                    priority_level=4,
                )
            },
            eligible_edges={},
            all_evaluated_candidates=[],
        )

        unfulfilled = ProposalExplainer.diagnose_unfulfilled_demands(problem, allocations_kg={})
        assert len(unfulfilled) == 1
        assert unfulfilled[0].reason_code == "NO_COMPATIBLE_SUPPLY"
        assert "No active surplus listings in category 'COOKED_FOOD'" in unfulfilled[0].diagnostic_explanation

    def test_no_compatible_receiver_diagnostics(self):
        """Surplus listing with zero demands produces NO_COMPATIBLE_DEMAND diagnostic."""
        surplus_id = uuid.uuid4()
        supplier_id = uuid.uuid4()

        problem = AllocationProblem(
            surplus_nodes={
                surplus_id: SurplusNode(
                    id=surplus_id,
                    supplier_id=supplier_id,
                    supplier_name="Fresh Farm",
                    food_category="FRUITS",
                    item_name="Apples",
                    available_kg=100.0,
                    available_hundredths_kg=to_hundredths_kg(100.0),
                    urgency="HIGH",
                )
            },
            demand_nodes={},
            eligible_edges={},
            all_evaluated_candidates=[],
        )

        unallocated = ProposalExplainer.diagnose_unallocated_surplus(problem, allocations_kg={})
        assert len(unallocated) == 1
        assert unallocated[0].reason_code == "NO_COMPATIBLE_DEMAND"
        assert "No open receiver demands" in unallocated[0].diagnostic_explanation


# =============================================================================
# 5. DUPLICATE APPROVAL & CONCURRENT INVENTORY CONFLICTS
# =============================================================================

class TestConcurrencyAndLifecycleEdgeCases:
    def test_duplicate_approval_idempotent_behavior(self, db_session):
        """Calling approve twice on the same proposal returns the existing transaction idempotently."""
        coordinator = User(email="coord_dup@fhd.org", hashed_password="pw", role="COORDINATOR")
        supplier = User(email="supp_dup@fhd.org", hashed_password="pw", role="SUPPLIER")
        receiver = User(email="recv_dup@fhd.org", hashed_password="pw", role="RECEIVER")
        db_session.add_all([coordinator, supplier, receiver])
        db_session.commit()

        sp = SupplierProfile(
            user_id=supplier.id,
            organization_name="Bakery Supplier",
            contact_phone="+1-555-3000",
            latitude=Decimal("37.7749"),
            longitude=Decimal("-122.4194"),
            address="150 Bakery St",
            facility_type="BAKERY",
        )
        rp = ReceiverProfile(
            user_id=receiver.id,
            organization_name="Youth Center",
            contact_phone="+1-555-4000",
            latitude=Decimal("37.7850"),
            longitude=Decimal("-122.4100"),
            address="250 Youth Ave",
            capacity_daily_kg=Decimal("300.0"),
            receiver_category="COMMUNITY_CENTER",
        )
        db_session.add_all([sp, rp])
        db_session.commit()

        now = datetime.now(timezone.utc)
        listing = SurplusListing(
            supplier_id=sp.id,
            food_category="BAKERY",
            item_name="Croissants",
            initial_quantity_kg=Decimal("15.0"),
            remaining_quantity_kg=Decimal("15.0"),
            harvest_or_prep_date=now - timedelta(hours=2),
            estimated_deadline=now + timedelta(hours=10),
            food_condition="GOOD",
            storage_condition="AMBIENT",
            status="AVAILABLE",
        )
        demand = DemandRequest(
            receiver_id=rp.id,
            food_category="BAKERY",
            item_name="Breakfast pastries",
            requested_quantity_kg=Decimal("15.0"),
            fulfilled_quantity_kg=Decimal("0.0"),
            required_by=now + timedelta(hours=6),
            storage_capability="AMBIENT",
            status="ACTIVE",
            priority_weight=3,
        )
        db_session.add_all([listing, demand])
        db_session.commit()

        proposal = AllocationProposal(
            status="PENDING_REVIEW",
            solver_status="OPTIMAL",
            total_allocated_kg=Decimal("15.0"),
            total_unallocated_kg=Decimal("0.0"),
            total_unmet_demand_kg=Decimal("0.0"),
        )
        db_session.add(proposal)
        db_session.commit()

        item = AllocationItem(
            proposal_id=proposal.id,
            surplus_listing_id=listing.id,
            demand_request_id=demand.id,
            allocated_quantity_kg=Decimal("15.0"),
            estimated_distance_km=Decimal("3.0"),
            estimated_transit_minutes=10,
            urgency_at_allocation="HIGH",
        )
        db_session.add(item)
        db_session.commit()

        app_req = ApproveProposalRequest(dispatch_notes="First approval")
        tx1 = TransactionService.approve_proposal(db_session, proposal.id, coordinator, app_req)
        assert tx1 is not None
        assert proposal.status == "APPROVED"

        # Second approval attempt returns the existing transaction idempotently
        tx2 = TransactionService.approve_proposal(db_session, proposal.id, coordinator, app_req)
        assert tx2.id == tx1.id
        assert tx2.tracking_code == tx1.tracking_code

    def test_concurrent_inventory_conflict_insufficient_remaining(self, db_session):
        """If remaining inventory drops below allocated quantity before approval, revalidation must fail with HTTP 409."""
        coordinator = User(email="coord_conflict@fhd.org", hashed_password="pw", role="COORDINATOR")
        supplier = User(email="supp_conflict@fhd.org", hashed_password="pw", role="SUPPLIER")
        receiver = User(email="recv_conflict@fhd.org", hashed_password="pw", role="RECEIVER")
        db_session.add_all([coordinator, supplier, receiver])
        db_session.commit()

        sp = SupplierProfile(
            user_id=supplier.id,
            organization_name="Grain Supplier",
            contact_phone="+1-555-5000",
            latitude=Decimal("37.7749"),
            longitude=Decimal("-122.4194"),
            address="300 Silo Rd",
            facility_type="WAREHOUSE",
        )
        rp = ReceiverProfile(
            user_id=receiver.id,
            organization_name="Shelter Receiver",
            contact_phone="+1-555-6000",
            latitude=Decimal("37.7900"),
            longitude=Decimal("-122.4050"),
            address="400 Shelter Rd",
            capacity_daily_kg=Decimal("1000.0"),
            receiver_category="SOUP_KITCHEN",
        )
        db_session.add_all([sp, rp])
        db_session.commit()

        now = datetime.now(timezone.utc)
        listing = SurplusListing(
            supplier_id=sp.id,
            food_category="GRAINS",
            item_name="Rice Bags",
            initial_quantity_kg=Decimal("50.0"),
            remaining_quantity_kg=Decimal("10.0"),  # Only 10 kg remains!
            harvest_or_prep_date=now - timedelta(days=1),
            estimated_deadline=now + timedelta(days=2),
            food_condition="GOOD",
            storage_condition="AMBIENT",
            status="AVAILABLE",
        )
        demand = DemandRequest(
            receiver_id=rp.id,
            food_category="GRAINS",
            item_name="Pantry grains",
            requested_quantity_kg=Decimal("40.0"),
            fulfilled_quantity_kg=Decimal("0.0"),
            required_by=now + timedelta(days=1),
            storage_capability="AMBIENT",
            status="ACTIVE",
            priority_weight=3,
        )
        db_session.add_all([listing, demand])
        db_session.commit()

        # Proposal attempts to allocate 40 kg, but only 10 kg is remaining
        proposal = AllocationProposal(
            status="PENDING_REVIEW",
            solver_status="OPTIMAL",
            total_allocated_kg=Decimal("40.0"),
            total_unallocated_kg=Decimal("0.0"),
            total_unmet_demand_kg=Decimal("0.0"),
        )
        db_session.add(proposal)
        db_session.commit()

        item = AllocationItem(
            proposal_id=proposal.id,
            surplus_listing_id=listing.id,
            demand_request_id=demand.id,
            allocated_quantity_kg=Decimal("40.0"),
            estimated_distance_km=Decimal("4.0"),
            estimated_transit_minutes=12,
            urgency_at_allocation="MODERATE",
        )
        db_session.add(item)
        db_session.commit()

        app_req = ApproveProposalRequest(dispatch_notes="Approve over-allocated")
        with pytest.raises(HTTPException) as exc:
            TransactionService.approve_proposal(db_session, proposal.id, coordinator, app_req)
        assert exc.value.status_code == 409
        assert "Insufficient inventory" in exc.value.detail


# =============================================================================
# 6. EXTERNAL RESILIENCE (GEMINI FAILURE & DB DISCONNECTION)
# =============================================================================

class TestExternalServiceResilience:
    def test_gemini_api_failure_deterministic_fallback(self, db_session):
        """When Gemini API fails or is unconfigured, ResponseBuilder provides operational continuity."""
        coordinator = User(email="coord_fb@fhd.org", hashed_password="pw", role="COORDINATOR")
        db_session.add(coordinator)
        db_session.commit()

        # Test deterministic fallback for optimization inquiry
        text, tool_calls, tool_results, preview = ResponseBuilder.build_deterministic_fallback(
            user_text="Please optimize surplus distribution for our region",
            user=coordinator,
            db=db_session,
        )
        assert "Deterministic Assistance Mode" in text
        assert "Allocation Proposal" in text
        assert any(t.tool_name == "prepare_redistribution_proposal" for t in tool_calls)

    def test_database_disconnection_gracefully_handled(self):
        """When database engine connect fails, check_db_connection returns status=disconnected without raising."""
        with patch("app.database.session.engine.connect", side_effect=Exception("ConnectionRefusedError: Port 5432 down")):
            res = check_db_connection()
            assert res["connected"] is False
            assert res["status"] == "disconnected"
            assert "Database unreachable" in res["details"]
