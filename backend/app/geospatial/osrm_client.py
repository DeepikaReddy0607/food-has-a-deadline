import logging
from typing import Optional, Dict, Any
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class OSRMClient:
    """
    HTTP client for the Open Source Routing Machine (OSRM) driving profile.
    Treats public OSRM as a demonstration service with strict timeouts,
    per-instance coordinate route caching to prevent redundant queries, and robust fallback.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        self.base_url = (base_url or settings.OSRM_BASE_URL).rstrip("/")
        self.timeout = timeout_seconds or settings.OSRM_TIMEOUT_SECONDS
        self._cache: Dict[Any, Optional[Dict[str, Any]]] = {}

    def get_driving_route(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Request driving route between origin and destination coordinates.
        Note: OSRM expects coordinates in {longitude},{latitude} order.
        Returns parsed route details dictionary or None on failure.
        """
        cache_key = (round(origin_lat, 5), round(origin_lon, 5), round(dest_lat, 5), round(dest_lon, 5))
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Format: /route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson
        url = (
            f"{self.base_url}/route/v1/driving/"
            f"{origin_lon:.6f},{origin_lat:.6f};{dest_lon:.6f},{dest_lat:.6f}"
            "?overview=full&geometries=geojson"
        )

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)
                if response.status_code != 200:
                    logger.warning(
                        f"OSRM service returned HTTP {response.status_code}: {response.text[:200]}"
                    )
                    self._cache[cache_key] = None
                    return None

                data = response.json()
                if data.get("code") != "Ok" or not data.get("routes"):
                    logger.warning(f"OSRM returned non-success code: {data.get('code')}")
                    self._cache[cache_key] = None
                    return None

                route = data["routes"][0]
                distance_meters = float(route.get("distance", 0.0))
                duration_seconds = float(route.get("duration", 0.0))
                geometry = route.get("geometry")

                res = {
                    "road_distance_km": round(distance_meters / 1000.0, 2),
                    "travel_minutes": round(duration_seconds / 60.0, 1),
                    "geometry": geometry,
                    "provider": "OSRM",
                }
                self._cache[cache_key] = res
                return res

        except httpx.TimeoutException:
            logger.warning(
                f"OSRM routing request timed out after {self.timeout}s. Invoking fallback."
            )
            self._cache[cache_key] = None
            return None
        except httpx.RequestError as exc:
            logger.warning(f"OSRM connection failed ({type(exc).__name__}): {exc}. Invoking fallback.")
            self._cache[cache_key] = None
            return None
        except Exception as exc:
            logger.error(f"Unexpected error querying OSRM: {exc}. Invoking fallback.")
            self._cache[cache_key] = None
            return None
