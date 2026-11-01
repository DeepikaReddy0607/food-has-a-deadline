import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock
import httpx
import pytest

from app.geospatial.distance_calculator import (
    validate_wgs84_coordinates,
    haversine_distance,
    approximate_road_distance,
    approximate_travel_duration_minutes,
)
from app.geospatial.osrm_client import OSRMClient
from app.geospatial.feasibility_checker import FeasibilityChecker
from app.geospatial.routing_service import RoutingService


# =============================================================================
# 1. HAVERSINE & MATHEMATICAL DISTANCE TESTS
# =============================================================================

class TestHaversineAndDistanceCalculator:
    def test_haversine_coincident_points(self):
        """Coincident points must return exactly 0.0 km."""
        assert haversine_distance(37.7749, -122.4194, 37.7749, -122.4194) == 0.0

    def test_haversine_known_reference_distance(self):
        """
        Verify Haversine against known great-circle distance:
        San Francisco Ferry Building (37.7955, -122.3937) to
        Oakland City Center (37.8044, -122.2711) is ~10.8 km.
        """
        dist = haversine_distance(37.7955, -122.3937, 37.8044, -122.2711)
        assert 10.5 <= dist <= 11.2

    def test_haversine_out_of_bounds_validation(self):
        """Out of bounds WGS84 coordinates must raise ValueError."""
        with pytest.raises(ValueError, match="out of WGS84 bounds"):
            validate_wgs84_coordinates(91.0, 0.0)

        with pytest.raises(ValueError, match="out of WGS84 bounds"):
            validate_wgs84_coordinates(-90.5, 0.0)

        with pytest.raises(ValueError, match="out of WGS84 bounds"):
            validate_wgs84_coordinates(0.0, 180.5)

        with pytest.raises(ValueError, match="out of WGS84 bounds"):
            validate_wgs84_coordinates(0.0, -181.0)

        with pytest.raises(ValueError, match="must be valid numerical values"):
            validate_wgs84_coordinates(float("nan"), 0.0)

    def test_approximate_road_distance(self):
        """Test road network circuity approximation."""
        straight_km = 20.0
        # Default circuity 1.35x -> 27.0 km
        assert approximate_road_distance(straight_km, 1.35) == 27.0

        with pytest.raises(ValueError, match="Circuity factor cannot be less than 1.0"):
            approximate_road_distance(10.0, 0.9)

        with pytest.raises(ValueError, match="Distance cannot be negative"):
            approximate_road_distance(-5.0, 1.35)

    def test_approximate_travel_duration_minutes(self):
        """Test duration estimation based on road distance and speed."""
        # 35.0 km at 35.0 km/h is 1.0 hour = 60.0 minutes
        assert approximate_travel_duration_minutes(35.0, 35.0) == 60.0
        # 17.5 km at 35.0 km/h is 30.0 minutes
        assert approximate_travel_duration_minutes(17.5, 35.0) == 30.0

        with pytest.raises(ValueError, match="Average speed must be greater than 0"):
            approximate_travel_duration_minutes(10.0, 0.0)

        with pytest.raises(ValueError, match="Road distance cannot be negative"):
            approximate_travel_duration_minutes(-10.0, 35.0)


# =============================================================================
# 2. OSRM CLIENT & FALLBACK ROUTING TESTS
# =============================================================================

class TestOSRMClient:
    def test_osrm_successful_response(self):
        """Successful OSRM HTTP 200 parsed into road distance, duration, and GeoJSON geometry."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": "Ok",
            "routes": [
                {
                    "distance": 15420.5,  # meters
                    "duration": 1380.0,   # seconds (23 mins)
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [-122.4194, 37.7749],
                            [-122.3937, 37.7955],
                        ],
                    },
                }
            ],
        }

        with patch("httpx.Client.get", return_value=mock_response):
            client = OSRMClient(base_url="http://mock-osrm", timeout_seconds=1.0)
            res = client.get_driving_route(37.7749, -122.4194, 37.7955, -122.3937)

            assert res is not None
            assert res["road_distance_km"] == 15.42
            assert res["travel_minutes"] == 23.0
            assert res["provider"] == "OSRM"
            assert res["geometry"]["type"] == "LineString"
            assert len(res["geometry"]["coordinates"]) == 2

    def test_osrm_server_error_returns_none(self):
        """OSRM HTTP 500 error returns None without raising an uncaught exception."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.Client.get", return_value=mock_response):
            client = OSRMClient(base_url="http://mock-osrm")
            res = client.get_driving_route(37.7749, -122.4194, 37.7955, -122.3937)
            assert res is None

    def test_osrm_timeout_returns_none(self):
        """OSRM timeout returns None to trigger graceful fallback."""
        with patch("httpx.Client.get", side_effect=httpx.TimeoutException("Connection timed out")):
            client = OSRMClient(base_url="http://mock-osrm", timeout_seconds=0.5)
            res = client.get_driving_route(37.7749, -122.4194, 37.7955, -122.3937)
            assert res is None

    def test_osrm_request_error_returns_none(self):
        """OSRM network error returns None to trigger graceful fallback."""
        with patch("httpx.Client.get", side_effect=httpx.RequestError("Host unreachable")):
            client = OSRMClient(base_url="http://mock-osrm")
            res = client.get_driving_route(37.7749, -122.4194, 37.7955, -122.3937)
            assert res is None

    def test_osrm_no_route_code_returns_none(self):
        """Non-'Ok' code from OSRM returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": "NoRoute", "routes": []}

        with patch("httpx.Client.get", return_value=mock_response):
            client = OSRMClient(base_url="http://mock-osrm")
            res = client.get_driving_route(37.7749, -122.4194, 37.7955, -122.3937)
            assert res is None


class TestRoutingServiceFallback:
    def test_routing_service_uses_fallback_when_osrm_unavailable(self):
        """When OSRM fails, RoutingService uses mathematical circuity fallback and does NOT fake geometry."""
        mock_osrm = MagicMock(spec=OSRMClient)
        mock_osrm.get_driving_route.return_value = None  # OSRM down

        service = RoutingService(osrm_client=mock_osrm)
        sup_id = uuid.uuid4()
        rec_id = uuid.uuid4()

        result = service.estimate_route(
            supplier_id=sup_id,
            receiver_id=rec_id,
            supplier_lat=37.7749,
            supplier_lon=-122.4194,
            dest_lat=37.8044,
            dest_lon=-122.2711,
            estimated_usable_deadline=datetime.now(timezone.utc) + timedelta(hours=3),
            handling_buffer_minutes=30,
        )

        assert result.routing_provider == "HAVERSINE_FALLBACK"
        assert result.is_fallback is True
        assert result.route_geometry is None  # Must never fabricate turn-by-turn road geometry!
        assert result.straight_line_distance_km > 0
        assert result.road_distance_km == round(result.straight_line_distance_km * 1.35, 2)
        assert any("FALLBACK ESTIMATE" in w for w in result.warnings)


# =============================================================================
# 3. FEASIBILITY CHECKER TESTS
# =============================================================================

class TestFeasibilityChecker:
    def test_feasible_ample_time(self):
        """Deadline is 4 hours away, travel is 30m, buffer is 30m -> FEASIBLE."""
        now = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
        deadline = now + timedelta(hours=4)

        res = FeasibilityChecker.check_feasibility(
            estimated_usable_deadline=deadline,
            estimated_travel_minutes=30.0,
            handling_buffer_minutes=30,
            evaluation_time=now,
        )

        assert res["feasibility"] == "FEASIBLE"
        assert res["available_minutes"] == 240.0
        assert res["required_minutes"] == 60.0
        # Slack is 180 min (>= 60), so no tight margin warning
        assert not any("TIGHT MARGIN" in w for w in res["warnings"])

    def test_feasible_tight_margin(self):
        """Available time is 75 mins, required is 60 mins -> FEASIBLE with TIGHT MARGIN warning."""
        now = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
        deadline = now + timedelta(minutes=75)

        res = FeasibilityChecker.check_feasibility(
            estimated_usable_deadline=deadline,
            estimated_travel_minutes=30.0,
            handling_buffer_minutes=30,
            evaluation_time=now,
        )

        assert res["feasibility"] == "FEASIBLE"
        assert res["available_minutes"] == 75.0
        assert res["required_minutes"] == 60.0
        assert any("TIGHT MARGIN" in w for w in res["warnings"])

    def test_infeasible_required_exceeds_available(self):
        """Available time is 45 mins, required is 60 mins -> INFEASIBLE."""
        now = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
        deadline = now + timedelta(minutes=45)

        res = FeasibilityChecker.check_feasibility(
            estimated_usable_deadline=deadline,
            estimated_travel_minutes=30.0,
            handling_buffer_minutes=30,
            evaluation_time=now,
        )

        assert res["feasibility"] == "INFEASIBLE"
        assert any("TEMPORALLY INFEASIBLE: Required delivery time" in w for w in res["warnings"])

    def test_infeasible_deadline_already_passed(self):
        """Deadline has already expired -> INFEASIBLE."""
        now = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
        deadline = now - timedelta(minutes=15)

        res = FeasibilityChecker.check_feasibility(
            estimated_usable_deadline=deadline,
            estimated_travel_minutes=25.0,
            handling_buffer_minutes=30,
            evaluation_time=now,
        )

        assert res["feasibility"] == "INFEASIBLE"
        assert any("Usable deadline passed" in w for w in res["warnings"])

    def test_unknown_feasibility_when_missing_deadline(self):
        """Missing usable deadline returns UNKNOWN."""
        res = FeasibilityChecker.check_feasibility(
            estimated_usable_deadline=None,
            estimated_travel_minutes=25.0,
            handling_buffer_minutes=30,
        )
        assert res["feasibility"] == "UNKNOWN"
        assert any("DATA QUALITY WARNING" in w for w in res["warnings"])


# =============================================================================
# 4. API INTEGRATION & ROLE-BASED ACCESS CONTROL TESTS
# =============================================================================

def register_and_login(client, name: str, email: str, role: str) -> str:
    client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": "SecurePassword123!", "role": role},
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    return res.json()["access_token"]


def create_supplier_and_listing(client, email="sup_geo@test.com"):
    token = register_and_login(client, "Supplier Geo", email, "SUPPLIER")
    headers = {"Authorization": f"Bearer {token}"}
    profile_payload = {
        "organization_name": "San Francisco Central Farm",
        "contact_phone": "+1-555-1111",
        "address": "1 Ferry Plaza",
        "state": "California",
        "district": "San Francisco",
        "city": "San Francisco",
        "latitude": 37.7955,
        "longitude": -122.3937,
        "facility_type": "FARM",
    }
    client.post("/api/v1/suppliers/profile", json=profile_payload, headers=headers)

    now = datetime.now(timezone.utc)
    listing_payload = {
        "food_category": "VEGETABLES",
        "item_name": "Hydroponic Lettuce",
        "initial_quantity_kg": 50.0,
        "harvest_or_prep_date": (now - timedelta(hours=3)).isoformat(),
        "estimated_deadline": (now + timedelta(hours=6)).isoformat(),
        "food_condition": "EXCELLENT",
        "storage_condition": "REFRIGERATED",
    }
    res = client.post("/api/v1/surplus-listings", json=listing_payload, headers=headers)
    listing_id = res.json()["id"]
    return token, headers, listing_id


def create_receiver(client, email="rec_geo@test.com"):
    token = register_and_login(client, "Receiver Geo", email, "RECEIVER")
    headers = {"Authorization": f"Bearer {token}"}
    profile_payload = {
        "organization_name": "Oakland Community Food Bank",
        "contact_phone": "+1-555-2222",
        "address": "123 City Center",
        "state": "California",
        "district": "Alameda",
        "city": "Oakland",
        "latitude": 37.8044,
        "longitude": -122.2711,
        "receiver_category": "FOOD_BANK",
        "capacity_daily_kg": 500.0,
        "priority_level": 4,
    }
    res = client.post("/api/v1/receivers/profile", json=profile_payload, headers=headers)
    receiver_id = res.json()["id"]
    return token, headers, receiver_id


def test_supplier_estimates_route_to_receiver(client):
    """Supplier can estimate route and feasibility from their listing to a registered receiver."""
    sup_token, sup_headers, listing_id = create_supplier_and_listing(client, "sup1@test.com")
    rec_token, rec_headers, receiver_id = create_receiver(client, "rec1@test.com")

    payload = {
        "surplus_listing_id": listing_id,
        "receiver_id": receiver_id,
        "handling_buffer_minutes": 30,
    }

    res = client.post("/api/v1/geospatial/route-estimate", json=payload, headers=sup_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["supplier_id"] is not None
    assert data["receiver_id"] == receiver_id
    assert data["supplier_name"] == "San Francisco Central Farm"
    assert data["receiver_name"] == "Oakland Community Food Bank"
    assert data["straight_line_distance_km"] > 0
    assert data["road_distance_km"] > 0
    assert data["estimated_travel_minutes"] > 0
    assert data["feasibility"] in ["FEASIBLE", "INFEASIBLE", "UNKNOWN"]
    assert data["routing_provider"] in ["OSRM", "HAVERSINE_FALLBACK"]


def test_supplier_cannot_access_other_supplier_listing(client):
    """Supplier 2 cannot estimate route for Supplier 1's surplus listing."""
    sup1_token, sup1_headers, listing1_id = create_supplier_and_listing(client, "sup_owner@test.com")
    sup2_token, sup2_headers, _ = create_supplier_and_listing(client, "sup_intruder@test.com")
    rec_token, rec_headers, receiver_id = create_receiver(client, "rec_sec@test.com")

    payload = {
        "surplus_listing_id": listing1_id,
        "receiver_id": receiver_id,
        "handling_buffer_minutes": 30,
    }

    res = client.post("/api/v1/geospatial/route-estimate", json=payload, headers=sup2_headers)
    assert res.status_code == 404
    assert "Surplus listing not found" in res.json()["detail"]


def test_receiver_estimates_route_for_own_facility(client):
    """Receiver can estimate route for their own facility from a surplus listing."""
    sup_token, sup_headers, listing_id = create_supplier_and_listing(client, "sup_for_rec@test.com")
    rec_token, rec_headers, receiver_id = create_receiver(client, "rec_own@test.com")

    payload = {
        "surplus_listing_id": listing_id,
        "receiver_id": receiver_id,
        "handling_buffer_minutes": 25,
    }

    res = client.post("/api/v1/geospatial/route-estimate", json=payload, headers=rec_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["receiver_id"] == receiver_id
    assert data["handling_buffer_minutes"] == 25


def test_receiver_cannot_estimate_route_for_other_receiver(client):
    """Receiver 2 cannot estimate route specifying Receiver 1's ID."""
    sup_token, sup_headers, listing_id = create_supplier_and_listing(client, "sup_multi@test.com")
    rec1_token, rec1_headers, rec1_id = create_receiver(client, "rec_first@test.com")
    rec2_token, rec2_headers, rec2_id = create_receiver(client, "rec_second@test.com")

    payload = {
        "surplus_listing_id": listing_id,
        "receiver_id": rec1_id,  # Receiver 2 specifies Receiver 1's ID
    }

    res = client.post("/api/v1/geospatial/route-estimate", json=payload, headers=rec2_headers)
    assert res.status_code == 404
    assert "Receiver facility profile not found" in res.json()["detail"]


def test_coordinator_can_estimate_any_route(client, db_session):
    """Coordinators have authority to estimate routes across any supplier and receiver."""
    from app.models.user import User
    from app.core.security import hash_password, create_access_token

    # Admin/Coordinator creation directly in database
    coord_user = User(
        email="coord_geo@test.com",
        hashed_password=hash_password("Password123!"),
        role="COORDINATOR",
        is_active=True,
    )
    db_session.add(coord_user)
    db_session.commit()
    db_session.refresh(coord_user)

    coord_token = create_access_token(coord_user.id, coord_user.role)
    coord_headers = {"Authorization": f"Bearer {coord_token}"}

    sup_token, sup_headers, listing_id = create_supplier_and_listing(client, "sup_coord@test.com")
    rec_token, rec_headers, receiver_id = create_receiver(client, "rec_coord@test.com")

    payload = {
        "surplus_listing_id": listing_id,
        "receiver_id": receiver_id,
    }

    res = client.post("/api/v1/geospatial/route-estimate", json=payload, headers=coord_headers)
    assert res.status_code == 200
    assert res.json()["supplier_name"] == "San Francisco Central Farm"


def test_unauthenticated_request_rejected(client):
    """Anonymous request to route estimate returns 401."""
    res = client.post(
        "/api/v1/geospatial/route-estimate",
        json={"surplus_listing_id": str(uuid.uuid4()), "receiver_id": str(uuid.uuid4())},
    )
    assert res.status_code == 401


def test_receivers_directory_endpoint(client):
    """Authenticated users can query the receiver directory to choose destinations."""
    token = register_and_login(client, "Directory User", "dir_user@test.com", "SUPPLIER")
    headers = {"Authorization": f"Bearer {token}"}

    # Add a receiver to the database
    create_receiver(client, "rec_dir@test.com")

    res = client.get("/api/v1/receivers/directory", headers=headers)
    assert res.status_code == 200
    receivers = res.json()
    assert isinstance(receivers, list)
    assert len(receivers) >= 1
    assert receivers[0]["organization_name"] == "Oakland Community Food Bank"
    assert receivers[0]["latitude"] is not None
    assert receivers[0]["longitude"] is not None
