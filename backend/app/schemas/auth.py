import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Contact name or organization display name")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(..., min_length=8, max_length=128, description="Strong password (minimum 8 characters)")
    role: str = Field(..., description="Role: SUPPLIER or RECEIVER")

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized in ("ADMIN", "COORDINATOR"):
            raise ValueError(
                "Public registration is restricted to SUPPLIER and RECEIVER roles. "
                "ADMIN and COORDINATOR roles must be assigned administratively."
            )
        if normalized not in ("SUPPLIER", "RECEIVER"):
            raise ValueError("Role must be either 'SUPPLIER' or 'RECEIVER'")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return value


class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")


class UserSummary(BaseModel):
    id: uuid.UUID
    email: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserSummary


class UserPublicResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    profile: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}
