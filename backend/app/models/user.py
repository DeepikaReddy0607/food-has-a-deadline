import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import (
    String,
    Boolean,
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
    from app.models.food import SurplusListing, DemandRequest
    from app.models.audit import AuditLog, SimulationRun


class UserRole(str, Enum):
    SUPPLIER = "SUPPLIER"
    RECEIVER = "RECEIVER"
    COORDINATOR = "COORDINATOR"
    ADMIN = "ADMIN"


class FacilityType(str, Enum):
    FARM = "FARM"
    WHOLESALER = "WHOLESALER"
    RETAILER = "RETAILER"
    RESTAURANT = "RESTAURANT"
    FOOD_PROCESSOR = "FOOD_PROCESSOR"
    OTHER = "OTHER"


class ReceiverCategory(str, Enum):
    FOOD_BANK = "FOOD_BANK"
    NGO = "NGO"
    COMMUNITY_KITCHEN = "COMMUNITY_KITCHEN"
    SHELTER = "SHELTER"
    HOSPITAL = "HOSPITAL"
    OTHER = "OTHER"


class VerificationStatus(str, Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    DOCUMENTS_SUBMITTED = "DOCUMENTS_SUBMITTED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(32), default="PENDING_VERIFICATION", nullable=False
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
            "role IN ('SUPPLIER', 'RECEIVER', 'COORDINATOR', 'ADMIN')",
            name="ck_users_role",
        ),
        CheckConstraint(
            "verification_status IN ('PENDING_VERIFICATION', 'DOCUMENTS_SUBMITTED', 'VERIFIED', 'REJECTED')",
            name="ck_users_verification_status",
        ),
    )

    # 1-to-1 Profile Relationships
    supplier_profile: Mapped[Optional["SupplierProfile"]] = relationship(
        "SupplierProfile",
        back_populates="user",
        foreign_keys="[SupplierProfile.user_id]",
        cascade="all, delete-orphan",
        uselist=False,
    )
    receiver_profile: Mapped[Optional["ReceiverProfile"]] = relationship(
        "ReceiverProfile",
        back_populates="user",
        foreign_keys="[ReceiverProfile.user_id]",
        cascade="all, delete-orphan",
        uselist=False,
    )

    # 1-to-Many System Relationships
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="user"
    )
    simulation_runs: Mapped[List["SimulationRun"]] = relationship(
        "SimulationRun", back_populates="user"
    )


class SupplierProfile(Base):
    __tablename__ = "supplier_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    organization_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    facility_type: Mapped[str] = mapped_column(String(64), nullable=False)
    operating_hours: Mapped[Optional[dict]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True, default=dict
    )
    storage_capabilities: Mapped[Optional[dict]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True, default=dict
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(32), default="PENDING_VERIFICATION", nullable=False
    )
    license_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    representative_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verification_document_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    verification_document_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verification_submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    @property
    def is_verified(self) -> bool:
        return self.verification_status == "VERIFIED"

    @is_verified.setter
    def is_verified(self, val: bool) -> None:
        if val:
            self.verification_status = "VERIFIED"

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
            "latitude BETWEEN -90 AND 90", name="ck_supplier_latitude"
        ),
        CheckConstraint(
            "longitude BETWEEN -180 AND 180", name="ck_supplier_longitude"
        ),
        CheckConstraint(
            "verification_status IN ('PENDING_VERIFICATION', 'DOCUMENTS_SUBMITTED', 'VERIFIED', 'REJECTED')",
            name="ck_supplier_verification_status",
        ),
        Index("idx_supplier_coords", "latitude", "longitude"),
    )

    user: Mapped["User"] = relationship("User", back_populates="supplier_profile", foreign_keys=[user_id])
    surplus_listings: Mapped[List["SurplusListing"]] = relationship(
        "SurplusListing", back_populates="supplier"
    )


class ReceiverProfile(Base):
    __tablename__ = "receiver_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    organization_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    receiver_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    capacity_daily_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    cold_storage_capabilities: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=lambda: {"refrigeration": False, "freezer": False},
    )
    dietary_handling_capabilities: Mapped[Optional[list]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True, default=list
    )
    operating_hours: Mapped[Optional[dict]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True, default=dict
    )
    priority_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(32), default="PENDING_VERIFICATION", nullable=False
    )
    license_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    representative_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verification_document_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    verification_document_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verification_submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    @property
    def is_verified(self) -> bool:
        return self.verification_status == "VERIFIED"

    @is_verified.setter
    def is_verified(self, val: bool) -> None:
        if val:
            self.verification_status = "VERIFIED"

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
            "latitude BETWEEN -90 AND 90", name="ck_receiver_latitude"
        ),
        CheckConstraint(
            "longitude BETWEEN -180 AND 180", name="ck_receiver_longitude"
        ),
        CheckConstraint(
            "capacity_daily_kg > 0", name="ck_receiver_capacity_positive"
        ),
        CheckConstraint(
            "priority_level BETWEEN 1 AND 5", name="ck_receiver_priority_level"
        ),
        CheckConstraint(
            "verification_status IN ('PENDING_VERIFICATION', 'DOCUMENTS_SUBMITTED', 'VERIFIED', 'REJECTED')",
            name="ck_receiver_verification_status",
        ),
        Index("idx_receiver_coords", "latitude", "longitude"),
        Index("idx_receiver_priority", "priority_level"),
    )

    user: Mapped["User"] = relationship("User", back_populates="receiver_profile", foreign_keys=[user_id])
    demand_requests: Mapped[List["DemandRequest"]] = relationship(
        "DemandRequest", back_populates="receiver"
    )
