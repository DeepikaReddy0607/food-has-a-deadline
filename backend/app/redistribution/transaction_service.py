import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from app.models.user import User
from app.models.food import SurplusListing, DemandRequest
from app.models.redistribution import (
    AllocationProposal,
    AllocationItem,
    RedistributionTransaction,
    TransactionStatusHistory,
)
from app.models.audit import AuditLog
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
    TransactionResponse,
    TransactionItemResponse,
    TransactionStatusHistoryResponse,
    TransactionListResponse,
    ProposalActionResponse,
)


class TransactionService:
    """
    Manages the human-controlled lifecycle for reviewing, approving, executing,
    and tracking food redistribution transactions with ACID guarantees, row-level
    locking, revalidation, and idempotent operations.
    """

    @classmethod
    def _verify_coordinator_role(cls, current_user: User) -> None:
        if current_user.role not in ("COORDINATOR", "ADMIN"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Authorization Denied: Role '{current_user.role}' is not permitted to approve or modify redistribution transactions.",
            )

    @classmethod
    def _build_transaction_response(cls, tx: RedistributionTransaction) -> TransactionResponse:
        items_responses: List[TransactionItemResponse] = []
        proposal = tx.proposal

        if proposal and proposal.items:
            for it in proposal.items:
                s_name = "Supplier Facility"
                r_name = "Receiver Facility"
                if it.surplus_listing and it.surplus_listing.supplier:
                    s_name = it.surplus_listing.supplier.organization_name
                if it.demand_request and it.demand_request.receiver:
                    r_name = it.demand_request.receiver.organization_name

                item_title = it.surplus_listing.item_name if it.surplus_listing else "Food Item"
                category = it.surplus_listing.food_category if it.surplus_listing else "OTHER"

                items_responses.append(
                    TransactionItemResponse(
                        item_id=it.id,
                        surplus_listing_id=it.surplus_listing_id,
                        demand_request_id=it.demand_request_id,
                        supplier_id=it.surplus_listing.supplier_id if it.surplus_listing else uuid.uuid4(),
                        receiver_id=it.demand_request.receiver_id if it.demand_request else uuid.uuid4(),
                        supplier_name=s_name,
                        receiver_name=r_name,
                        item_name=item_title,
                        food_category=category,
                        allocated_quantity_kg=float(it.allocated_quantity_kg),
                        estimated_distance_km=float(it.estimated_distance_km),
                        estimated_transit_minutes=it.estimated_transit_minutes,
                        urgency_at_allocation=it.urgency_at_allocation,
                    )
                )

        history_responses = [
            TransactionStatusHistoryResponse(
                id=h.id,
                previous_status=h.previous_status,
                new_status=h.new_status,
                changed_by_user_id=h.changed_by_user_id,
                reason=h.reason,
                changed_at=h.changed_at,
            )
            for h in tx.status_history
        ]

        total_kg = float(proposal.total_allocated_kg) if proposal else sum(i.allocated_quantity_kg for i in items_responses)

        return TransactionResponse(
            id=tx.id,
            proposal_id=tx.proposal_id,
            tracking_code=tx.tracking_code,
            status=tx.status,
            scheduled_pickup_at=tx.scheduled_pickup_at,
            actual_pickup_at=tx.actual_pickup_at,
            actual_delivery_at=tx.actual_delivery_at,
            dispatch_notes=tx.dispatch_notes,
            total_allocated_kg=round(total_kg, 2),
            items_count=len(items_responses),
            items=items_responses,
            status_history=history_responses,
            created_at=tx.created_at,
            updated_at=tx.updated_at,
        )

    # -------------------------------------------------------------------------
    # 1. APPROVE PROPOSAL & COMMIT TRANSACTIONS
    # -------------------------------------------------------------------------
    @classmethod
    def approve_proposal(
        cls,
        db: Session,
        proposal_id: uuid.UUID,
        current_user: User,
        request: ApproveProposalRequest,
    ) -> TransactionResponse:
        cls._verify_coordinator_role(current_user)

        # 1. Fetch & Exclusively Lock Proposal row (PostgreSQL MVCC concurrency lock)
        proposal = (
            db.query(AllocationProposal)
            .filter(AllocationProposal.id == proposal_id)
            .with_for_update()
            .first()
        )

        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Allocation proposal {proposal_id} not found.",
            )

        # 2. Idempotency Check: if already approved, return existing transaction
        if proposal.status in (ProposalStatus.APPROVED, ProposalStatus.ACCEPTED) and proposal.transaction:
            return cls._build_transaction_response(proposal.transaction)

        if proposal.status != ProposalStatus.PENDING_REVIEW:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot approve proposal: Proposal is currently in '{proposal.status}' status (must be 'PENDING_REVIEW').",
            )

        if not proposal.items or len(proposal.items) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot approve an empty proposal with zero allocation items.",
            )

        now = datetime.now(timezone.utc)

        # 3. Calculate cumulative allocations across items to prevent split-allocation overbooking
        total_per_surplus = defaultdict(Decimal)
        total_per_demand = defaultdict(Decimal)
        for item in proposal.items:
            total_per_surplus[item.surplus_listing_id] += Decimal(str(item.allocated_quantity_kg))
            total_per_demand[item.demand_request_id] += Decimal(str(item.allocated_quantity_kg))

        # 4. Revalidation & Row-Level Locking in strictly sorted order (eliminates PostgreSQL deadlocks)
        locked_surplus_map = {}
        for surplus_id in sorted(total_per_surplus.keys()):
            listing = (
                db.query(SurplusListing)
                .filter(SurplusListing.id == surplus_id)
                .with_for_update()
                .first()
            )
            if not listing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Surplus listing {surplus_id} referenced in proposal no longer exists.",
                )

            if listing.status not in ("ACTIVE", "AVAILABLE"):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Cannot approve proposal: Surplus listing '{listing.item_name}' (ID: {listing.id}) "
                        f"is no longer available (current status: {listing.status})."
                    ),
                )

            # Check expiration
            listing_deadline = listing.estimated_deadline
            if listing_deadline.tzinfo is None:
                listing_deadline = listing_deadline.replace(tzinfo=timezone.utc)

            if listing_deadline <= now:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Cannot approve proposal: Surplus listing '{listing.item_name}' (ID: {listing.id}) "
                        f"has expired (deadline was {listing.estimated_deadline.isoformat()})."
                    ),
                )

            # Check cumulative quantity availability
            required_surplus = total_per_surplus[surplus_id]
            if listing.remaining_quantity_kg < required_surplus:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Cannot approve proposal: Insufficient inventory for surplus listing '{listing.item_name}' "
                        f"(ID: {listing.id}). Cumulative allocated is {required_surplus} kg but only "
                        f"{listing.remaining_quantity_kg} kg remains available."
                    ),
                )
            locked_surplus_map[surplus_id] = listing

        locked_demand_map = {}
        for demand_id in sorted(total_per_demand.keys()):
            demand = (
                db.query(DemandRequest)
                .filter(DemandRequest.id == demand_id)
                .with_for_update()
                .first()
            )
            if not demand:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Demand request {demand_id} referenced in proposal no longer exists.",
                )

            if demand.status not in ("OPEN", "ACTIVE", "PARTIALLY_FULFILLED"):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Cannot approve proposal: Demand request '{demand.item_name or demand.food_category}' "
                        f"(ID: {demand.id}) is no longer open (current status: {demand.status})."
                    ),
                )

            # Check demand deadline
            demand_deadline = demand.required_by
            if demand_deadline.tzinfo is None:
                demand_deadline = demand_deadline.replace(tzinfo=timezone.utc)

            if demand_deadline <= now:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Cannot approve proposal: Demand request '{demand.item_name or demand.food_category}' "
                        f"(ID: {demand.id}) requirement deadline has expired."
                    ),
                )

            # Check cumulative demand fulfillment capacity
            required_demand = total_per_demand[demand_id]
            if demand.remaining_requirement_kg < required_demand:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Cannot approve proposal: Over-fulfillment for demand request "
                        f"'{demand.item_name or demand.food_category}' (ID: {demand.id}). "
                        f"Cumulative allocated is {required_demand} kg but outstanding requirement is only "
                        f"{demand.remaining_requirement_kg} kg."
                    ),
                )
            locked_demand_map[demand_id] = demand

        # 5. Atomic Execution: Decrement inventory and increment fulfilled demand
        for item in proposal.items:
            listing = locked_surplus_map[item.surplus_listing_id]
            demand = locked_demand_map[item.demand_request_id]

            new_rem_qty = round(listing.remaining_quantity_kg - item.allocated_quantity_kg, 2)
            listing.remaining_quantity_kg = new_rem_qty
            if listing.remaining_quantity_kg <= Decimal("0.00"):
                listing.remaining_quantity_kg = Decimal("0.00")
                listing.status = "DEPLETED"

            new_ful_qty = round(demand.fulfilled_quantity_kg + item.allocated_quantity_kg, 2)
            demand.fulfilled_quantity_kg = new_ful_qty
            if demand.fulfilled_quantity_kg >= demand.requested_quantity_kg:
                demand.fulfilled_quantity_kg = demand.requested_quantity_kg
                demand.status = "FULFILLED"
            else:
                demand.status = "PARTIALLY_FULFILLED"

        # 5. Create Redistribution Transaction
        tracking_code = f"FHD-TX-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        transaction = RedistributionTransaction(
            proposal_id=proposal.id,
            tracking_code=tracking_code,
            status=TransactionStatus.APPROVED,
            scheduled_pickup_at=request.scheduled_pickup_at,
            dispatch_notes=request.dispatch_notes,
        )
        db.add(transaction)
        db.flush()

        # 6. Record Status History
        history = TransactionStatusHistory(
            transaction_id=transaction.id,
            previous_status=None,
            new_status=TransactionStatus.APPROVED,
            changed_by_user_id=current_user.id,
            reason="Proposal approved and inventory committed by coordinator.",
        )
        db.add(history)

        # 7. Update Proposal Status
        proposal.status = ProposalStatus.APPROVED

        # 8. Append Immutable Audit Log
        audit = AuditLog(
            user_id=current_user.id,
            action="PROPOSAL_APPROVED",
            entity_name="allocation_proposals",
            entity_id=str(proposal.id),
            details={
                "transaction_id": str(transaction.id),
                "tracking_code": tracking_code,
                "total_allocated_kg": float(proposal.total_allocated_kg),
                "items_count": len(proposal.items),
                "dispatch_notes": request.dispatch_notes,
            },
        )
        db.add(audit)

        db.commit()
        db.refresh(transaction)
        return cls._build_transaction_response(transaction)

    # -------------------------------------------------------------------------
    # 2. REJECT PROPOSAL
    # -------------------------------------------------------------------------
    @classmethod
    def reject_proposal(
        cls,
        db: Session,
        proposal_id: uuid.UUID,
        current_user: User,
        request: RejectProposalRequest,
    ) -> ProposalActionResponse:
        cls._verify_coordinator_role(current_user)

        proposal = db.query(AllocationProposal).filter(AllocationProposal.id == proposal_id).first()
        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Allocation proposal {proposal_id} not found.",
            )

        # Idempotent rejection
        if proposal.status == ProposalStatus.REJECTED:
            return ProposalActionResponse(
                proposal_id=proposal.id,
                status=proposal.status,
                message="Proposal was already rejected.",
                rejection_reason=proposal.rejection_reason,
                transaction=None,
            )

        if proposal.status != ProposalStatus.PENDING_REVIEW:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot reject proposal in '{proposal.status}' status (must be 'PENDING_REVIEW').",
            )

        proposal.status = ProposalStatus.REJECTED
        proposal.rejection_reason = request.reason

        audit = AuditLog(
            user_id=current_user.id,
            action="PROPOSAL_REJECTED",
            entity_name="allocation_proposals",
            entity_id=str(proposal.id),
            details={"reason": request.reason},
        )
        db.add(audit)

        db.commit()
        db.refresh(proposal)

        return ProposalActionResponse(
            proposal_id=proposal.id,
            status=proposal.status,
            message=f"Proposal {proposal.id} successfully rejected.",
            rejection_reason=proposal.rejection_reason,
            transaction=None,
        )

    # -------------------------------------------------------------------------
    # 3. EXECUTE APPROVED TRANSACTION
    # -------------------------------------------------------------------------
    @classmethod
    def execute_transaction(
        cls,
        db: Session,
        transaction_id: uuid.UUID,
        current_user: User,
    ) -> TransactionResponse:
        cls._verify_coordinator_role(current_user)

        tx = (
            db.query(RedistributionTransaction)
            .options(
                joinedload(RedistributionTransaction.proposal)
                .joinedload(AllocationProposal.items)
                .joinedload(AllocationItem.surplus_listing)
                .joinedload(SurplusListing.supplier),
                joinedload(RedistributionTransaction.proposal)
                .joinedload(AllocationProposal.items)
                .joinedload(AllocationItem.demand_request)
                .joinedload(DemandRequest.receiver),
                joinedload(RedistributionTransaction.status_history),
            )
            .filter(RedistributionTransaction.id == transaction_id)
            .first()
        )

        if not tx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Redistribution transaction {transaction_id} not found.",
            )

        # If already executing or in transit, return existing state
        if tx.status in (TransactionStatus.PICKUP_SCHEDULED, TransactionStatus.DISPATCHED, TransactionStatus.PICKED_UP):
            return cls._build_transaction_response(tx)

        if tx.status not in (TransactionStatus.APPROVED, TransactionStatus.SCHEDULED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot execute transaction in '{tx.status}' state. Must be 'APPROVED' or 'SCHEDULED'.",
            )

        old_status = tx.status
        new_status = TransactionStatus.PICKUP_SCHEDULED
        validate_transaction_transition(old_status, new_status)

        tx.status = new_status
        if tx.proposal:
            tx.proposal.status = ProposalStatus.EXECUTING

        history = TransactionStatusHistory(
            transaction_id=tx.id,
            previous_status=old_status,
            new_status=new_status,
            changed_by_user_id=current_user.id,
            reason="Coordinator triggered dispatch execution.",
        )
        db.add(history)

        audit = AuditLog(
            user_id=current_user.id,
            action="TRANSACTION_EXECUTED",
            entity_name="redistribution_transactions",
            entity_id=str(tx.id),
            details={"previous_status": old_status, "new_status": new_status},
        )
        db.add(audit)

        db.commit()
        db.refresh(tx)
        return cls._build_transaction_response(tx)

    # -------------------------------------------------------------------------
    # 4. UPDATE TRANSACTION STATUS & MILESTONES
    # -------------------------------------------------------------------------
    @classmethod
    def update_transaction_status(
        cls,
        db: Session,
        transaction_id: uuid.UUID,
        current_user: User,
        request: UpdateTransactionStatusRequest,
    ) -> TransactionResponse:
        cls._verify_coordinator_role(current_user)

        tx = (
            db.query(RedistributionTransaction)
            .options(
                joinedload(RedistributionTransaction.proposal)
                .joinedload(AllocationProposal.items)
                .joinedload(AllocationItem.surplus_listing),
                joinedload(RedistributionTransaction.proposal)
                .joinedload(AllocationProposal.items)
                .joinedload(AllocationItem.demand_request),
                joinedload(RedistributionTransaction.status_history),
            )
            .filter(RedistributionTransaction.id == transaction_id)
            .first()
        )

        if not tx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Redistribution transaction {transaction_id} not found.",
            )

        target_status = request.status.upper()
        old_status = tx.status

        # Validate allowed transition
        validate_transaction_transition(old_status, target_status)

        # Update timestamps
        now = datetime.now(timezone.utc)
        if request.actual_pickup_at:
            tx.actual_pickup_at = request.actual_pickup_at
        elif target_status in (TransactionStatus.PICKED_UP, TransactionStatus.DISPATCHED) and not tx.actual_pickup_at:
            tx.actual_pickup_at = now

        if request.actual_delivery_at:
            tx.actual_delivery_at = request.actual_delivery_at
        elif target_status in (TransactionStatus.DELIVERED, TransactionStatus.COMPLETED) and not tx.actual_delivery_at:
            tx.actual_delivery_at = now

        if request.dispatch_notes:
            tx.dispatch_notes = request.dispatch_notes

        tx.status = target_status

        # Synchronize proposal status
        if tx.proposal:
            if target_status == TransactionStatus.COMPLETED:
                tx.proposal.status = ProposalStatus.COMPLETED
            elif target_status == TransactionStatus.FAILED:
                tx.proposal.status = ProposalStatus.FAILED
            elif target_status == TransactionStatus.CANCELLED:
                tx.proposal.status = ProposalStatus.CANCELLED

        # ---------------------------------------------------------------------
        # PHYSICAL CUSTODY INTEGRITY & INVENTORY RESTORATION RULES
        # ---------------------------------------------------------------------
        # 1. Delivered / Completed transactions cannot be cancelled to restore inventory
        if old_status in (TransactionStatus.DELIVERED, TransactionStatus.COMPLETED):
            if target_status in (TransactionStatus.CANCELLED, TransactionStatus.FAILED):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot cancel or fail transaction: food has already been physically delivered to receiver (current status: {old_status}).",
                )

        # 2. Cancellation / Failure Handling
        if target_status in (TransactionStatus.CANCELLED, TransactionStatus.FAILED) and tx.proposal and tx.proposal.items:
            is_pre_pickup = old_status in (
                TransactionStatus.APPROVED,
                TransactionStatus.SCHEDULED,
                TransactionStatus.PICKUP_SCHEDULED,
            )
            is_post_pickup = old_status in (
                TransactionStatus.PICKED_UP,
                TransactionStatus.DISPATCHED,
                TransactionStatus.IN_TRANSIT,
            )
            total_allocated = Decimal(str(tx.proposal.total_allocated_kg))

            if is_pre_pickup:
                # Food has NOT physically left supplier facility. 100% of allocation remains at warehouse.
                for item in tx.proposal.items:
                    if item.surplus_listing_id:
                        listing = (
                            db.query(SurplusListing)
                            .filter(SurplusListing.id == item.surplus_listing_id)
                            .with_for_update()
                            .first()
                        )
                        if listing:
                            listing_deadline = listing.estimated_deadline
                            if listing_deadline.tzinfo is None:
                                listing_deadline = listing_deadline.replace(tzinfo=timezone.utc)

                            if listing_deadline <= now:
                                listing.status = "EXPIRED"
                            else:
                                listing.remaining_quantity_kg = round(
                                    listing.remaining_quantity_kg + item.allocated_quantity_kg, 2
                                )
                                if listing.status == "DEPLETED":
                                    listing.status = "ACTIVE"

                    if item.demand_request_id:
                        demand = (
                            db.query(DemandRequest)
                            .filter(DemandRequest.id == item.demand_request_id)
                            .with_for_update()
                            .first()
                        )
                        if demand:
                            demand.fulfilled_quantity_kg = round(
                                max(Decimal("0.00"), demand.fulfilled_quantity_kg - item.allocated_quantity_kg), 2
                            )
                            if demand.fulfilled_quantity_kg == Decimal("0.00"):
                                demand.status = "ACTIVE"
                            else:
                                demand.status = "PARTIALLY_FULFILLED"

            elif is_post_pickup:
                # Food has already departed the supplier warehouse!
                # Only physically confirmed returned quantities may be restored to available inventory.
                confirmed_returned = Decimal(str(request.confirmed_returned_kg or 0.0))
                if confirmed_returned > total_allocated:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Confirmed returned quantity ({confirmed_returned} kg) cannot exceed total allocated quantity ({total_allocated} kg).",
                    )

                # Demand was NOT received by receiver; decrement demand fulfilled quantity by full allocated quantity
                for item in tx.proposal.items:
                    if item.demand_request_id:
                        demand = (
                            db.query(DemandRequest)
                            .filter(DemandRequest.id == item.demand_request_id)
                            .with_for_update()
                            .first()
                        )
                        if demand:
                            demand.fulfilled_quantity_kg = round(
                                max(Decimal("0.00"), demand.fulfilled_quantity_kg - item.allocated_quantity_kg), 2
                            )
                            if demand.fulfilled_quantity_kg == Decimal("0.00"):
                                demand.status = "ACTIVE"
                            else:
                                demand.status = "PARTIALLY_FULFILLED"

                # Restore ONLY physically confirmed returned quantity to supplier inventory (if not expired)
                if confirmed_returned > Decimal("0.00"):
                    remaining_to_restore = confirmed_returned
                    for item in tx.proposal.items:
                        if remaining_to_restore <= Decimal("0.00"):
                            break
                        if item.surplus_listing_id:
                            listing = (
                                db.query(SurplusListing)
                                .filter(SurplusListing.id == item.surplus_listing_id)
                                .with_for_update()
                                .first()
                            )
                            if listing:
                                listing_deadline = listing.estimated_deadline
                                if listing_deadline.tzinfo is None:
                                    listing_deadline = listing_deadline.replace(tzinfo=timezone.utc)

                                restore_amt = min(remaining_to_restore, item.allocated_quantity_kg)
                                remaining_to_restore -= restore_amt

                                if listing_deadline <= now:
                                    listing.status = "EXPIRED"
                                else:
                                    listing.remaining_quantity_kg = round(
                                        listing.remaining_quantity_kg + restore_amt, 2
                                    )
                                    if listing.status == "DEPLETED":
                                        listing.status = "ACTIVE"

        # 3. Partial Delivery Handling at DELIVERED or COMPLETED
        if target_status in (TransactionStatus.DELIVERED, TransactionStatus.COMPLETED) and tx.proposal and tx.proposal.items:
            if request.actual_delivered_kg is not None:
                actual_delivered = Decimal(str(request.actual_delivered_kg))
                total_allocated = Decimal(str(tx.proposal.total_allocated_kg))
                if actual_delivered > total_allocated:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Actual delivered quantity ({actual_delivered} kg) cannot exceed allocated quantity ({total_allocated} kg).",
                    )
                if actual_delivered < total_allocated:
                    undelivered = total_allocated - actual_delivered
                    remaining_undelivered = undelivered
                    for item in tx.proposal.items:
                        if remaining_undelivered <= Decimal("0.00"):
                            break
                        if item.demand_request_id:
                            demand = (
                                db.query(DemandRequest)
                                .filter(DemandRequest.id == item.demand_request_id)
                                .with_for_update()
                                .first()
                            )
                            if demand:
                                reduce_amt = min(remaining_undelivered, item.allocated_quantity_kg)
                                remaining_undelivered -= reduce_amt
                                demand.fulfilled_quantity_kg = round(
                                    max(Decimal("0.00"), demand.fulfilled_quantity_kg - reduce_amt), 2
                                )
                                if demand.fulfilled_quantity_kg < demand.requested_quantity_kg:
                                    demand.status = "PARTIALLY_FULFILLED"

                    # If confirmed_returned_kg was provided, restore that portion to supplier inventory
                    if request.confirmed_returned_kg and request.confirmed_returned_kg > 0:
                        confirmed_returned = Decimal(str(request.confirmed_returned_kg))
                        returned_to_restore = min(confirmed_returned, undelivered)
                        for item in tx.proposal.items:
                            if returned_to_restore <= Decimal("0.00"):
                                break
                            if item.surplus_listing_id:
                                listing = (
                                    db.query(SurplusListing)
                                    .filter(SurplusListing.id == item.surplus_listing_id)
                                    .with_for_update()
                                    .first()
                                )
                                if listing:
                                    listing_deadline = listing.estimated_deadline
                                    if listing_deadline.tzinfo is None:
                                        listing_deadline = listing_deadline.replace(tzinfo=timezone.utc)
                                    restore_amt = min(returned_to_restore, item.allocated_quantity_kg)
                                    returned_to_restore -= restore_amt
                                    if listing_deadline <= now:
                                        listing.status = "EXPIRED"
                                    else:
                                        listing.remaining_quantity_kg = round(
                                            listing.remaining_quantity_kg + restore_amt, 2
                                        )
                                        if listing.status == "DEPLETED":
                                            listing.status = "ACTIVE"

        history = TransactionStatusHistory(
            transaction_id=tx.id,
            previous_status=old_status,
            new_status=target_status,
            changed_by_user_id=current_user.id,
            reason=request.reason or f"Status updated to {target_status}.",
        )
        db.add(history)

        audit = AuditLog(
            user_id=current_user.id,
            action="TRANSACTION_STATUS_UPDATED",
            entity_name="redistribution_transactions",
            entity_id=str(tx.id),
            details={
                "previous_status": old_status,
                "new_status": target_status,
                "reason": request.reason,
            },
        )
        db.add(audit)

        db.commit()
        db.refresh(tx)
        return cls._build_transaction_response(tx)

    # -------------------------------------------------------------------------
    # 5. LIST & RETRIEVE TRANSACTIONS
    # -------------------------------------------------------------------------
    @classmethod
    def list_transactions(
        cls,
        db: Session,
        current_user: User,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> TransactionListResponse:
        cls._verify_coordinator_role(current_user)

        query = db.query(RedistributionTransaction).options(
            joinedload(RedistributionTransaction.proposal)
            .joinedload(AllocationProposal.items)
            .joinedload(AllocationItem.surplus_listing)
            .joinedload(SurplusListing.supplier),
            joinedload(RedistributionTransaction.proposal)
            .joinedload(AllocationProposal.items)
            .joinedload(AllocationItem.demand_request)
            .joinedload(DemandRequest.receiver),
            joinedload(RedistributionTransaction.status_history),
        )

        if status_filter:
            query = query.filter(RedistributionTransaction.status == status_filter.upper())

        total_count = query.count()
        txs = query.order_by(RedistributionTransaction.created_at.desc()).offset(offset).limit(limit).all()

        return TransactionListResponse(
            total_count=total_count,
            items=[cls._build_transaction_response(t) for t in txs],
        )

    @classmethod
    def get_transaction_by_id(
        cls,
        db: Session,
        transaction_id: uuid.UUID,
        current_user: User,
    ) -> TransactionResponse:
        cls._verify_coordinator_role(current_user)

        tx = (
            db.query(RedistributionTransaction)
            .options(
                joinedload(RedistributionTransaction.proposal)
                .joinedload(AllocationProposal.items)
                .joinedload(AllocationItem.surplus_listing)
                .joinedload(SurplusListing.supplier),
                joinedload(RedistributionTransaction.proposal)
                .joinedload(AllocationProposal.items)
                .joinedload(AllocationItem.demand_request)
                .joinedload(DemandRequest.receiver),
                joinedload(RedistributionTransaction.status_history),
            )
            .filter(RedistributionTransaction.id == transaction_id)
            .first()
        )

        if not tx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Redistribution transaction {transaction_id} not found.",
            )

        return cls._build_transaction_response(tx)
