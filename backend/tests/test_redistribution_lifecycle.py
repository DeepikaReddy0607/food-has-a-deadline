import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from fastapi import HTTPException

from app.models.food import SurplusListing, DemandRequest
from app.models.user import User, SupplierProfile, ReceiverProfile
from app.models.redistribution import (
    AllocationProposal,
    AllocationItem,
    RedistributionTransaction,
    TransactionStatusHistory,
)
from app.models.audit import AuditLog
from app.core.security import hash_password, create_access_token
from app.redistribution.state_machine import (
    ProposalStatus,
    TransactionStatus,
    validate_proposal_transition,
    validate_transaction_transition,
)
from app.redistribution.models import (
    ApproveProposalRequest,
    RejectProposalRequest,
    UpdateTransactionStatusRequest,
)
from app.redistribution.transaction_service import TransactionService


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def coordinator_user(db_session):
    u = User(
        email="coordinator@fhd.org",
        hashed_password=hash_password("CoordSecret123!"),
        role="COORDINATOR",
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def supplier_user(db_session):
    u = User(
        email="donor@bakery.org",
        hashed_password=hash_password("SupplierPass123!"),
        role="SUPPLIER",
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    profile = SupplierProfile(
        user_id=u.id,
        organization_name="Sunrise Artisan Bakery",
        contact_phone="+61391112222",
        facility_type="RESTAURANT",
        address="100 Bakery Lane",
        latitude=Decimal("-37.8100"),
        longitude=Decimal("144.9600"),
    )
    db_session.add(profile)
    db_session.commit()
    return u


@pytest.fixture
def receiver_user(db_session):
    u = User(
        email="shelter@kitchen.org",
        hashed_password=hash_password("ReceiverPass123!"),
        role="RECEIVER",
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    profile = ReceiverProfile(
        user_id=u.id,
        organization_name="Northside Food Center",
        contact_phone="+61393334444",
        receiver_category="SHELTER",
        capacity_daily_kg=Decimal("1000.0"),
        priority_level=4,
        address="200 Shelter Road",
        latitude=Decimal("-37.8200"),
        longitude=Decimal("144.9700"),
    )
    db_session.add(profile)
    db_session.commit()
    return u


@pytest.fixture
def base_proposal_scenario(db_session, coordinator_user, supplier_user, receiver_user):
    now = datetime.now(timezone.utc)
    # Surplus Listing: 100 kg available, expires in 24 hours
    surplus = SurplusListing(
        supplier_id=supplier_user.supplier_profile.id,
        item_name="Fresh Ciabatta Loaves",
        food_category="BAKERY",
        initial_quantity_kg=Decimal("100.00"),
        remaining_quantity_kg=Decimal("100.00"),
        storage_condition="AMBIENT",
        food_condition="GOOD",
        harvest_or_prep_date=now - timedelta(hours=3),
        estimated_deadline=now + timedelta(hours=24),
        status="ACTIVE",
    )
    db_session.add(surplus)

    # Demand Request: 60 kg requested, 0 fulfilled, needed within 36 hours
    demand = DemandRequest(
        receiver_id=receiver_user.receiver_profile.id,
        item_name="Daily Bread Distribution",
        food_category="BAKERY",
        requested_quantity_kg=Decimal("60.00"),
        fulfilled_quantity_kg=Decimal("0.00"),
        storage_capability="AMBIENT",
        priority_weight=4,
        required_by=now + timedelta(hours=36),
        status="OPEN",
    )
    db_session.add(demand)
    db_session.flush()

    # Draft Proposal: allocating 60 kg
    proposal = AllocationProposal(
        generated_by_user_id=coordinator_user.id,
        status="PENDING_REVIEW",
        total_allocated_kg=Decimal("60.00"),
        total_unallocated_kg=Decimal("40.00"),
        total_unmet_demand_kg=Decimal("0.00"),
        estimated_total_transit_km=Decimal("8.50"),
        ai_justification="Optimal match based on ambient bread compatibility and urgency.",
        solver_status="OPTIMAL",
    )
    db_session.add(proposal)
    db_session.flush()

    item = AllocationItem(
        proposal_id=proposal.id,
        surplus_listing_id=surplus.id,
        demand_request_id=demand.id,
        allocated_quantity_kg=Decimal("60.00"),
        estimated_distance_km=Decimal("8.50"),
        estimated_transit_minutes=18,
        urgency_at_allocation="HIGH",
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(surplus)
    db_session.refresh(demand)
    db_session.refresh(proposal)

    return surplus, demand, proposal


# =============================================================================
# 12 PRIORITY MODULE 10 TESTS
# =============================================================================

class TestRedistributionLifecycle:

    # 1. Valid proposal approval
    def test_valid_proposal_approval(self, db_session, coordinator_user, base_proposal_scenario):
        surplus, demand, proposal = base_proposal_scenario

        req = ApproveProposalRequest(dispatch_notes="Leave at Loading Dock 2")
        tx = TransactionService.approve_proposal(
            db=db_session,
            proposal_id=proposal.id,
            current_user=coordinator_user,
            request=req,
        )

        assert tx is not None
        assert tx.status == "APPROVED"
        assert tx.proposal_id == proposal.id
        assert tx.tracking_code.startswith("FHD-TX-")
        assert tx.total_allocated_kg == 60.0
        assert tx.dispatch_notes == "Leave at Loading Dock 2"
        assert len(tx.status_history) == 1
        assert tx.status_history[0].new_status == "APPROVED"

        # Check proposal status
        db_session.refresh(proposal)
        assert proposal.status == "APPROVED"

    # 2. Proposal rejection with mandatory reason
    def test_proposal_rejection_with_reason(self, db_session, coordinator_user, base_proposal_scenario):
        surplus, demand, proposal = base_proposal_scenario

        req = RejectProposalRequest(reason="Receiver facility reported power disruption today.")
        res = TransactionService.reject_proposal(
            db=db_session,
            proposal_id=proposal.id,
            current_user=coordinator_user,
            request=req,
        )

        assert res.status == "REJECTED"
        assert res.rejection_reason == "Receiver facility reported power disruption today."

        db_session.refresh(proposal)
        assert proposal.status == "REJECTED"
        assert proposal.rejection_reason == "Receiver facility reported power disruption today."

        # Audit log written
        audit = db_session.query(AuditLog).filter(
            AuditLog.entity_id == str(proposal.id),
            AuditLog.action == "PROPOSAL_REJECTED",
        ).first()
        assert audit is not None
        assert audit.details["reason"] == "Receiver facility reported power disruption today."

    # 3. Unauthorized approval rejected (SUPPLIER cannot approve)
    def test_unauthorized_approval_rejected(self, db_session, supplier_user, base_proposal_scenario):
        surplus, demand, proposal = base_proposal_scenario

        with pytest.raises(HTTPException) as exc_info:
            TransactionService.approve_proposal(
                db=db_session,
                proposal_id=proposal.id,
                current_user=supplier_user,
                request=ApproveProposalRequest(),
            )
        assert exc_info.value.status_code == 403
        assert "Authorization Denied" in exc_info.value.detail

    # 4. Expired listing during approval triggers revalidation conflict
    def test_expired_listing_revalidation_failure(self, db_session, coordinator_user, base_proposal_scenario):
        surplus, demand, proposal = base_proposal_scenario

        # Simulate time passing and listing expiring before coordinator approves
        surplus.estimated_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            TransactionService.approve_proposal(
                db=db_session,
                proposal_id=proposal.id,
                current_user=coordinator_user,
                request=ApproveProposalRequest(),
            )
        assert exc_info.value.status_code == 409
        assert "has expired" in exc_info.value.detail

        # Verify proposal remains PENDING_REVIEW and no transaction was created
        db_session.refresh(proposal)
        assert proposal.status == "PENDING_REVIEW"
        assert proposal.transaction is None

    # 5. Insufficient inventory during approval
    def test_insufficient_inventory_revalidation_failure(self, db_session, coordinator_user, base_proposal_scenario):
        surplus, demand, proposal = base_proposal_scenario

        # Simulate another order partially taking inventory, leaving only 20 kg
        surplus.remaining_quantity_kg = Decimal("20.00")
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            TransactionService.approve_proposal(
                db=db_session,
                proposal_id=proposal.id,
                current_user=coordinator_user,
                request=ApproveProposalRequest(),
            )
        assert exc_info.value.status_code == 409
        assert "Insufficient inventory" in exc_info.value.detail

    # 6. Duplicate execution prevention
    def test_duplicate_execution_prevention(self, db_session, coordinator_user, base_proposal_scenario):
        surplus, demand, proposal = base_proposal_scenario

        # First approval
        tx1 = TransactionService.approve_proposal(
            db=db_session,
            proposal_id=proposal.id,
            current_user=coordinator_user,
            request=ApproveProposalRequest(),
        )
        assert tx1.status == "APPROVED"

        # Advance to completed
        tx_rec = db_session.query(RedistributionTransaction).filter_by(id=tx1.id).first()
        tx_rec.status = "COMPLETED"
        proposal.status = "COMPLETED"
        db_session.commit()

        # Attempting second approval on completed proposal
        with pytest.raises(HTTPException) as exc_info:
            TransactionService.approve_proposal(
                db=db_session,
                proposal_id=proposal.id,
                current_user=coordinator_user,
                request=ApproveProposalRequest(),
            )
        assert exc_info.value.status_code == 409
        assert "COMPLETED" in exc_info.value.detail

    # 7. Inventory and demand updated correctly upon approval
    def test_inventory_and_demand_updated_correctly(self, db_session, coordinator_user, base_proposal_scenario):
        surplus, demand, proposal = base_proposal_scenario
        assert surplus.remaining_quantity_kg == Decimal("100.00")
        assert demand.fulfilled_quantity_kg == Decimal("0.00")

        TransactionService.approve_proposal(
            db=db_session,
            proposal_id=proposal.id,
            current_user=coordinator_user,
            request=ApproveProposalRequest(),
        )

        db_session.refresh(surplus)
        db_session.refresh(demand)

        # 100 - 60 = 40 kg remaining, still ACTIVE
        assert surplus.remaining_quantity_kg == Decimal("40.00")
        assert surplus.status == "ACTIVE"

        # 0 + 60 = 60 kg fulfilled, requested was 60 kg -> FULFILLED!
        assert demand.fulfilled_quantity_kg == Decimal("60.00")
        assert demand.status == "FULFILLED"

    # 8. Full depletion status handling
    def test_full_depletion_status_transition(self, db_session, coordinator_user, base_proposal_scenario):
        surplus, demand, proposal = base_proposal_scenario
        # Allocate entire 100 kg
        proposal.items[0].allocated_quantity_kg = Decimal("100.00")
        demand.requested_quantity_kg = Decimal("100.00")
        db_session.commit()

        TransactionService.approve_proposal(
            db=db_session,
            proposal_id=proposal.id,
            current_user=coordinator_user,
            request=ApproveProposalRequest(),
        )

        db_session.refresh(surplus)
        db_session.refresh(demand)
        assert surplus.remaining_quantity_kg == Decimal("0.00")
        assert surplus.status == "DEPLETED"
        assert demand.status == "FULFILLED"

    # 9. Transaction history recorded
    def test_transaction_status_history_recording(self, db_session, coordinator_user, base_proposal_scenario):
        surplus, demand, proposal = base_proposal_scenario

        tx = TransactionService.approve_proposal(
            db=db_session,
            proposal_id=proposal.id,
            current_user=coordinator_user,
            request=ApproveProposalRequest(),
        )

        # Execute dispatch
        tx_exec = TransactionService.execute_transaction(
            db=db_session,
            transaction_id=tx.id,
            current_user=coordinator_user,
        )
        assert tx_exec.status == "PICKUP_SCHEDULED"

        # Update to IN_TRANSIT
        tx_transit = TransactionService.update_transaction_status(
            db=db_session,
            transaction_id=tx.id,
            current_user=coordinator_user,
            request=UpdateTransactionStatusRequest(status="IN_TRANSIT", reason="Driver en route"),
        )
        assert tx_transit.status == "IN_TRANSIT"

        # Check history progression
        history = (
            db_session.query(TransactionStatusHistory)
            .filter(TransactionStatusHistory.transaction_id == tx.id)
            .order_by(TransactionStatusHistory.changed_at.asc())
            .all()
        )
        assert len(history) == 3
        assert history[0].new_status == "APPROVED"
        assert history[1].new_status == "PICKUP_SCHEDULED"
        assert history[2].new_status == "IN_TRANSIT"
        assert history[2].reason == "Driver en route"

    # 10. Rollback on execution failure (integrity preserved)
    def test_rollback_on_execution_failure(self, db_session, coordinator_user, base_proposal_scenario):
        surplus, demand, proposal = base_proposal_scenario

        # Corrupt demand status right before approval to trigger mid-flight failure
        demand.status = "CANCELLED"
        db_session.commit()

        try:
            TransactionService.approve_proposal(
                db=db_session,
                proposal_id=proposal.id,
                current_user=coordinator_user,
                request=ApproveProposalRequest(),
            )
        except HTTPException:
            pass

        db_session.refresh(surplus)
        db_session.refresh(proposal)

        # Verify surplus inventory was not decremented
        assert surplus.remaining_quantity_kg == Decimal("100.00")
        assert proposal.status == "PENDING_REVIEW"
        assert proposal.transaction is None

    # 11. Idempotent repeated requests
    def test_idempotent_repeated_approval(self, db_session, coordinator_user, base_proposal_scenario):
        surplus, demand, proposal = base_proposal_scenario

        # First approval
        tx1 = TransactionService.approve_proposal(
            db=db_session,
            proposal_id=proposal.id,
            current_user=coordinator_user,
            request=ApproveProposalRequest(),
        )

        db_session.refresh(surplus)
        qty_after_first = surplus.remaining_quantity_kg

        # Second approval (idempotent call)
        tx2 = TransactionService.approve_proposal(
            db=db_session,
            proposal_id=proposal.id,
            current_user=coordinator_user,
            request=ApproveProposalRequest(),
        )

        assert tx1.id == tx2.id
        assert tx1.tracking_code == tx2.tracking_code

        # Inventory must NOT be decremented a second time!
        db_session.refresh(surplus)
        assert surplus.remaining_quantity_kg == qty_after_first

    # 12. Invalid status transitions rejected
    def test_invalid_status_transitions_rejected(self, db_session, coordinator_user, base_proposal_scenario):
        surplus, demand, proposal = base_proposal_scenario

        tx = TransactionService.approve_proposal(
            db=db_session,
            proposal_id=proposal.id,
            current_user=coordinator_user,
            request=ApproveProposalRequest(),
        )

        # Directly jumping from APPROVED to DELIVERED without pickup or transit is invalid
        with pytest.raises(HTTPException) as exc_info:
            TransactionService.update_transaction_status(
                db=db_session,
                transaction_id=tx.id,
                current_user=coordinator_user,
                request=UpdateTransactionStatusRequest(status="DELIVERED"),
            )
        assert exc_info.value.status_code == 400
        assert "Invalid transaction status transition" in exc_info.value.detail

        # Proposal transition check
        with pytest.raises(HTTPException) as exc_proposal:
            validate_proposal_transition(current_status="REJECTED", target_status="APPROVED")
        assert exc_proposal.value.status_code == 400

    # 13. Cancellation post-pickup with 0 confirmed returned quantity does NOT restore inventory
    def test_cancellation_post_pickup_zero_returned_does_not_restore_inventory(
        self, db_session, coordinator_user, base_proposal_scenario
    ):
        surplus, demand, proposal = base_proposal_scenario
        initial_remaining = surplus.remaining_quantity_kg  # 100.0

        tx = TransactionService.approve_proposal(
            db=db_session,
            proposal_id=proposal.id,
            current_user=coordinator_user,
            request=ApproveProposalRequest(),
        )
        db_session.refresh(surplus)
        assert surplus.remaining_quantity_kg == Decimal("40.00")  # 100 - 60 allocated

        # Pick up food from warehouse
        TransactionService.update_transaction_status(
            db=db_session,
            transaction_id=tx.id,
            current_user=coordinator_user,
            request=UpdateTransactionStatusRequest(status="PICKED_UP"),
        )

        # Cancel in transit without confirmed returned food (e.g. refrigeration failed in van)
        TransactionService.update_transaction_status(
            db=db_session,
            transaction_id=tx.id,
            current_user=coordinator_user,
            request=UpdateTransactionStatusRequest(
                status="CANCELLED",
                reason="Van cooling unit broke down; batch spoiled in transit",
                confirmed_returned_kg=0.0,
            ),
        )

        # Food did NOT return to supplier; remaining quantity must STAY at 40.00!
        db_session.refresh(surplus)
        assert surplus.remaining_quantity_kg == Decimal("40.00")
        # Demand fulfilled quantity was rolled back because receiver never received it
        db_session.refresh(demand)
        assert demand.fulfilled_quantity_kg == Decimal("0.00")

    # 14. Cancellation post-pickup with partial confirmed returned restores ONLY confirmed amount
    def test_cancellation_post_pickup_partial_confirmed_returned(
        self, db_session, coordinator_user, base_proposal_scenario
    ):
        surplus, demand, proposal = base_proposal_scenario

        tx = TransactionService.approve_proposal(
            db=db_session,
            proposal_id=proposal.id,
            current_user=coordinator_user,
            request=ApproveProposalRequest(),
        )
        db_session.refresh(surplus)
        assert surplus.remaining_quantity_kg == Decimal("40.00")

        TransactionService.update_transaction_status(
            db=db_session,
            transaction_id=tx.id,
            current_user=coordinator_user,
            request=UpdateTransactionStatusRequest(status="PICKED_UP"),
        )

        # Cancel with only 25.0 kg confirmed returned intact (out of 60.0 kg allocated)
        TransactionService.update_transaction_status(
            db=db_session,
            transaction_id=tx.id,
            current_user=coordinator_user,
            request=UpdateTransactionStatusRequest(
                status="CANCELLED",
                reason="Partial return: 25 kg intact, 35 kg damaged",
                confirmed_returned_kg=25.0,
            ),
        )

        # Only the 25.0 kg physically returned is restored: 40.00 + 25.00 = 65.00 kg!
        db_session.refresh(surplus)
        assert surplus.remaining_quantity_kg == Decimal("65.00")

    # 15. Physically delivered transactions cannot be cancelled
    def test_delivered_transaction_cannot_be_cancelled(
        self, db_session, coordinator_user, base_proposal_scenario
    ):
        surplus, demand, proposal = base_proposal_scenario

        tx = TransactionService.approve_proposal(
            db=db_session,
            proposal_id=proposal.id,
            current_user=coordinator_user,
            request=ApproveProposalRequest(),
        )

        TransactionService.update_transaction_status(
            db=db_session,
            transaction_id=tx.id,
            current_user=coordinator_user,
            request=UpdateTransactionStatusRequest(status="PICKED_UP"),
        )
        TransactionService.update_transaction_status(
            db=db_session,
            transaction_id=tx.id,
            current_user=coordinator_user,
            request=UpdateTransactionStatusRequest(status="IN_TRANSIT"),
        )
        TransactionService.update_transaction_status(
            db=db_session,
            transaction_id=tx.id,
            current_user=coordinator_user,
            request=UpdateTransactionStatusRequest(status="DELIVERED"),
        )

        # Attempting to cancel already-delivered food must be rejected
        with pytest.raises(HTTPException) as exc_info:
            TransactionService.update_transaction_status(
                db=db_session,
                transaction_id=tx.id,
                current_user=coordinator_user,
                request=UpdateTransactionStatusRequest(status="CANCELLED"),
            )
        assert exc_info.value.status_code == 400
        assert (
            "cannot move from 'DELIVERED' to 'CANCELLED'" in exc_info.value.detail
            or "already been physically delivered" in exc_info.value.detail
        )

    # 16. Partial delivery credits ONLY actually delivered quantity toward demand
    def test_partial_delivery_adjusts_demand_fulfillment(
        self, db_session, coordinator_user, base_proposal_scenario
    ):
        surplus, demand, proposal = base_proposal_scenario

        tx = TransactionService.approve_proposal(
            db=db_session,
            proposal_id=proposal.id,
            current_user=coordinator_user,
            request=ApproveProposalRequest(),
        )

        TransactionService.update_transaction_status(
            db=db_session,
            transaction_id=tx.id,
            current_user=coordinator_user,
            request=UpdateTransactionStatusRequest(status="PICKED_UP"),
        )
        TransactionService.update_transaction_status(
            db=db_session,
            transaction_id=tx.id,
            current_user=coordinator_user,
            request=UpdateTransactionStatusRequest(status="IN_TRANSIT"),
        )

        # Receiver only accepts 45.0 kg out of 60.0 kg allocated (15 kg rejected)
        # and confirmed returned 15.0 kg back to supplier
        TransactionService.update_transaction_status(
            db=db_session,
            transaction_id=tx.id,
            current_user=coordinator_user,
            request=UpdateTransactionStatusRequest(
                status="DELIVERED",
                actual_delivered_kg=45.0,
                confirmed_returned_kg=15.0,
            ),
        )

        # Demand fulfilled quantity was adjusted down from 60.00 to 45.00
        db_session.refresh(demand)
        assert demand.fulfilled_quantity_kg == Decimal("45.00")
        assert demand.status == "PARTIALLY_FULFILLED"

        # Surplus was restored for the 15.0 kg returned: 40.00 + 15.00 = 55.00 kg!
        db_session.refresh(surplus)
        assert surplus.remaining_quantity_kg == Decimal("55.00")


# =============================================================================
# API ENDPOINT INTEGRATION TESTS
# =============================================================================

class TestRedistributionAPIEndpoints:
    def test_api_approve_proposal_flow(self, client, db_session, coordinator_user, base_proposal_scenario):
        surplus, demand, proposal = base_proposal_scenario
        token = create_access_token(subject=str(coordinator_user.id), role=coordinator_user.role)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post(
            f"/api/v1/optimization/proposals/{proposal.id}/approve",
            json={"dispatch_notes": "Urgent rescue pickup"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "APPROVED"
        assert data["tracking_code"].startswith("FHD-TX-")
        assert data["total_allocated_kg"] == 60.0

        # Query via GET /api/v1/transactions/{id}
        tx_id = data["id"]
        get_resp = client.get(f"/api/v1/transactions/{tx_id}", headers=headers)
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["id"] == tx_id
        assert get_data["tracking_code"] == data["tracking_code"]

        # List via GET /api/v1/transactions
        list_resp = client.get("/api/v1/transactions", headers=headers)
        assert list_resp.status_code == 200
        assert list_resp.json()["total_count"] >= 1

        # Advance status via POST /api/v1/transactions/{id}/execute
        exec_resp = client.post(
            f"/api/v1/transactions/{tx_id}/execute",
            headers=headers,
        )
        assert exec_resp.status_code == 200
        assert exec_resp.json()["status"] == "PICKUP_SCHEDULED"

        # Advance status via PATCH /api/v1/transactions/{id}/status
        patch_resp = client.patch(
            f"/api/v1/transactions/{tx_id}/status",
            json={"status": "IN_TRANSIT", "reason": "Driver dispatched"},
            headers=headers,
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["status"] == "IN_TRANSIT"

    def test_api_reject_proposal_flow(self, client, db_session, coordinator_user, base_proposal_scenario):
        surplus, demand, proposal = base_proposal_scenario
        token = create_access_token(subject=str(coordinator_user.id), role=coordinator_user.role)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post(
            f"/api/v1/optimization/proposals/{proposal.id}/reject",
            json={"reason": "Donor reported vehicle breakdown preventing pickup."},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "REJECTED"
        assert "Donor reported vehicle breakdown" in data["rejection_reason"]
