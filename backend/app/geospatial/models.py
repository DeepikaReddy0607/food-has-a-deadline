import uuid
from datetime import datetime
from typing import Optional, List, Literal, Any
from pydantic import BaseModel, Field

FeasibilityStatus = Literal["FEASIBLE", "INFEASIBLE", "UNKNOWN"]
RoutingProvider = Literal["OSRM", "HAVERSINE_FALLBACK"]


class Coordinates(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 Latitude (-90 to +90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 Longitude (-180 to +180)")


class RouteGeometry(BaseModel):
    type: str = Field(default="LineString", description="GeoJSON geometry type")
    coordinates: List[List[float]] = Field(
        ..., description="List of [longitude, latitude] coordinate pairs along the route"
    )


class RouteEstimateRequest(BaseModel):
    receiver_id: uuid.UUID = Field(..., description="Target Receiver Profile UUID")
    surplus_listing_id: uuid.UUID = Field(..., description="Surplus Inventory Listing UUID")
    handling_buffer_minutes: Optional[int] = Field(
        default=30, ge=0, le=360, description="Loading, inspection, and unloading buffer in minutes"
    )


class RouteEstimateResult(BaseModel):
    supplier_id: uuid.UUID
    receiver_id: uuid.UUID
    supplier_name: Optional[str] = None
    receiver_name: Optional[str] = None
    supplier_coordinates: Coordinates
    receiver_coordinates: Coordinates
    straight_line_distance_km: float = Field(..., description="Great-circle Haversine distance in km")
    road_distance_km: float = Field(..., description="Estimated road travel distance in km")
    estimated_travel_minutes: float = Field(..., description="Estimated one-way vehicle travel time in minutes")
    routing_provider: RoutingProvider = Field(..., description="OSRM | HAVERSINE_FALLBACK")
    is_fallback: bool = Field(..., description="True if OSRM was unavailable and mathematical fallback was used")
    route_geometry: Optional[RouteGeometry] = Field(None, description="Actual road route geometry if available")
    feasibility: FeasibilityStatus = Field(..., description="Temporal feasibility: FEASIBLE | INFEASIBLE | UNKNOWN")
    available_minutes: Optional[float] = Field(None, description="Remaining minutes until usable food deadline")
    required_minutes: Optional[float] = Field(None, description="Total required minutes (travel + handling buffer)")
    handling_buffer_minutes: int = Field(default=30, description="Configured handling buffer applied")
    warnings: List[str] = Field(default_factory=list, description="Quality, safety, or fallback warnings")
    evaluated_at: datetime = Field(..., description="Evaluation timestamp (UTC)")
