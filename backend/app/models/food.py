import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, TYPE_CHECKING

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
    JSON,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.models.user import SupplierProfile, ReceiverProfile
    from app.models.redistribution import AllocationItem


class SurplusListing(Base):
    __tablename__ = "surplus_listings"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("supplier_profiles.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    food_category: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False
    )
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    initial_quantity_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    remaining_quantity_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    storage_condition: Mapped[str] = mapped_column(String(32), nullable=False)
    food_condition: Mapped[str] = mapped_column(String(32), nullable=False)
    harvest_or_prep_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    preparation_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    estimated_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    pickup_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    handling_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    urgency_classification: Mapped[str] = mapped_column(
        String(16), default="PENDING", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default="ACTIVE", index=True, nullable=False
    )
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
            "initial_quantity_kg > 0", name="ck_surplus_initial_qty_positive"
        ),
        CheckConstraint(
            "remaining_quantity_kg >= 0 AND remaining_quantity_kg <= initial_quantity_kg",
            name="ck_surplus_remaining_qty_bounds",
        ),
        CheckConstraint(
            "storage_condition IN ('AMBIENT', 'REFRIGERATED', 'FROZEN')",
            name="ck_surplus_storage_condition",
        ),
        CheckConstraint(
            "food_condition IN ('EXCELLENT', 'GOOD', 'FAIR', 'RIPE', 'IMMINENT_DECAY', 'IMPERFECT')",
            name="ck_surplus_food_condition",
        ),
        CheckConstraint(
            "urgency_classification IN ('CRITICAL', 'HIGH', 'MODERATE', 'LOW', 'PENDING')",
            name="ck_surplus_urgency",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'PAUSED', 'DEPLETED', 'EXPIRED', 'CANCELLED', 'AVAILABLE', 'ALLOCATING', 'EXHAUSTED')",
            name="ck_surplus_status",
        ),
        CheckConstraint(
            "estimated_deadline > harvest_or_prep_date",
            name="ck_surplus_deadline_after_prep",
        ),
        Index("idx_surplus_deadline_status", "status", "estimated_deadline"),
        Index("idx_surplus_supplier", "supplier_id"),
        Index("idx_surplus_category", "food_category"),
    )

    supplier: Mapped["SupplierProfile"] = relationship(
        "SupplierProfile", back_populates="surplus_listings"
    )
    allocation_items: Mapped[List["AllocationItem"]] = relationship(
        "AllocationItem", back_populates="surplus_listing"
    )


class DemandRequest(Base):
    __tablename__ = "demand_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    receiver_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("receiver_profiles.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    food_category: Mapped[str] = mapped_column(String(64), nullable=False)
    item_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requested_quantity_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    fulfilled_quantity_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    acceptable_food_condition: Mapped[Optional[str]] = mapped_column(
        String(32), default="FAIR", nullable=True
    )
    dietary_requirements: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list
    )
    storage_capability: Mapped[str] = mapped_column(String(32), nullable=False)
    delivery_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    handling_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    required_by: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    priority_weight: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default="OPEN", index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    @property
    def remaining_requirement_kg(self) -> Decimal:
        return (self.requested_quantity_kg or Decimal("0.00")) - (
            self.fulfilled_quantity_kg or Decimal("0.00")
        )

    __table_args__ = (
        CheckConstraint(
            "requested_quantity_kg > 0", name="ck_demand_requested_qty_positive"
        ),
        CheckConstraint(
            "fulfilled_quantity_kg >= 0 AND fulfilled_quantity_kg <= requested_quantity_kg",
            name="ck_demand_fulfilled_qty_bounds",
        ),
        CheckConstraint(
            "storage_capability IN ('AMBIENT', 'REFRIGERATED', 'FROZEN')",
            name="ck_demand_storage_capability",
        ),
        CheckConstraint(
            "priority_weight BETWEEN 1 AND 5", name="ck_demand_priority_weight"
        ),
        CheckConstraint(
            "status IN ('OPEN', 'PAUSED', 'PARTIALLY_FULFILLED', 'FULFILLED', 'EXPIRED', 'CANCELLED', 'ACTIVE')",
            name="ck_demand_status",
        ),
        Index("idx_demand_status_reqby", "status", "required_by"),
        Index("idx_demand_receiver", "receiver_id"),
    )

    receiver: Mapped["ReceiverProfile"] = relationship(
        "ReceiverProfile", back_populates="demand_requests"
    )
    allocation_items: Mapped[List["AllocationItem"]] = relationship(
        "AllocationItem", back_populates="demand_request"
    )
