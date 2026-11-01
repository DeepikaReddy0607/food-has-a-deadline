import math
from typing import Tuple

# WGS84 Mean Earth Radius in kilometers
EARTH_RADIUS_KM = 6371.0088


def validate_wgs84_coordinates(lat: float, lon: float) -> Tuple[float, float]:
    """
    Validate WGS84 coordinate boundaries.
    Latitude: [-90.0, +90.0]
    Longitude: [-180.0, +180.0]
    """
    if lat is None or lon is None or math.isnan(lat) or math.isnan(lon):
        raise ValueError("Latitude and longitude must be valid numerical values.")

    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"Latitude {lat} out of WGS84 bounds [-90.0, +90.0].")

    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"Longitude {lon} out of WGS84 bounds [-180.0, +180.0].")

    return float(lat), float(lon)


def haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """
    Calculate great-circle distance between two points on Earth using Haversine formula.
    Returns distance in kilometers, rounded to 2 decimal places.
    """
    v_lat1, v_lon1 = validate_wgs84_coordinates(lat1, lon1)
    v_lat2, v_lon2 = validate_wgs84_coordinates(lat2, lon2)

    # Coincident coordinates return exactly 0.0 km
    if v_lat1 == v_lat2 and v_lon1 == v_lon2:
        return 0.0

    phi1 = math.radians(v_lat1)
    phi2 = math.radians(v_lat2)
    delta_phi = math.radians(v_lat2 - v_lat1)
    delta_lambda = math.radians(v_lon2 - v_lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )

    # Clamp a within [0.0, 1.0] to guard against floating-point rounding errors
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distance = EARTH_RADIUS_KM * c

    return round(distance, 2)


def approximate_road_distance(
    straight_line_km: float, circuity_factor: float = 1.35
) -> float:
    """
    Approximate road network distance using straight-line distance and a network circuity factor.
    Default circuity factor 1.35 reflects empirical urban/suburban road networks.
    """
    if straight_line_km < 0:
        raise ValueError("Distance cannot be negative.")
    if circuity_factor < 1.0:
        raise ValueError("Circuity factor cannot be less than 1.0 (straight-line minimum).")

    return round(straight_line_km * circuity_factor, 2)


def approximate_travel_duration_minutes(
    road_distance_km: float, average_speed_kmh: float = 35.0
) -> float:
    """
    Estimate transit duration in minutes based on road distance and assumed commercial average speed.
    Default speed 35.0 km/h reflects urban delivery routing with stop-and-go conditions.
    """
    if road_distance_km < 0:
        raise ValueError("Road distance cannot be negative.")
    if average_speed_kmh <= 0:
        raise ValueError("Average speed must be greater than 0 km/h.")

    hours = road_distance_km / average_speed_kmh
    return round(hours * 60.0, 1)
