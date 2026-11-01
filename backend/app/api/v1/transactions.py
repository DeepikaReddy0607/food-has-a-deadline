import uuid
from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import require_role
from app.models.user import User
from app.redistribution.models import (
    TransactionResponse,
    TransactionListResponse,
    UpdateTransactionStatusRequest,
)
from app.redistribution.transaction_service import TransactionService

router = APIRouter(prefix="/transactions", tags=["Redistribution Transactions"])


@router.get(
    "",
    response_model=TransactionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Redistribution Transactions",
    description="Retrieves committed redistribution transactions with optional status filtering and pagination.",
)
def list_transactions(
    status: Optional[str] = Query(default=None, description="Optional status filter"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("COORDINATOR", "ADMIN")),
) -> TransactionListResponse:
    return TransactionService.list_transactions(
        db=db,
        current_user=current_user,
        status_filter=status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Redistribution Transaction by ID",
    description="Fetches full transaction details including line items and status progression history.",
)
def get_transaction(
    transaction_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("COORDINATOR", "ADMIN")),
) -> TransactionResponse:
    return TransactionService.get_transaction_by_id(
        db=db,
        transaction_id=transaction_id,
        current_user=current_user,
    )


@router.post(
    "/{transaction_id}/execute",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Redistribution Transaction",
    description="Advances an approved transaction into execution dispatch (status: PICKUP_SCHEDULED).",
)
def execute_transaction(
    transaction_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("COORDINATOR", "ADMIN")),
) -> TransactionResponse:
    return TransactionService.execute_transaction(
        db=db,
        transaction_id=transaction_id,
        current_user=current_user,
    )


@router.patch(
    "/{transaction_id}/status",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Transaction Status Checkpoint",
    description="""
    Advances a redistribution transaction along its authorized lifecycle:
    PICKUP_SCHEDULED, PICKED_UP, IN_TRANSIT, DELIVERED, COMPLETED, FAILED, CANCELLED.
    Records timestamp, coordinator identity, and operational reason in transaction history.
    """,
)
def update_transaction_status(
    transaction_id: uuid.UUID,
    request: UpdateTransactionStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("COORDINATOR", "ADMIN")),
) -> TransactionResponse:
    return TransactionService.update_transaction_status(
        db=db,
        transaction_id=transaction_id,
        current_user=current_user,
        request=request,
    )
