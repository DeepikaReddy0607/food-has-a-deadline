import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from app.core.config import settings
from app.geospatial.models import (
    Coordinates,
    RouteGeometry,
    RouteEstimateResult,
    RoutingProvider,
)
from app.geospatial.distance_calculator import (
    validate_wgs84_coordinates,
    haversine_distance,
    approximate_road_distance,
    approximate_travel_duration_minutes,
)
from app.geospatial.osrm_client import OSRMClient
from app.geospatial.feasibility_checker import FeasibilityChecker


class RoutingService:
    """
    Provider-independent Geospatial Routing Service.
    Coordinates route estimation, external OSRM queries, mathematical fallbacks,
    and deterministic shelf-life transit feasibility checks.
    """

    def __init__(self, osrm_client: Optional[OSRMClient] = None):
        self.osrm_client = osrm_client or OSRMClient()

    def estimate_route(
        self,
        supplier_id: uuid.UUID,
        receiver_id: uuid.UUID,
        supplier_lat: float,
        supplier_lon: float,
        dest_lat: float,
        dest_lon: float,
        estimated_usable_deadline: Optional[datetime] = None,
        handling_buffer_minutes: int = 30,
        supplier_name: Optional[str] = None,
        receiver_name: Optional[str] = None,
        evaluation_time: Optional[datetime] = None,
    ) -> RouteEstimateResult:
        warnings: List[str] = []
        now = evaluation_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # 1. Validate coordinates
        s_lat, s_lon = validate_wgs84_coordinates(supplier_lat, supplier_lon)
        r_lat, r_lon = validate_wgs84_coordinates(dest_lat, dest_lon)

        # 2. Straight-line distance
        straight_line_km = haversine_distance(s_lat, s_lon, r_lat, r_lon)

        # 3. Query OSRM
        osrm_result = self.osrm_client.get_driving_route(s_lat, s_lon, r_lat, r_lon)

        road_distance_km: float
        estimated_travel_minutes: float
        routing_provider: RoutingProvider
        is_fallback: bool
        route_geometry: Optional[RouteGeometry] = None

        if osrm_result is not None:
            road_distance_km = osrm_result["road_distance_km"]
            estimated_travel_minutes = osrm_result["travel_minutes"]
            routing_provider = "OSRM"
            is_fallback = False
            if osrm_result.get("geometry"):
                route_geometry = RouteGeometry(**osrm_result["geometry"])
        else:
            # Fallback strategy
            circuity = settings.DEFAULT_CIRCUITY_FACTOR
            speed = settings.DEFAULT_AVERAGE_SPEED_KMH

            road_distance_km = approximate_road_distance(straight_line_km, circuity)
            estimated_travel_minutes = approximate_travel_duration_minutes(road_distance_km, speed)
            routing_provider = "HAVERSINE_FALLBACK"
            is_fallback = True
            route_geometry = None  # Never fabricate route geometry

            warnings.append(
                f"FALLBACK ESTIMATE: OSRM routing service was unavailable. Road distance ({road_distance_km} km) "
                f"and travel duration ({estimated_travel_minutes} mins) were approximated using Haversine "
                f"straight-line distance (circuity factor {circuity}x and {speed} km/h assumed speed). "
                "Confidence is reduced; physical route geometry is unavailable."
            )

        # 4. Check Feasibility
        feasibility_result = FeasibilityChecker.check_feasibility(
            estimated_usable_deadline=estimated_usable_deadline,
            estimated_travel_minutes=estimated_travel_minutes,
            handling_buffer_minutes=handling_buffer_minutes,
            evaluation_time=now,
        )
        warnings.extend(feasibility_result["warnings"])

        return RouteEstimateResult(
            supplier_id=supplier_id,
            receiver_id=receiver_id,
            supplier_name=supplier_name,
            receiver_name=receiver_name,
            supplier_coordinates=Coordinates(latitude=s_lat, longitude=s_lon),
            receiver_coordinates=Coordinates(latitude=r_lat, longitude=r_lon),
            straight_line_distance_km=straight_line_km,
            road_distance_km=road_distance_km,
            estimated_travel_minutes=estimated_travel_minutes,
            routing_provider=routing_provider,
            is_fallback=is_fallback,
            route_geometry=route_geometry,
            feasibility=feasibility_result["feasibility"],
            available_minutes=feasibility_result["available_minutes"],
            required_minutes=feasibility_result["required_minutes"],
            handling_buffer_minutes=handling_buffer_minutes,
            warnings=warnings,
            evaluated_at=now,
        )


# Global singleton instance for injection
routing_service = RoutingService()
