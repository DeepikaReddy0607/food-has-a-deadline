import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from sqlalchemy.exc import IntegrityError

from app.database.session import check_db_connection
from app.models.user import User, SupplierProfile, ReceiverProfile
from app.models.food import SurplusListing, DemandRequest
from app.models.redistribution import (
    AllocationProposal,
    AllocationItem,
    RedistributionTransaction,
    TransactionStatusHistory,
)
from app.models.audit import SimulationRun, AuditLog


def test_postgres_database_connection():
    """Verify live PostgreSQL database connectivity."""
    status = check_db_connection()
    assert status["connected"] is True
    assert status["status"] == "connected"


def test_user_and_profile_model_creation(db_session):
    """Test creating user, supplier, and receiver profile models with relationships."""
    # 1. Create Supplier User & Profile
    user_s = User(
        email="donor@market.org",
        hashed_password="dummy_hash_for_test",
        role="SUPPLIER",
    )
    db_session.add(user_s)
    db_session.commit()
    db_session.refresh(user_s)

    supplier_profile = SupplierProfile(
        user_id=user_s.id,
        organization_name="Green Harvest Foods",
        contact_phone="+1-555-1234",
        latitude=Decimal("37.7749"),
        longitude=Decimal("-122.4194"),
        address="100 Market St",
        facility_type="SUPERMARKET",
    )
    db_session.add(supplier_profile)
    db_session.commit()
    db_session.refresh(supplier_profile)

    assert user_s.supplier_profile.organization_name == "Green Harvest Foods"
    assert supplier_profile.user.email == "donor@market.org"

    # 2. Create Receiver User & Profile
    user_r = User(
        email="receiver@shelter.org",
        hashed_password="dummy_hash_for_test",
        role="RECEIVER",
    )
    db_session.add(user_r)
    db_session.commit()
    db_session.refresh(user_r)

    receiver_profile = ReceiverProfile(
        user_id=user_r.id,
        organization_name="Downtown Shelter",
        contact_phone="+1-555-5678",
        latitude=Decimal("37.7833"),
        longitude=Decimal("-122.4167"),
        address="200 Mission St",
        capacity_daily_kg=Decimal("450.00"),
        cold_storage_capabilities={"refrigeration": True, "freezer": False},
        priority_level=4,
    )
    db_session.add(receiver_profile)
    db_session.commit()
    db_session.refresh(receiver_profile)

    assert user_r.receiver_profile.capacity_daily_kg == Decimal("450.00")
    assert receiver_profile.user.email == "receiver@shelter.org"


def test_redistribution_lifecycle_models(db_session):
    """Test creating surplus, demand, proposals, items, transactions, and audit records."""
    # Setup users and profiles
    user_s = User(email="farm@donor.org", hashed_password="pw", role="SUPPLIER")
    user_r = User(email="pantry@rec.org", hashed_password="pw", role="RECEIVER")
    db_session.add_all([user_s, user_r])
    db_session.commit()

    supplier = SupplierProfile(
        user_id=user_s.id,
        organization_name="Valley Farm",
        contact_phone="123",
        latitude=Decimal("34.05"),
        longitude=Decimal("-118.25"),
        address="Farm Road",
        facility_type="FARM",
    )
    receiver = ReceiverProfile(
        user_id=user_r.id,
        organization_name="City Pantry",
        contact_phone="456",
        latitude=Decimal("34.08"),
        longitude=Decimal("-118.22"),
        address="Pantry Ave",
        capacity_daily_kg=Decimal("200.00"),
        cold_storage_capabilities={"refrigeration": True},
        priority_level=3,
    )
    db_session.add_all([supplier, receiver])
    db_session.commit()

    # Create SurplusListing
    now = datetime.now(timezone.utc)
    surplus = SurplusListing(
        supplier_id=supplier.id,
        food_category="PRODUCE",
        item_name="Organic Apples (Crates)",
        initial_quantity_kg=Decimal("100.00"),
        remaining_quantity_kg=Decimal("100.00"),
        storage_condition="AMBIENT",
        food_condition="EXCELLENT",
        harvest_or_prep_date=now - timedelta(days=1),
        estimated_deadline=now + timedelta(days=2),
        urgency_classification="MODERATE",
        status="AVAILABLE",
    )
    # Create DemandRequest
    demand = DemandRequest(
        receiver_id=receiver.id,
        food_category="PRODUCE",
        requested_quantity_kg=Decimal("60.00"),
        fulfilled_quantity_kg=Decimal("0.00"),
        dietary_requirements=["VEGAN"],
        storage_capability="AMBIENT",
        required_by=now + timedelta(days=1),
        priority_weight=3,
        status="ACTIVE",
    )
    db_session.add_all([surplus, demand])
    db_session.commit()

    # Create AllocationProposal and AllocationItem
    proposal = AllocationProposal(
        generated_by_user_id=user_s.id,
        status="PENDING_REVIEW",
        total_allocated_kg=Decimal("60.00"),
        total_unallocated_kg=Decimal("40.00"),
        total_unmet_demand_kg=Decimal("0.00"),
        estimated_total_transit_km=Decimal("4.50"),
        ai_justification="Feasible match within local transit radius.",
        solver_status="OPTIMAL",
    )
    db_session.add(proposal)
    db_session.commit()

    item = AllocationItem(
        proposal_id=proposal.id,
        surplus_listing_id=surplus.id,
        demand_request_id=demand.id,
        allocated_quantity_kg=Decimal("60.00"),
        estimated_distance_km=Decimal("4.50"),
        estimated_transit_minutes=15,
        urgency_at_allocation="MODERATE",
    )
    db_session.add(item)
    db_session.commit()

    # Create RedistributionTransaction & Status History
    tx = RedistributionTransaction(
        proposal_id=proposal.id,
        tracking_code="FHD-TEST-1234",
        status="SCHEDULED",
        dispatch_notes="Leave crates at loading dock A",
    )
    db_session.add(tx)
    db_session.commit()

    history = TransactionStatusHistory(
        transaction_id=tx.id,
        previous_status=None,
        new_status="SCHEDULED",
        changed_by_user_id=user_s.id,
        reason="Initial proposal accepted by coordinator",
    )
    db_session.add(history)
    db_session.commit()

    # Create SimulationRun and AuditLog
    sim = SimulationRun(
        user_id=user_s.id,
        scenario_type="TRANSIT_DELAY",
        disruption_parameters={"added_minutes": 30},
        baseline_results={"salvaged_kg": 60.0},
        simulated_results={"salvaged_kg": 60.0},
        impact_delta={"lost_salvage_kg": 0.0},
    )
    audit = AuditLog(
        user_id=user_s.id,
        action="CREATE_PROPOSAL",
        entity_name="allocation_proposals",
        entity_id=str(proposal.id),
        details={"status": "PENDING_REVIEW"},
        ip_address="127.0.0.1",
    )
    db_session.add_all([sim, audit])
    db_session.commit()

    # Assert all relationships navigate cleanly
    assert len(proposal.items) == 1
    assert proposal.items[0].allocated_quantity_kg == Decimal("60.00")
    assert tx.proposal.id == proposal.id
    assert len(tx.status_history) == 1
    assert tx.status_history[0].new_status == "SCHEDULED"


def test_unique_email_constraint(db_session):
    """Verify database raises IntegrityError when inserting duplicate emails."""
    u1 = User(email="duplicate@test.org", hashed_password="pw1", role="SUPPLIER")
    db_session.add(u1)
    db_session.commit()

    u2 = User(email="duplicate@test.org", hashed_password="pw2", role="RECEIVER")
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_check_constraints_role(db_session):
    """Verify check constraint rejects invalid role string."""
    invalid_user = User(
        email="invalid@role.org",
        hashed_password="pw",
        role="UNAUTHORIZED_ROLE",
    )
    db_session.add(invalid_user)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
