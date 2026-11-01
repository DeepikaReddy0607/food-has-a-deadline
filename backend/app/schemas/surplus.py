import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator


VALID_FOOD_CATEGORIES = {
    "FRUITS",
    "VEGETABLES",
    "GRAINS",
    "DAIRY",
    "BAKERY",
    "COOKED_FOOD",
    "OTHER",
}

VALID_FOOD_CONDITIONS = {
    "EXCELLENT",
    "GOOD",
    "FAIR",
    "RIPE",
    "IMMINENT_DECAY",
    "IMPERFECT",
}

VALID_STORAGE_CONDITIONS = {
    "AMBIENT",
    "REFRIGERATED",
    "FROZEN",
}


class SurplusListingCreate(BaseModel):
    food_category: str = Field(..., description="FRUITS | VEGETABLES | GRAINS | DAIRY | BAKERY | COOKED_FOOD | OTHER")
    item_name: str = Field(..., min_length=2, max_length=255, description="Specific food batch name or title")
    description: Optional[str] = Field(None, max_length=1500)
    initial_quantity_kg: Decimal = Field(..., gt=0, description="Available food weight in kilograms (must be > 0)")
    harvest_or_prep_date: datetime = Field(..., description="Date & time when food was harvested, prepared or received")
    preparation_date: Optional[datetime] = Field(None, description="Optional preparation or cooking timestamp")
    estimated_deadline: datetime = Field(..., description="Hard timestamp when food will no longer be safe or usable")
    food_condition: str = Field("GOOD", description="EXCELLENT | GOOD | FAIR")
    storage_condition: str = Field("AMBIENT", description="AMBIENT | REFRIGERATED | FROZEN")
    pickup_address: Optional[str] = Field(None, description="Specific pickup address (defaults to supplier facility address if empty)")
    handling_instructions: Optional[str] = Field(None, max_length=1000)

    @field_validator("food_category")
    @classmethod
    def check_category(cls, v: str) -> str:
        norm = v.strip().upper()
        if norm not in VALID_FOOD_CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(sorted(VALID_FOOD_CATEGORIES))}")
        return norm

    @field_validator("food_condition")
    @classmethod
    def check_condition(cls, v: str) -> str:
        norm = v.strip().upper()
        if norm not in VALID_FOOD_CONDITIONS:
            raise ValueError(f"Condition must be one of: {', '.join(sorted(VALID_FOOD_CONDITIONS))}")
        return norm

    @field_validator("storage_condition")
    @classmethod
    def check_storage(cls, v: str) -> str:
        norm = v.strip().upper()
        if norm not in VALID_STORAGE_CONDITIONS:
            raise ValueError(f"Storage condition must be one of: {', '.join(sorted(VALID_STORAGE_CONDITIONS))}")
        return norm

    @model_validator(mode="after")
    def check_dates(self) -> "SurplusListingCreate":
        now = datetime.now(timezone.utc)
        deadline = self.estimated_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)

        prep = self.harvest_or_prep_date
        if prep.tzinfo is None:
            prep = prep.replace(tzinfo=timezone.utc)

        if deadline <= prep:
            raise ValueError("Estimated usable deadline must be after harvest or preparation date.")

        if deadline <= now:
            raise ValueError("Estimated usable deadline cannot be in the past. Food is already expired.")

        return self


class SurplusListingUpdate(BaseModel):
    item_name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    remaining_quantity_kg: Optional[Decimal] = Field(None, ge=0)
    estimated_deadline: Optional[datetime] = None
    food_condition: Optional[str] = None
    storage_condition: Optional[str] = None
    pickup_address: Optional[str] = None
    handling_instructions: Optional[str] = None

    @field_validator("food_condition")
    @classmethod
    def check_condition(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            norm = v.strip().upper()
            if norm not in VALID_FOOD_CONDITIONS:
                raise ValueError(f"Condition must be one of: {', '.join(sorted(VALID_FOOD_CONDITIONS))}")
            return norm
        return None

    @field_validator("storage_condition")
    @classmethod
    def check_storage(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            norm = v.strip().upper()
            if norm not in VALID_STORAGE_CONDITIONS:
                raise ValueError(f"Storage condition must be one of: {', '.join(sorted(VALID_STORAGE_CONDITIONS))}")
            return norm
        return None


class SurplusListingResponse(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    food_category: str
    item_name: str
    description: Optional[str] = None
    initial_quantity_kg: Decimal
    remaining_quantity_kg: Decimal
    storage_condition: str
    food_condition: str
    harvest_or_prep_date: datetime
    preparation_date: Optional[datetime] = None
    estimated_deadline: datetime
    pickup_address: Optional[str] = None
    handling_instructions: Optional[str] = None
    urgency_classification: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SurplusPaginationResponse(BaseModel):
    items: List[SurplusListingResponse]
    total: int
    page: int
    page_size: int
    pages: int
