import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class VerificationSubmission(BaseModel):
    representative_name: str = Field(..., min_length=2, max_length=255)
    license_number: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, min_length=5)


class VerificationRejectionRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000, description="Mandatory reason for verification rejection")


class OrganizationVerificationItem(BaseModel):
    org_id: uuid.UUID
    user_id: uuid.UUID
    org_name: str
    org_type: str  # "SUPPLIER" | "RECEIVER"
    email: str
    registered_at: datetime
    verification_status: str
    license_number: Optional[str] = None
    representative_name: Optional[str] = None
    address: str
    city: Optional[str] = None
    has_document: bool = False
    document_name: Optional[str] = None
    submitted_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    model_config = {"from_attributes": True}


class OrganizationVerificationStatusResponse(BaseModel):
    org_id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    org_name: Optional[str] = None
    org_type: str
    verification_status: str
    is_verified: bool
    license_number: Optional[str] = None
    representative_name: Optional[str] = None
    has_document: bool = False
    document_name: Optional[str] = None
    submitted_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
