import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import (
    String,
    DateTime,
    Numeric,
    Text,
    Integer,
    ForeignKey,
    CheckConstraint,
    Index,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.food import SurplusListing, DemandRequest


class AllocationProposal(Base):
    __tablename__ = "allocation_proposals"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    generated_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32), default="PENDING_REVIEW", index=True, nullable=False
    )
    total_allocated_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    total_unallocated_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    total_unmet_demand_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    estimated_total_transit_km: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    ai_justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    solver_status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING_REVIEW', 'APPROVED', 'ACCEPTED', 'EXECUTING', 'COMPLETED', 'REJECTED', 'CANCELLED', 'FAILED', 'SUPERSEDED')",
            name="ck_proposals_status",
        ),
        CheckConstraint(
            "total_allocated_kg > 0", name="ck_proposals_total_allocated_positive"
        ),
        CheckConstraint(
            "total_unallocated_kg >= 0",
            name="ck_proposals_total_unallocated_nonneg",
        ),
        CheckConstraint(
            "total_unmet_demand_kg >= 0", name="ck_proposals_total_unmet_nonneg"
        ),
        CheckConstraint(
            "estimated_total_transit_km >= 0",
            name="ck_proposals_transit_km_nonneg",
        ),
    )

    generated_by_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[generated_by_user_id]
    )
    items: Mapped[List["AllocationItem"]] = relationship(
        "AllocationItem", back_populates="proposal", cascade="all, delete-orphan"
    )
    transaction: Mapped[Optional["RedistributionTransaction"]] = relationship(
        "RedistributionTransaction",
        back_populates="proposal",
        uselist=False,
    )


class AllocationItem(Base):
    __tablename__ = "allocation_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("allocation_proposals.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    surplus_listing_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("surplus_listings.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    demand_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("demand_requests.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    allocated_quantity_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    estimated_distance_km: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), nullable=False
    )
    estimated_transit_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    urgency_at_allocation: Mapped[str] = mapped_column(
        String(16), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "allocated_quantity_kg > 0", name="ck_alloc_item_qty_positive"
        ),
        CheckConstraint(
            "estimated_distance_km >= 0", name="ck_alloc_item_dist_nonneg"
        ),
        CheckConstraint(
            "estimated_transit_minutes >= 0",
            name="ck_alloc_item_transit_nonneg",
        ),
    )

    proposal: Mapped["AllocationProposal"] = relationship(
        "AllocationProposal", back_populates="items"
    )
    surplus_listing: Mapped["SurplusListing"] = relationship(
        "SurplusListing", back_populates="allocation_items"
    )
    demand_request: Mapped["DemandRequest"] = relationship(
        "DemandRequest", back_populates="allocation_items"
    )


class RedistributionTransaction(Base):
    __tablename__ = "redistribution_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("allocation_proposals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tracking_code: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default="SCHEDULED", index=True, nullable=False
    )
    scheduled_pickup_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_pickup_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_delivery_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dispatch_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('APPROVED', 'SCHEDULED', 'PICKUP_SCHEDULED', 'DISPATCHED', 'PICKED_UP', 'IN_TRANSIT', 'DELIVERED', 'COMPLETED', 'FAILED', 'CANCELLED')",
            name="ck_tx_status",
        ),
    )

    proposal: Mapped["AllocationProposal"] = relationship(
        "AllocationProposal", back_populates="transaction"
    )
    status_history: Mapped[List["TransactionStatusHistory"]] = relationship(
        "TransactionStatusHistory",
        back_populates="transaction",
        cascade="all, delete-orphan",
    )


class TransactionStatusHistory(Base):
    __tablename__ = "transaction_status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("redistribution_transactions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    previous_status: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    changed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    transaction: Mapped["RedistributionTransaction"] = relationship(
        "RedistributionTransaction", back_populates="status_history"
    )
    changed_by_user: Mapped["User"] = relationship(
        "User", foreign_keys=[changed_by_user_id]
    )
