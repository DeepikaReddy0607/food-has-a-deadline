import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from app.matching.models import CandidateMatch


# Scale factor: 1 kg = 100 hundredths of a kilogram (0.01 kg resolution, exact 2 decimal places matching DB schema)
SCALE_FACTOR = 100


def to_hundredths_kg(kg_value: float) -> int:
    """Scale kilograms to integer hundredths of a kilogram (1 kg = 100 hundredth-kg units)."""
    return int(round(kg_value * SCALE_FACTOR))


def to_kg(hundredths_value: int) -> float:
    """Convert integer hundredths of a kilogram back to decimal kilograms."""
    return round(float(hundredths_value) / SCALE_FACTOR, 2)


# Backwards compatibility alias
to_centigrams = to_hundredths_kg


@dataclass
class SurplusNode:
    id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: str
    food_category: str
    item_name: str
    available_kg: float
    available_hundredths_kg: int = 0
    urgency: str = "MODERATE"
    remaining_shelf_life_hours: float = 24.0
    available_centigrams: Optional[int] = None

    def __post_init__(self):
        if self.available_centigrams is not None and not self.available_hundredths_kg:
            self.available_hundredths_kg = self.available_centigrams
        elif self.available_hundredths_kg and self.available_centigrams is None:
            self.available_centigrams = self.available_hundredths_kg


@dataclass
class DemandNode:
    id: uuid.UUID
    receiver_id: uuid.UUID
    receiver_name: str
    food_category: str
    item_name: Optional[str]
    requested_kg: float
    requested_hundredths_kg: int = 0
    priority_level: int = 3
    requested_centigrams: Optional[int] = None

    def __post_init__(self):
        if self.requested_centigrams is not None and not self.requested_hundredths_kg:
            self.requested_hundredths_kg = self.requested_centigrams
        elif self.requested_hundredths_kg and self.requested_centigrams is None:
            self.requested_centigrams = self.requested_hundredths_kg


@dataclass
class EligibleEdge:
    surplus_id: uuid.UUID
    demand_id: uuid.UUID
    max_flow_hundredths_kg: int = 0
    urgency: str = "MODERATE"
    receiver_priority: int = 3
    road_distance_km: float = 0.0
    estimated_transit_minutes: int = 0
    shelf_life_slack_minutes: float = 0.0
    score: float = 0.0
    explanation: str = ""
    candidate_match: Optional[CandidateMatch] = None
    max_flow_centigrams: Optional[int] = None

    def __post_init__(self):
        if self.max_flow_centigrams is not None and not self.max_flow_hundredths_kg:
            self.max_flow_hundredths_kg = self.max_flow_centigrams
        elif self.max_flow_hundredths_kg and self.max_flow_centigrams is None:
            self.max_flow_centigrams = self.max_flow_hundredths_kg


@dataclass
class AllocationProblem:
    surplus_nodes: Dict[uuid.UUID, SurplusNode] = field(default_factory=dict)
    demand_nodes: Dict[uuid.UUID, DemandNode] = field(default_factory=dict)
    eligible_edges: Dict[Tuple[uuid.UUID, uuid.UUID], EligibleEdge] = field(default_factory=dict)

    # Ineligible / Review pairs for diagnostic explanations
    all_evaluated_candidates: List[CandidateMatch] = field(default_factory=list)

    @property
    def total_available_kg(self) -> float:
        return round(sum(s.available_kg for s in self.surplus_nodes.values()), 2)

    @property
    def total_requested_kg(self) -> float:
        return round(sum(d.requested_kg for d in self.demand_nodes.values()), 2)

    def get_edges_for_surplus(self, surplus_id: uuid.UUID) -> List[EligibleEdge]:
        return [edge for (s_id, _), edge in self.eligible_edges.items() if s_id == surplus_id]

    def get_edges_for_demand(self, demand_id: uuid.UUID) -> List[EligibleEdge]:
        return [edge for (_, d_id), edge in self.eligible_edges.items() if d_id == demand_id]
