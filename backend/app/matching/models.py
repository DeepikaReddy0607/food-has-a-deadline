import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field

EligibilityStatus = Literal["ELIGIBLE", "INELIGIBLE", "REVIEW_REQUIRED"]
ProductMatchLevel = Literal["EXACT", "CATEGORY_COMPATIBLE", "SUBSET_COMPATIBLE", "INCOMPATIBLE", "AMBIGUOUS"]
StorageMatchLevel = Literal["COMPATIBLE", "INCOMPATIBLE", "UNKNOWN"]
QuantityMatchLevel = Literal["FULL_SATISFACTION", "PARTIAL_SATISFACTION", "ZERO_SURPLUS", "ZERO_DEMAND"]


class ProductCompatibilityResult(BaseModel):
    match_level: ProductMatchLevel
    is_compatible: bool
    category_match: bool
    item_match: Optional[bool] = None
    dietary_compatible: bool
    condition_compatible: bool
    dietary_flags: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    notes: str


class StorageCompatibilityResult(BaseModel):
    match_level: StorageMatchLevel
    is_compatible: bool
    required_storage: str
    available_storage: str
    receiver_has_cold_chain: bool
    warnings: List[str] = Field(default_factory=list)
    notes: str


class QuantityCompatibilityResult(BaseModel):
    match_level: QuantityMatchLevel
    is_compatible: bool
    surplus_available_kg: float
    demand_outstanding_kg: float
    matched_quantity_kg: float
    fulfillment_ratio: float = Field(..., description="Fraction of demand met (matched / outstanding)")
    surplus_utilization_ratio: float = Field(..., description="Fraction of surplus used (matched / available)")
    is_partial: bool
    notes: str


class ScoreBreakdown(BaseModel):
    urgency_score: float = Field(..., ge=0.0, le=100.0, description="25% weight: based on remaining shelf life and urgency tier")
    proximity_score: float = Field(..., ge=0.0, le=100.0, description="25% weight: based on road distance between facilities")
    shelf_life_margin_score: float = Field(..., ge=0.0, le=100.0, description="20% weight: based on transit time buffer margin")
    quantity_fit_score: float = Field(..., ge=0.0, le=100.0, description="15% weight: based on quantity match overlap ratio")
    priority_score: float = Field(..., ge=0.0, le=100.0, description="15% weight: based on receiver priority level")
    total_score: float = Field(..., ge=0.0, le=100.0, description="Composite weighted ranking score")


class CandidateMatch(BaseModel):
    candidate_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    surplus_listing_id: uuid.UUID
    demand_request_id: uuid.UUID
    supplier_id: uuid.UUID
    receiver_id: uuid.UUID
    supplier_name: str
    receiver_name: str
    item_name: str
    food_category: str
    eligibility: EligibilityStatus
    is_eligible: bool
    rejection_reasons: List[str] = Field(default_factory=list)
    product_compatibility: ProductCompatibilityResult
    quantity_compatibility: QuantityCompatibilityResult
    storage_compatibility: StorageCompatibilityResult
    perishability_urgency: str
    remaining_shelf_life_hours: float
    transit_feasibility: str = Field(..., description="FEASIBLE | INFEASIBLE | UNKNOWN")
    straight_line_distance_km: float
    road_distance_km: float
    estimated_transit_minutes: float
    handling_buffer_minutes: int
    routing_provider: str = Field(..., description="OSRM | HAVERSINE_FALLBACK")
    is_route_fallback: bool
    receiver_priority: int
    receiver_category: Optional[str] = None
    score: float = Field(..., ge=0.0, le=100.0)
    score_breakdown: ScoreBreakdown
    warnings: List[str] = Field(default_factory=list)
    explanation: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MatchingQueryResponse(BaseModel):
    source_type: Literal["SURPLUS_LISTING", "DEMAND_REQUEST"]
    source_id: uuid.UUID
    source_name: str
    total_candidates: int
    eligible_count: int
    ineligible_count: int
    review_required_count: int
    page: int
    page_size: int
    candidates: List[CandidateMatch]
