from typing import Set, Dict
from fastapi import HTTPException, status


class ProposalStatus:
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    ACCEPTED = "ACCEPTED"  # Backward-compatible alias for APPROVED
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"


class TransactionStatus:
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    PICKUP_SCHEDULED = "PICKUP_SCHEDULED"
    DISPATCHED = "DISPATCHED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# Allowed state transitions for AllocationProposal
PROPOSAL_TRANSITIONS: Dict[str, Set[str]] = {
    ProposalStatus.PENDING_REVIEW: {
        ProposalStatus.APPROVED,
        ProposalStatus.ACCEPTED,
        ProposalStatus.REJECTED,
        ProposalStatus.SUPERSEDED,
    },
    ProposalStatus.APPROVED: {
        ProposalStatus.EXECUTING,
        ProposalStatus.COMPLETED,
        ProposalStatus.CANCELLED,
    },
    ProposalStatus.ACCEPTED: {
        ProposalStatus.EXECUTING,
        ProposalStatus.COMPLETED,
        ProposalStatus.CANCELLED,
    },
    ProposalStatus.EXECUTING: {
        ProposalStatus.COMPLETED,
        ProposalStatus.FAILED,
        ProposalStatus.CANCELLED,
    },
    # Terminal states
    ProposalStatus.COMPLETED: set(),
    ProposalStatus.REJECTED: set(),
    ProposalStatus.CANCELLED: set(),
    ProposalStatus.FAILED: set(),
    ProposalStatus.SUPERSEDED: set(),
}


# Allowed state transitions for RedistributionTransaction
TRANSACTION_TRANSITIONS: Dict[str, Set[str]] = {
    TransactionStatus.APPROVED: {
        TransactionStatus.PICKUP_SCHEDULED,
        TransactionStatus.SCHEDULED,
        TransactionStatus.DISPATCHED,
        TransactionStatus.PICKED_UP,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.SCHEDULED: {
        TransactionStatus.PICKUP_SCHEDULED,
        TransactionStatus.DISPATCHED,
        TransactionStatus.PICKED_UP,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.PICKUP_SCHEDULED: {
        TransactionStatus.DISPATCHED,
        TransactionStatus.PICKED_UP,
        TransactionStatus.IN_TRANSIT,
        TransactionStatus.CANCELLED,
        TransactionStatus.FAILED,
    },
    TransactionStatus.DISPATCHED: {
        TransactionStatus.PICKED_UP,
        TransactionStatus.IN_TRANSIT,
        TransactionStatus.CANCELLED,
        TransactionStatus.FAILED,
    },
    TransactionStatus.PICKED_UP: {
        TransactionStatus.IN_TRANSIT,
        TransactionStatus.DELIVERED,
        TransactionStatus.CANCELLED,
        TransactionStatus.FAILED,
    },
    TransactionStatus.IN_TRANSIT: {
        TransactionStatus.DELIVERED,
        TransactionStatus.COMPLETED,
        TransactionStatus.FAILED,
    },
    TransactionStatus.DELIVERED: {
        TransactionStatus.COMPLETED,
        TransactionStatus.FAILED,
    },
    # Terminal states
    TransactionStatus.COMPLETED: set(),
    TransactionStatus.FAILED: set(),
    TransactionStatus.CANCELLED: set(),
}


def validate_proposal_transition(current_status: str, target_status: str) -> None:
    """
    Validates whether an AllocationProposal can transition from current_status to target_status.
    Raises HTTPException(400) if the transition is invalid.
    """
    if current_status == target_status:
        return  # Idempotent same-state check

    allowed = PROPOSAL_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid proposal status transition: cannot move from '{current_status}' "
                f"to '{target_status}'. Allowed transitions: {sorted(list(allowed))}."
            ),
        )


def validate_transaction_transition(current_status: str, target_status: str) -> None:
    """
    Validates whether a RedistributionTransaction can transition from current_status to target_status.
    Raises HTTPException(400) if the transition is invalid.
    """
    if current_status == target_status:
        return  # Idempotent same-state check

    allowed = TRANSACTION_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid transaction status transition: cannot move from '{current_status}' "
                f"to '{target_status}'. Allowed transitions: {sorted(list(allowed))}."
            ),
        )
