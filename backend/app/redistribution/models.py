import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ApproveProposalRequest(BaseModel):
    """
    Coordinator confirmation payload to approve an allocation proposal
    and crystallize it into an atomic redistribution transaction.
    """
    dispatch_notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Operational instructions (loading dock, contact, handling).",
    )
    scheduled_pickup_at: Optional[datetime] = Field(
        default=None,
        description="Optional agreed scheduled pickup timestamp.",
    )


class RejectProposalRequest(BaseModel):
    """
    Coordinator rejection payload. Requires a mandatory operational rationale.
    """
    reason: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Mandatory justification for rejecting this proposal.",
    )


class UpdateTransactionStatusRequest(BaseModel):
    """
    Payload for advancing transaction dispatch checkpoints.
    Supports confirmed returned quantities on cancellation and partial delivery accounting.
    """
    status: str = Field(
        ...,
        description="Target status: PICKUP_SCHEDULED, PICKED_UP, IN_TRANSIT, DELIVERED, COMPLETED, FAILED, CANCELLED.",
    )
    reason: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Operational context, delay explanation, or failure cause.",
    )
    actual_pickup_at: Optional[datetime] = Field(
        default=None,
        description="Driver recorded pickup timestamp.",
    )
    actual_delivery_at: Optional[datetime] = Field(
        default=None,
        description="Driver recorded arrival/delivery timestamp.",
    )
    dispatch_notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Updated dispatch or gate instructions.",
    )
    confirmed_returned_kg: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Physically confirmed returned quantity to restore to supplier inventory (used on cancellation/failure after pickup).",
    )
    actual_delivered_kg: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Physically verified delivered quantity accepted by receiver upon DELIVERED/COMPLETED (for partial delivery).",
    )


class TransactionStatusHistoryResponse(BaseModel):
    id: uuid.UUID
    previous_status: Optional[str] = None
    new_status: str
    changed_by_user_id: uuid.UUID
    reason: Optional[str] = None
    changed_at: datetime


class TransactionItemResponse(BaseModel):
    item_id: uuid.UUID
    surplus_listing_id: uuid.UUID
    demand_request_id: uuid.UUID
    supplier_id: uuid.UUID
    receiver_id: uuid.UUID
    supplier_name: str
    receiver_name: str
    item_name: str
    food_category: str
    allocated_quantity_kg: float
    estimated_distance_km: float
    estimated_transit_minutes: int
    urgency_at_allocation: str


class TransactionResponse(BaseModel):
    id: uuid.UUID
    proposal_id: uuid.UUID
    tracking_code: str
    status: str
    scheduled_pickup_at: Optional[datetime] = None
    actual_pickup_at: Optional[datetime] = None
    actual_delivery_at: Optional[datetime] = None
    dispatch_notes: Optional[str] = None
    total_allocated_kg: float
    items_count: int
    items: List[TransactionItemResponse] = Field(default_factory=list)
    status_history: List[TransactionStatusHistoryResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TransactionListResponse(BaseModel):
    total_count: int
    items: List[TransactionResponse]


class ProposalActionResponse(BaseModel):
    proposal_id: uuid.UUID
    status: str
    message: str
    rejection_reason: Optional[str] = None
    transaction: Optional[TransactionResponse] = None
