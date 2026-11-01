import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator


def validate_phone_number(v: str) -> str:
    cleaned = v.strip()
    digits = re.sub(r"\D", "", cleaned)
    if not (7 <= len(digits) <= 15) or not re.match(r"^\+?[0-9\s\-\(\)\.]{7,25}$", cleaned):
        raise ValueError("Invalid phone number format. Must contain 7 to 15 digits.")
    return cleaned


def validate_latitude(v: Decimal) -> Decimal:
    if not (Decimal("-90.0") <= v <= Decimal("90.0")):
        raise ValueError("Latitude must be between -90.0 and 90.0 degrees (WGS84).")
    return v


def validate_longitude(v: Decimal) -> Decimal:
    if not (Decimal("-180.0") <= v <= Decimal("180.0")):
        raise ValueError("Longitude must be between -180.0 and 180.0 degrees (WGS84).")
    return v


# =========================================================================
# SUPPLIER PROFILE SCHEMAS
# =========================================================================

VALID_FACILITY_TYPES = {
    "FARM",
    "WHOLESALER",
    "RETAILER",
    "RESTAURANT",
    "FOOD_PROCESSOR",
    "OTHER",
}


class SupplierProfileCreate(BaseModel):
    organization_name: str = Field(..., min_length=2, max_length=255)
    contact_phone: str = Field(..., description="Phone number with country or area code")
    address: str = Field(..., min_length=5, description="Physical pickup address")
    state: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    latitude: Decimal = Field(..., description="WGS84 latitude (-90 to +90)")
    longitude: Decimal = Field(..., description="WGS84 longitude (-180 to +180)")
    facility_type: str = Field(..., description="FARM | WHOLESALER | RETAILER | RESTAURANT | FOOD_PROCESSOR | OTHER")
    operating_hours: Optional[Dict[str, Any]] = Field(default_factory=dict)
    storage_capabilities: Optional[Dict[str, bool]] = Field(
        default_factory=lambda: {"ambient": True, "refrigerated": False, "frozen": False}
    )
    description: Optional[str] = Field(None, max_length=1000)

    @field_validator("contact_phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        return validate_phone_number(v)

    @field_validator("latitude")
    @classmethod
    def check_lat(cls, v: Decimal) -> Decimal:
        return validate_latitude(v)

    @field_validator("longitude")
    @classmethod
    def check_lon(cls, v: Decimal) -> Decimal:
        return validate_longitude(v)

    @field_validator("facility_type")
    @classmethod
    def check_facility(cls, v: str) -> str:
        norm = v.strip().upper()
        if norm not in VALID_FACILITY_TYPES:
            raise ValueError(f"Facility type must be one of: {', '.join(sorted(VALID_FACILITY_TYPES))}")
        return norm


class SupplierProfileUpdate(BaseModel):
    organization_name: Optional[str] = Field(None, min_length=2, max_length=255)
    contact_phone: Optional[str] = None
    address: Optional[str] = Field(None, min_length=5)
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    facility_type: Optional[str] = None
    operating_hours: Optional[Dict[str, Any]] = None
    storage_capabilities: Optional[Dict[str, bool]] = None
    description: Optional[str] = None

    @field_validator("contact_phone")
    @classmethod
    def check_phone(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone_number(v) if v is not None else None

    @field_validator("latitude")
    @classmethod
    def check_lat(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        return validate_latitude(v) if v is not None else None

    @field_validator("longitude")
    @classmethod
    def check_lon(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        return validate_longitude(v) if v is not None else None

    @field_validator("facility_type")
    @classmethod
    def check_facility(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            norm = v.strip().upper()
            if norm not in VALID_FACILITY_TYPES:
                raise ValueError(f"Facility type must be one of: {', '.join(sorted(VALID_FACILITY_TYPES))}")
            return norm
        return None


class SupplierProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    organization_name: str
    contact_phone: str
    address: str
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    latitude: Decimal
    longitude: Decimal
    facility_type: str
    operating_hours: Optional[Dict[str, Any]] = None
    storage_capabilities: Optional[Dict[str, bool]] = None
    description: Optional[str] = None
    verification_status: str = "PENDING_VERIFICATION"
    is_verified: bool = False
    license_number: Optional[str] = None
    representative_name: Optional[str] = None
    verification_submitted_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# =========================================================================
# RECEIVER PROFILE SCHEMAS
# =========================================================================

VALID_RECEIVER_CATEGORIES = {
    "FOOD_BANK",
    "NGO",
    "COMMUNITY_KITCHEN",
    "SHELTER",
    "HOSPITAL",
    "OTHER",
}


class ReceiverProfileCreate(BaseModel):
    organization_name: str = Field(..., min_length=2, max_length=255)
    contact_phone: str = Field(..., description="Phone number with country or area code")
    address: str = Field(..., min_length=5, description="Physical delivery destination")
    state: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    latitude: Decimal = Field(..., description="WGS84 latitude (-90 to +90)")
    longitude: Decimal = Field(..., description="WGS84 longitude (-180 to +180)")
    receiver_category: str = Field(..., description="FOOD_BANK | NGO | COMMUNITY_KITCHEN | SHELTER | HOSPITAL | OTHER")
    capacity_daily_kg: Decimal = Field(..., gt=0, description="Daily intake storage capacity in kg (must be > 0)")
    cold_storage_capabilities: Optional[Dict[str, bool]] = Field(
        default_factory=lambda: {"refrigeration": False, "freezer": False}
    )
    dietary_handling_capabilities: Optional[List[str]] = Field(default_factory=list)
    operating_hours: Optional[Dict[str, Any]] = Field(default_factory=dict)
    priority_level: int = Field(3, ge=1, le=5, description="Priority urgency level (1 to 5)")
    description: Optional[str] = Field(None, max_length=1000)

    @field_validator("contact_phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        return validate_phone_number(v)

    @field_validator("latitude")
    @classmethod
    def check_lat(cls, v: Decimal) -> Decimal:
        return validate_latitude(v)

    @field_validator("longitude")
    @classmethod
    def check_lon(cls, v: Decimal) -> Decimal:
        return validate_longitude(v)

    @field_validator("receiver_category")
    @classmethod
    def check_category(cls, v: str) -> str:
        norm = v.strip().upper()
        if norm not in VALID_RECEIVER_CATEGORIES:
            raise ValueError(f"Receiver category must be one of: {', '.join(sorted(VALID_RECEIVER_CATEGORIES))}")
        return norm


class ReceiverProfileUpdate(BaseModel):
    organization_name: Optional[str] = Field(None, min_length=2, max_length=255)
    contact_phone: Optional[str] = None
    address: Optional[str] = Field(None, min_length=5)
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    receiver_category: Optional[str] = None
    capacity_daily_kg: Optional[Decimal] = Field(None, gt=0)
    cold_storage_capabilities: Optional[Dict[str, bool]] = None
    dietary_handling_capabilities: Optional[List[str]] = None
    operating_hours: Optional[Dict[str, Any]] = None
    priority_level: Optional[int] = Field(None, ge=1, le=5)
    description: Optional[str] = None

    @field_validator("contact_phone")
    @classmethod
    def check_phone(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone_number(v) if v is not None else None

    @field_validator("latitude")
    @classmethod
    def check_lat(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        return validate_latitude(v) if v is not None else None

    @field_validator("longitude")
    @classmethod
    def check_lon(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        return validate_longitude(v) if v is not None else None

    @field_validator("receiver_category")
    @classmethod
    def check_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            norm = v.strip().upper()
            if norm not in VALID_RECEIVER_CATEGORIES:
                raise ValueError(f"Receiver category must be one of: {', '.join(sorted(VALID_RECEIVER_CATEGORIES))}")
            return norm
        return None


class ReceiverProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    organization_name: str
    contact_phone: str
    address: str
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    latitude: Decimal
    longitude: Decimal
    receiver_category: Optional[str] = None
    capacity_daily_kg: Decimal
    cold_storage_capabilities: Optional[Dict[str, bool]] = None
    dietary_handling_capabilities: Optional[List[str]] = None
    operating_hours: Optional[Dict[str, Any]] = None
    priority_level: int
    description: Optional[str] = None
    verification_status: str = "PENDING_VERIFICATION"
    is_verified: bool = False
    license_number: Optional[str] = None
    representative_name: Optional[str] = None
    verification_submitted_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
