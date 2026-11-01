import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import require_role
from app.models.user import User
from app.optimization.models import (
    OptimizationRunRequest,
    OptimizationProposalResponse,
)
from app.optimization.allocation_service import AllocationService
from app.redistribution.models import (
    ApproveProposalRequest,
    RejectProposalRequest,
    TransactionResponse,
    ProposalActionResponse,
)
from app.redistribution.transaction_service import TransactionService

router = APIRouter(prefix="/optimization", tags=["Allocation Optimization"])


@router.post(
    "/allocation-proposals",
    response_model=OptimizationProposalResponse,
    status_code=status.HTTP_200_OK,
    summary="Run Google OR-Tools Constrained Allocation Optimization",
    description="""
    Solves a multi-commodity capacitated transportation network optimization problem
    using Google OR-Tools CP-SAT. Ingests eligible surplus listings and open receiver demands,
    enforces hard conservation constraints, optimizes urgency and priority, penalizes transit waste,
    generates auditable diagnostic explanations, and persists proposal for human review.

    STRICT GUARANTEE: Never modifies surplus inventory or demand quantities.
    Restricted to COORDINATOR and ADMIN roles.
    """,
)
def create_allocation_proposal(
    request: OptimizationRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("COORDINATOR", "ADMIN")),
) -> OptimizationProposalResponse:
    return AllocationService.generate_proposal(
        db=db,
        request=request,
        current_user=current_user,
    )


@router.get(
    "/proposals/{proposal_id}",
    response_model=OptimizationProposalResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve an Allocation Proposal by ID",
    description="Fetches a previously persisted allocation proposal and its line items.",
)
def get_allocation_proposal(
    proposal_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("COORDINATOR", "ADMIN")),
) -> OptimizationProposalResponse:
    return AllocationService.get_proposal_by_id(
        db=db,
        proposal_id=proposal_id,
        current_user=current_user,
    )


@router.post(
    "/proposals/{proposal_id}/approve",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve Allocation Proposal and Crystallize Redistribution Transaction",
    description="""
    Human coordinator approval endpoint. Revalidates listing availability, remaining inventory,
    outstanding demand requirements, and expiration timestamps.
    Atomically decrements surplus inventory, updates demand fulfillment, and creates a
    binding RedistributionTransaction with status history and audit logging.
    """,
)
def approve_proposal(
    proposal_id: uuid.UUID,
    request: ApproveProposalRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("COORDINATOR", "ADMIN")),
) -> TransactionResponse:
    req = request or ApproveProposalRequest()
    return TransactionService.approve_proposal(
        db=db,
        proposal_id=proposal_id,
        current_user=current_user,
        request=req,
    )


@router.post(
    "/proposals/{proposal_id}/reject",
    response_model=ProposalActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject Allocation Proposal with Mandatory Justification",
    description="Coordinator rejection endpoint. Requires a mandatory operational rationale.",
)
def reject_proposal(
    proposal_id: uuid.UUID,
    request: RejectProposalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("COORDINATOR", "ADMIN")),
) -> ProposalActionResponse:
    return TransactionService.reject_proposal(
        db=db,
        proposal_id=proposal_id,
        current_user=current_user,
        request=request,
    )
