import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class OptimizationRunRequest(BaseModel):
    """
    Coordinator request parameters to trigger an allocation optimization run.
    """
    surplus_listing_ids: Optional[List[uuid.UUID]] = Field(
        default=None,
        description="Optional subset of surplus listing IDs to include. If omitted, all active listings are considered.",
    )
    demand_request_ids: Optional[List[uuid.UUID]] = Field(
        default=None,
        description="Optional subset of demand request IDs to include. If omitted, all open demands are considered.",
    )
    timeout_seconds: float = Field(
        default=5.0,
        ge=0.1,
        le=60.0,
        description="Maximum solver execution time in seconds.",
    )
    max_distance_km: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=500.0,
        description="Optional maximum road distance threshold for candidate pair consideration.",
    )
    evaluation_time: Optional[datetime] = Field(
        default=None,
        description="Reference evaluation timestamp (defaults to current UTC time).",
    )


class AllocationItemDetail(BaseModel):
    """
    Detailed proposal allocation line item connecting a surplus batch to a receiver demand.
    """
    item_id: Optional[uuid.UUID] = Field(default=None, description="Database ID if persisted")
    proposal_id: Optional[uuid.UUID] = Field(default=None)
    surplus_listing_id: uuid.UUID
    demand_request_id: uuid.UUID
    supplier_id: uuid.UUID
    receiver_id: uuid.UUID
    supplier_name: str
    receiver_name: str
    item_name: str
    food_category: str
    allocated_quantity_kg: float = Field(..., gt=0.0)
    estimated_distance_km: float = Field(..., ge=0.0)
    estimated_transit_minutes: int = Field(..., ge=0)
    urgency_at_allocation: str
    shelf_life_slack_minutes: Optional[float] = None
    allocation_score: float = Field(..., ge=0.0)
    explanation: str


class UnfulfilledDemandDetail(BaseModel):
    """
    Audit diagnostic explaining why a demand request could not be completely fulfilled.
    """
    demand_request_id: uuid.UUID
    receiver_id: uuid.UUID
    receiver_name: str
    food_category: str
    item_name: Optional[str] = None
    requested_quantity_kg: float
    fulfilled_in_proposal_kg: float
    unfulfilled_quantity_kg: float
    reason_code: str = Field(
        ...,
        description="Diagnostic code e.g. NO_COMPATIBLE_SUPPLY, INSUFFICIENT_SUPPLY, TRANSIT_INFEASIBLE, SUPPLY_ALLOCATED_TO_HIGHER_PRIORITY",
    )
    diagnostic_explanation: str


class UnallocatedSurplusDetail(BaseModel):
    """
    Audit diagnostic explaining why a surplus listing has remaining unallocated quantity.
    """
    surplus_listing_id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: str
    food_category: str
    item_name: str
    available_quantity_kg: float
    allocated_in_proposal_kg: float
    unallocated_quantity_kg: float
    urgency: str
    reason_code: str = Field(
        ...,
        description="Diagnostic code e.g. NO_COMPATIBLE_DEMAND, ALL_DEMANDS_FULFILLED, TRANSIT_EXCEEDED_SHELF_LIFE",
    )
    diagnostic_explanation: str


class SolverDiagnostics(BaseModel):
    """
    Mathematical and operational diagnostic metrics from Google OR-Tools execution.
    """
    solver_name: str = "Google OR-Tools CP-SAT"
    solver_status: str = Field(..., description="OPTIMAL | FEASIBLE | INFEASIBLE | MODEL_INVALID | TIMEOUT")
    solve_time_ms: float
    num_surplus_considered: int
    num_demands_considered: int
    num_candidate_pairs: int
    num_variables: int
    num_constraints: int
    objective_value: Optional[float] = None


class OptimizationProposalResponse(BaseModel):
    """
    Complete proposal response returned to the coordinator and persisted in PostgreSQL.
    """
    proposal_id: Optional[uuid.UUID] = Field(default=None, description="Persisted AllocationProposal ID")
    status: str = Field(default="PENDING_REVIEW")
    total_allocated_kg: float = Field(..., ge=0.0)
    total_unallocated_kg: float = Field(..., ge=0.0)
    total_unmet_demand_kg: float = Field(..., ge=0.0)
    estimated_total_transit_km: float = Field(..., ge=0.0)
    solver_status: str
    solve_time_ms: float
    ai_justification: str
    items: List[AllocationItemDetail] = Field(default_factory=list)
    unfulfilled_demands: List[UnfulfilledDemandDetail] = Field(default_factory=list)
    unallocated_surplus: List[UnallocatedSurplusDetail] = Field(default_factory=list)
    diagnostics: SolverDiagnostics
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
