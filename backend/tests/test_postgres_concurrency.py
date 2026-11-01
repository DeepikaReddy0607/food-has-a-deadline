import uuid
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.database.session import check_db_connection
from app.models.user import User, SupplierProfile, ReceiverProfile
from app.models.food import SurplusListing, DemandRequest
from app.models.redistribution import (
    AllocationProposal,
    AllocationItem,
    RedistributionTransaction,
    TransactionStatusHistory,
)
from app.redistribution.transaction_service import TransactionService
from app.redistribution.models import ApproveProposalRequest


# Check if live PostgreSQL is reachable
db_status = check_db_connection()
is_postgres_available = db_status.get("connected", False)

pytestmark = pytest.mark.skipif(
    not is_postgres_available,
    reason="Live PostgreSQL database not available on localhost:5432",
)


@pytest.fixture(scope="module")
def pg_session_factory():
    """Provides a thread-safe sessionmaker connected directly to live PostgreSQL."""
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=10,
        max_overflow=5,
        pool_timeout=10,
    )
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def pg_coordinator(pg_session_factory):
    """Creates a real coordinator user in PostgreSQL for the test session."""
    session = pg_session_factory()
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"pg_coord_{uid.hex[:8]}@fhd-test.org",
        hashed_password="test_hashed_password",
        role="COORDINATOR",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    yield user

    # Teardown
    try:
        session.delete(user)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def _create_test_entities(session: Session, coordinator_id: uuid.UUID, initial_qty: float = 100.0):
    """Helper to create supplier, receiver, listing, and demand directly in PostgreSQL."""
    now = datetime.now(timezone.utc)
    uid = uuid.uuid4().hex[:8]

    # Supplier
    sup_user = User(
        id=uuid.uuid4(),
        email=f"sup_{uid}@test.org",
        hashed_password="pwd",
        role="SUPPLIER",
        is_active=True,
    )
    session.add(sup_user)
    session.flush()

    supplier = SupplierProfile(
        id=uuid.uuid4(),
        user_id=sup_user.id,
        organization_name=f"PG Supplier {uid}",
        contact_phone="+15551234567",
        facility_type="RETAILER",
        address="100 Market St",
        latitude=Decimal("37.774900"),
        longitude=Decimal("-122.419400"),
    )
    session.add(supplier)

    # Receiver
    rec_user = User(
        id=uuid.uuid4(),
        email=f"rec_{uid}@test.org",
        hashed_password="pwd",
        role="RECEIVER",
        is_active=True,
    )
    session.add(rec_user)
    session.flush()

    receiver = ReceiverProfile(
        id=uuid.uuid4(),
        user_id=rec_user.id,
        organization_name=f"PG Receiver {uid}",
        contact_phone="+15559876543",
        receiver_category="SOUP_KITCHEN",
        address="200 Shelter Way",
        latitude=Decimal("37.784900"),
        longitude=Decimal("-122.409400"),
        capacity_daily_kg=Decimal("500.00"),
    )
    session.add(receiver)
    session.flush()

    # Listing
    listing = SurplusListing(
        id=uuid.uuid4(),
        supplier_id=supplier.id,
        food_category="COOKED_FOOD",
        item_name=f"PG Meals {uid}",
        initial_quantity_kg=Decimal(str(initial_qty)),
        remaining_quantity_kg=Decimal(str(initial_qty)),
        storage_condition="AMBIENT",
        food_condition="GOOD",
        harvest_or_prep_date=now - timedelta(hours=2),
        estimated_deadline=now + timedelta(hours=10),
        status="ACTIVE",
    )
    session.add(listing)

    # Demand
    demand = DemandRequest(
        id=uuid.uuid4(),
        receiver_id=receiver.id,
        food_category="COOKED_FOOD",
        requested_quantity_kg=Decimal("150.00"),
        fulfilled_quantity_kg=Decimal("0.00"),
        storage_capability="AMBIENT",
        acceptable_food_condition="FAIR",
        required_by=now + timedelta(hours=8),
        status="ACTIVE",
    )
    session.add(demand)
    session.commit()

    return supplier, receiver, listing, demand


def _create_proposal(session: Session, coordinator_id: uuid.UUID, listing_id: uuid.UUID, demand_id: uuid.UUID, alloc_kg: float):
    now = datetime.now(timezone.utc)
    proposal = AllocationProposal(
        id=uuid.uuid4(),
        generated_by_user_id=coordinator_id,
        status="PENDING_REVIEW",
        total_allocated_kg=Decimal(str(alloc_kg)),
        total_unallocated_kg=Decimal("0.00"),
        total_unmet_demand_kg=Decimal("0.00"),
        estimated_total_transit_km=Decimal("5.0"),
        solver_status="OPTIMAL",
        created_at=now,
    )
    session.add(proposal)
    session.flush()

    item = AllocationItem(
        id=uuid.uuid4(),
        proposal_id=proposal.id,
        surplus_listing_id=listing_id,
        demand_request_id=demand_id,
        allocated_quantity_kg=Decimal(str(alloc_kg)),
        estimated_distance_km=Decimal("5.0"),
        estimated_transit_minutes=15,
        urgency_at_allocation="HIGH",
        created_at=now,
    )
    session.add(item)
    session.commit()
    session.refresh(proposal)
    return proposal


class TestPostgresConcurrency:
    """
    Rigorously tests PostgreSQL-specific concurrency, multithreading, and row-level
    locking behavior under simultaneous, conflicting requests.
    """

    def test_pg_concurrent_proposal_approvals_same_listing(
        self, pg_session_factory, pg_coordinator
    ):
        """
        Scenario 1: Two separate proposals compete for the EXACT SAME 50 kg surplus listing.
        Two worker threads concurrently attempt to approve Proposal A and Proposal B.
        PostgreSQL SELECT ... FOR UPDATE must ensure exactly ONE succeeds and ONE fails with 409 Conflict.
        """
        setup_session = pg_session_factory()
        supplier, receiver, listing, demand = _create_test_entities(setup_session, pg_coordinator.id, initial_qty=50.0)

        # Create Proposal 1 (wants 50 kg)
        p1 = _create_proposal(setup_session, pg_coordinator.id, listing.id, demand.id, alloc_kg=50.0)
        # Create Proposal 2 (also wants 50 kg)
        p2 = _create_proposal(setup_session, pg_coordinator.id, listing.id, demand.id, alloc_kg=50.0)

        p1_id = p1.id
        p2_id = p2.id
        listing_id = listing.id
        setup_session.close()

        results = {}

        def attempt_approval(proposal_id, thread_name):
            thread_session = pg_session_factory()
            try:
                tx = TransactionService.approve_proposal(
                    db=thread_session,
                    proposal_id=proposal_id,
                    current_user=pg_coordinator,
                    request=ApproveProposalRequest(dispatch_notes=f"Approved by {thread_name}"),
                )
                results[thread_name] = ("SUCCESS", tx.tracking_code)
            except HTTPException as e:
                results[thread_name] = ("CONFLICT", e.status_code, e.detail)
            except Exception as e:
                results[thread_name] = ("ERROR", str(e))
            finally:
                thread_session.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(attempt_approval, p1_id, "Thread_P1")
            f2 = executor.submit(attempt_approval, p2_id, "Thread_P2")
            f1.result()
            f2.result()

        # Exactly one must have succeeded and one must have received HTTP 409 Conflict!
        statuses = [res[0] for res in results.values()]
        assert statuses.count("SUCCESS") == 1
        assert statuses.count("CONFLICT") == 1

        conflict_result = next(res for res in results.values() if res[0] == "CONFLICT")
        assert conflict_result[1] == 409
        assert (
            "Insufficient inventory" in conflict_result[2]
            or "no longer available" in conflict_result[2]
        )

        # Verify final state in PostgreSQL: remaining quantity must be exactly 0.00 kg!
        verify_session = pg_session_factory()
        updated_listing = verify_session.query(SurplusListing).filter(SurplusListing.id == listing.id).one()
        assert updated_listing.remaining_quantity_kg == Decimal("0.00")
        assert updated_listing.status == "DEPLETED"
        verify_session.close()

    def test_pg_simultaneous_attempts_to_consume_same_listing(
        self, pg_session_factory, pg_coordinator
    ):
        """
        Scenario 2: Listing has 40 kg. P1 asks for 30 kg, P2 asks for 30 kg.
        Both run concurrently. Exactly one succeeds, one gets 409.
        Final inventory must be 10.00 kg (never negative!).
        """
        setup_session = pg_session_factory()
        supplier, receiver, listing, demand = _create_test_entities(setup_session, pg_coordinator.id, initial_qty=40.0)

        p1 = _create_proposal(setup_session, pg_coordinator.id, listing.id, demand.id, alloc_kg=30.0)
        p2 = _create_proposal(setup_session, pg_coordinator.id, listing.id, demand.id, alloc_kg=30.0)
        p1_id = p1.id
        p2_id = p2.id
        listing_id = listing.id
        setup_session.close()

        results = {}

        def attempt_approval(proposal_id, thread_name):
            thread_session = pg_session_factory()
            try:
                tx = TransactionService.approve_proposal(
                    db=thread_session,
                    proposal_id=proposal_id,
                    current_user=pg_coordinator,
                    request=ApproveProposalRequest(),
                )
                results[thread_name] = ("SUCCESS", tx.tracking_code)
            except HTTPException as e:
                results[thread_name] = ("CONFLICT", e.status_code, e.detail)
            finally:
                thread_session.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(attempt_approval, p1_id, "T1")
            f2 = executor.submit(attempt_approval, p2_id, "T2")
            f1.result()
            f2.result()

        statuses = [res[0] for res in results.values()]
        assert statuses.count("SUCCESS") == 1
        assert statuses.count("CONFLICT") == 1

        verify_session = pg_session_factory()
        updated_listing = verify_session.query(SurplusListing).filter(SurplusListing.id == listing_id).one()
        assert updated_listing.remaining_quantity_kg == Decimal("10.00")
        assert updated_listing.status == "ACTIVE"
        verify_session.close()

    def test_pg_duplicate_execution_requests_idempotency(
        self, pg_session_factory, pg_coordinator
    ):
        """
        Scenario 3: Two concurrent threads execute approval on the EXACT SAME proposal.
        Both threads must succeed without error, return the same tracking code, and
        the inventory must be decremented ONLY ONCE!
        """
        setup_session = pg_session_factory()
        supplier, receiver, listing, demand = _create_test_entities(setup_session, pg_coordinator.id, initial_qty=100.0)
        p = _create_proposal(setup_session, pg_coordinator.id, listing.id, demand.id, alloc_kg=40.0)
        p_id = p.id
        listing_id = listing.id
        setup_session.close()

        results = {}

        def attempt_approval(thread_name):
            thread_session = pg_session_factory()
            try:
                tx = TransactionService.approve_proposal(
                    db=thread_session,
                    proposal_id=p_id,
                    current_user=pg_coordinator,
                    request=ApproveProposalRequest(),
                )
                results[thread_name] = ("SUCCESS", tx.id, tx.tracking_code)
            except Exception as e:
                results[thread_name] = ("ERROR", str(e))
            finally:
                thread_session.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(attempt_approval, "T1")
            f2 = executor.submit(attempt_approval, "T2")
            f1.result()
            f2.result()

        assert results["T1"][0] == "SUCCESS"
        assert results["T2"][0] == "SUCCESS"
        # Both must return the exact same transaction ID and tracking code
        assert results["T1"][1] == results["T2"][1]
        assert results["T1"][2] == results["T2"][2]

        # Inventory must be decremented ONLY ONCE: 100 - 40 = 60 kg!
        verify_session = pg_session_factory()
        updated_listing = verify_session.query(SurplusListing).filter(SurplusListing.id == listing_id).one()
        assert updated_listing.remaining_quantity_kg == Decimal("60.00")
        verify_session.close()

    def test_pg_concurrent_demand_fulfillment(
        self, pg_session_factory, pg_coordinator
    ):
        """
        Scenario 4: Demand has only 40 kg outstanding requirement.
        Two separate listings are offered in P1 (30 kg) and P2 (30 kg) for this same demand.
        Concurrently approved: one succeeds, one gets 409 Conflict (Over-fulfillment).
        """
        setup_session = pg_session_factory()
        now = datetime.now(timezone.utc)
        uid = uuid.uuid4().hex[:8]

        # Receiver with small demand
        rec_user = User(id=uuid.uuid4(), email=f"rec_{uid}@test.org", hashed_password="pwd", role="RECEIVER", is_active=True)
        setup_session.add(rec_user)
        setup_session.flush()
        receiver = ReceiverProfile(
            id=uuid.uuid4(),
            user_id=rec_user.id,
            organization_name=f"Rec {uid}",
            contact_phone="+15551112233",
            receiver_category="SHELTER",
            address="50 Shelter Rd",
            latitude=Decimal("37.780000"),
            longitude=Decimal("-122.410000"),
            capacity_daily_kg=Decimal("200.00"),
        )
        setup_session.add(receiver)
        setup_session.flush()

        demand = DemandRequest(
            id=uuid.uuid4(),
            receiver_id=receiver.id,
            food_category="DAIRY",
            requested_quantity_kg=Decimal("40.00"),
            fulfilled_quantity_kg=Decimal("0.00"),
            storage_capability="REFRIGERATED",
            acceptable_food_condition="FAIR",
            required_by=now + timedelta(hours=8),
            status="ACTIVE",
        )
        setup_session.add(demand)

        # Supplier with two listings
        sup_user = User(id=uuid.uuid4(), email=f"sup_{uid}@test.org", hashed_password="pwd", role="SUPPLIER", is_active=True)
        setup_session.add(sup_user)
        setup_session.flush()
        supplier = SupplierProfile(
            id=uuid.uuid4(),
            user_id=sup_user.id,
            organization_name=f"Sup {uid}",
            contact_phone="+15554445566",
            facility_type="DAIRY_FARM",
            address="75 Farm Lane",
            latitude=Decimal("37.770000"),
            longitude=Decimal("-122.420000"),
        )
        setup_session.add(supplier)
        setup_session.flush()

        l1 = SurplusListing(
            id=uuid.uuid4(), supplier_id=supplier.id, food_category="DAIRY", item_name="Milk Batch 1",
            initial_quantity_kg=Decimal("50.00"), remaining_quantity_kg=Decimal("50.00"),
            storage_condition="REFRIGERATED", food_condition="GOOD",
            harvest_or_prep_date=now - timedelta(hours=1), estimated_deadline=now + timedelta(hours=12), status="ACTIVE"
        )
        l2 = SurplusListing(
            id=uuid.uuid4(), supplier_id=supplier.id, food_category="DAIRY", item_name="Milk Batch 2",
            initial_quantity_kg=Decimal("50.00"), remaining_quantity_kg=Decimal("50.00"),
            storage_condition="REFRIGERATED", food_condition="GOOD",
            harvest_or_prep_date=now - timedelta(hours=1), estimated_deadline=now + timedelta(hours=12), status="ACTIVE"
        )
        setup_session.add_all([l1, l2])
        setup_session.commit()

        p1 = _create_proposal(setup_session, pg_coordinator.id, l1.id, demand.id, alloc_kg=30.0)
        p2 = _create_proposal(setup_session, pg_coordinator.id, l2.id, demand.id, alloc_kg=30.0)
        p1_id = p1.id
        p2_id = p2.id
        demand_id = demand.id
        setup_session.close()

        results = {}

        def attempt_approval(proposal_id, thread_name):
            thread_session = pg_session_factory()
            try:
                tx = TransactionService.approve_proposal(
                    db=thread_session,
                    proposal_id=proposal_id,
                    current_user=pg_coordinator,
                    request=ApproveProposalRequest(),
                )
                results[thread_name] = ("SUCCESS", tx.tracking_code)
            except HTTPException as e:
                results[thread_name] = ("CONFLICT", e.status_code, e.detail)
            finally:
                thread_session.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(attempt_approval, p1_id, "T1")
            f2 = executor.submit(attempt_approval, p2_id, "T2")
            f1.result()
            f2.result()

        statuses = [res[0] for res in results.values()]
        assert statuses.count("SUCCESS") == 1
        assert statuses.count("CONFLICT") == 1
        conflict_res = next(r for r in results.values() if r[0] == "CONFLICT")
        assert "Over-fulfillment" in conflict_res[2]

        verify_session = pg_session_factory()
        updated_demand = verify_session.query(DemandRequest).filter(DemandRequest.id == demand_id).one()
        assert updated_demand.fulfilled_quantity_kg == Decimal("30.00")
        assert updated_demand.status == "PARTIALLY_FULFILLED"
        verify_session.close()

    def test_pg_transaction_rollback(
        self, pg_session_factory, pg_coordinator, monkeypatch
    ):
        """
        Scenario 5: Transaction rollback test on PostgreSQL.
        If an unexpected error occurs during commit/audit creation, the entire PostgreSQL
        transaction must abort and rollback. Surplus remaining quantity and demand fulfilled
        quantity must remain completely untouched.
        """
        setup_session = pg_session_factory()
        supplier, receiver, listing, demand = _create_test_entities(setup_session, pg_coordinator.id, initial_qty=80.0)
        p = _create_proposal(setup_session, pg_coordinator.id, listing.id, demand.id, alloc_kg=40.0)
        p_id = p.id
        listing_id = listing.id
        demand_id = demand.id
        setup_session.close()

        # Simulate a crash right before db.commit() inside approve_proposal
        def crashing_commit(self):
            raise RuntimeError("Simulated network failure during database commit")

        test_session = pg_session_factory()
        monkeypatch.setattr(Session, "commit", crashing_commit)

        with pytest.raises(RuntimeError):
            TransactionService.approve_proposal(
                db=test_session,
                proposal_id=p_id,
                current_user=pg_coordinator,
                request=ApproveProposalRequest(),
            )
        test_session.rollback()
        test_session.close()

        # Verify PostgreSQL state: neither listing nor demand was modified
        verify_session = pg_session_factory()
        verified_listing = verify_session.query(SurplusListing).filter(SurplusListing.id == listing_id).one()
        verified_demand = verify_session.query(DemandRequest).filter(DemandRequest.id == demand_id).one()

        assert verified_listing.remaining_quantity_kg == Decimal("80.00")
        assert verified_demand.fulfilled_quantity_kg == Decimal("0.00")
        verify_session.close()
