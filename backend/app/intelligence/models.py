import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field

from app.intelligence.reference_data import FOOD_SAFETY_DISCLAIMER

UrgencyLevel = Literal["CRITICAL", "HIGH", "MODERATE", "LOW", "PENDING"]
DataQualityLevel = Literal["COMPLETE", "PARTIAL", "SUSPECT", "INVALID"]


class PerishabilityEvaluation(BaseModel):
    listing_id: Optional[uuid.UUID] = Field(None, description="UUID of the surplus inventory listing, if evaluated from database")
    remaining_seconds: float = Field(..., description="Seconds remaining until estimated usable deadline (can be negative if expired)")
    remaining_hours: float = Field(..., description="Hours remaining until estimated usable deadline")
    urgency: UrgencyLevel = Field(..., description="Deterministic urgency tier: CRITICAL | HIGH | MODERATE | LOW | PENDING")
    condition: str = Field(..., description="Reported physical food condition (EXCELLENT | GOOD | FAIR | RIPE | IMMINENT_DECAY | IMPERFECT)")
    storage_condition: str = Field(..., description="Reported storage environment (AMBIENT | REFRIGERATED | FROZEN)")
    warnings: List[str] = Field(default_factory=list, description="Actionable warnings and safety verification requirements")
    explanation: str = Field(..., description="Clear human-readable justification for the assigned urgency classification")
    data_quality: DataQualityLevel = Field(..., description="Data completeness and validity assessment: COMPLETE | PARTIAL | SUSPECT | INVALID")
    evaluated_at: datetime = Field(..., description="UTC timestamp when this evaluation was calculated")
    factors: Dict[str, Any] = Field(default_factory=dict, description="Detailed factors contributing to the evaluation")
    disclaimer: str = Field(default=FOOD_SAFETY_DISCLAIMER, description="Statutory food safety inspection disclaimer")


class BatchEvaluationResponse(BaseModel):
    total_evaluated: int
    counts_by_urgency: Dict[str, int]
    items: List[PerishabilityEvaluation]
