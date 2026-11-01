import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator


VALID_DIETARY_REQUIREMENTS = {
    "VEGETARIAN",
    "VEGAN",
    "GLUTEN_FREE",
    "DAIRY_FREE",
    "NUT_FREE",
    "HALAL",
    "KOSHER",
    "OTHER",
}

VALID_STORAGE_CAPABILITIES = {
    "AMBIENT",
    "REFRIGERATED",
    "FROZEN",
}


class DemandRequestCreate(BaseModel):
    food_category: str = Field(..., description="Food category required or ANY")
    item_name: Optional[str] = Field(None, max_length=255, description="Specific item requested or meal type")
    description: Optional[str] = Field(None, max_length=1500)
    requested_quantity_kg: Decimal = Field(..., gt=0, description="Total food quantity requested in kilograms (must be > 0)")
    required_by: datetime = Field(..., description="Target service deadline / meal preparation cut-off time")
    acceptable_food_condition: Optional[str] = Field("FAIR", description="EXCELLENT | GOOD | FAIR | ANY")
    dietary_requirements: Optional[List[str]] = Field(default_factory=list, description="List of dietary requirements")
    storage_capability: str = Field("AMBIENT", description="Storage capability available at recipient facility (AMBIENT | REFRIGERATED | FROZEN)")
    delivery_address: Optional[str] = Field(None, description="Specific delivery address (defaults to receiver profile address if empty)")
    handling_instructions: Optional[str] = Field(None, max_length=1000)
    priority_weight: int = Field(3, ge=1, le=5, description="Urgency priority level from 1 (lowest) to 5 (highest)")

    @field_validator("storage_capability")
    @classmethod
    def check_storage(cls, v: str) -> str:
        norm = v.strip().upper()
        if norm not in VALID_STORAGE_CAPABILITIES:
            raise ValueError(f"Storage capability must be one of: {', '.join(sorted(VALID_STORAGE_CAPABILITIES))}")
        return norm

    @field_validator("dietary_requirements")
    @classmethod
    def check_dietary(cls, v: Optional[List[str]]) -> List[str]:
        if not v:
            return []
        cleaned = []
        for item in v:
            norm = item.strip().upper()
            cleaned.append(norm)
        return cleaned

    @model_validator(mode="after")
    def check_deadline(self) -> "DemandRequestCreate":
        now = datetime.now(timezone.utc)
        target = self.required_by
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)

        if target <= now:
            raise ValueError("Required-by deadline cannot be in the past.")

        return self


class DemandRequestUpdate(BaseModel):
    item_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    requested_quantity_kg: Optional[Decimal] = Field(None, gt=0)
    required_by: Optional[datetime] = None
    acceptable_food_condition: Optional[str] = None
    dietary_requirements: Optional[List[str]] = None
    storage_capability: Optional[str] = None
    delivery_address: Optional[str] = None
    handling_instructions: Optional[str] = None
    priority_weight: Optional[int] = Field(None, ge=1, le=5)

    @field_validator("storage_capability")
    @classmethod
    def check_storage(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            norm = v.strip().upper()
            if norm not in VALID_STORAGE_CAPABILITIES:
                raise ValueError(f"Storage capability must be one of: {', '.join(sorted(VALID_STORAGE_CAPABILITIES))}")
            return norm
        return None


class DemandRequestResponse(BaseModel):
    id: uuid.UUID
    receiver_id: uuid.UUID
    food_category: str
    item_name: Optional[str] = None
    description: Optional[str] = None
    requested_quantity_kg: Decimal
    fulfilled_quantity_kg: Decimal
    remaining_requirement_kg: Decimal
    acceptable_food_condition: Optional[str] = None
    dietary_requirements: List[str] = Field(default_factory=list)
    storage_capability: str
    delivery_address: Optional[str] = None
    handling_instructions: Optional[str] = None
    priority_weight: int
    status: str
    required_by: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DemandPaginationResponse(BaseModel):
    items: List[DemandRequestResponse]
    total: int
    page: int
    page_size: int
    pages: int
