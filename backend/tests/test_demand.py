import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest


def register_and_login(client, name: str, email: str, role: str) -> str:
    """Helper to register and login a user, returning their access token."""
    client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": "StrongPassword123!", "role": role},
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPassword123!"},
    )
    return res.json()["access_token"]


def create_receiver_with_profile(client, email="receiver@test.com"):
    token = register_and_login(client, "Community Shelter", email, "RECEIVER")
    headers = {"Authorization": f"Bearer {token}"}
    profile_payload = {
        "organization_name": "Hope Community Kitchen",
        "contact_phone": "+1-555-9876",
        "address": "456 Compassion Blvd",
        "state": "California",
        "district": "San Francisco",
        "city": "San Francisco",
        "latitude": 37.7833,
        "longitude": -122.4167,
        "receiver_category": "COMMUNITY_KITCHEN",
        "capacity_daily_kg": 250.0,
        "operating_hours": {"mon_sun": "07:00-19:00"},
        "cold_storage_capabilities": {"refrigeration": True, "freezer": False},
        "dietary_handling_capabilities": ["VEGETARIAN", "HALAL"],
        "priority_level": 4,
        "description": "Daily warm meals for families in need.",
    }
    res = client.post("/api/v1/receivers/profile", json=profile_payload, headers=headers)
    assert res.status_code == 201, f"Receiver profile creation failed: {res.text}"
    return token, headers


def test_receiver_must_complete_profile_before_demand(client):
    """Receiver without a profile cannot register demand requests."""
    token = register_and_login(client, "No Receiver Profile", "noreceiver@test.com", "RECEIVER")
    headers = {"Authorization": f"Bearer {token}"}

    now = datetime.now(timezone.utc)
    payload = {
        "food_category": "GRAINS",
        "item_name": "Rice & Lentils",
        "requested_quantity_kg": 50.0,
        "required_by": (now + timedelta(days=2)).isoformat(),
        "storage_capability": "AMBIENT",
    }
    res = client.post("/api/v1/demand-requests", json=payload, headers=headers)
    assert res.status_code == 400
    assert "Receiver profile must be completed" in res.json()["detail"]


def test_supplier_cannot_access_demand_endpoints(client):
    """Suppliers are forbidden from managing receiver demand requests."""
    token = register_and_login(client, "Supplier User", "supplier_access@test.com", "SUPPLIER")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/demand-requests", headers=headers)
    assert res.status_code == 403


def test_unauthenticated_demand_access_rejected(client):
    """Anonymous requests must be rejected with 401."""
    res = client.get("/api/v1/demand-requests")
    assert res.status_code == 401


def test_create_demand_request_success_and_defaults(client):
    """Receiver creates demand request and inherits default facility address."""
    token, headers = create_receiver_with_profile(client, "kitchen@test.com")

    now = datetime.now(timezone.utc)
    payload = {
        "food_category": "VEGETABLES",
        "item_name": "Fresh Greens for Salad",
        "description": "Needed for lunchtime salad bar.",
        "requested_quantity_kg": 30.0,
        "required_by": (now + timedelta(hours=36)).isoformat(),
        "acceptable_food_condition": "GOOD",
        "dietary_requirements": ["VEGETARIAN", "VEGAN"],
        "storage_capability": "REFRIGERATED",
        "priority_weight": 4,
    }
    res = client.post("/api/v1/demand-requests", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()

    assert data["item_name"] == "Fresh Greens for Salad"
    assert data["food_category"] == "VEGETABLES"
    assert float(data["requested_quantity_kg"]) == 30.0
    assert float(data["fulfilled_quantity_kg"]) == 0.0
    assert float(data["remaining_requirement_kg"]) == 30.0
    assert data["status"] == "OPEN"
    assert data["priority_weight"] == 4
    # Delivery address falls back to receiver profile address
    assert "456 Compassion Blvd" in data["delivery_address"]


def test_create_demand_validation_errors(client):
    """Validation rejects negative quantity, past deadlines, and invalid weights."""
    token, headers = create_receiver_with_profile(client, "demand_val@test.com")
    now = datetime.now(timezone.utc)

    # 1. Non-positive quantity
    bad_qty = {
        "food_category": "GRAINS",
        "requested_quantity_kg": -5,
        "required_by": (now + timedelta(days=1)).isoformat(),
    }
    assert client.post("/api/v1/demand-requests", json=bad_qty, headers=headers).status_code == 422

    # 2. Past required_by deadline
    past_dl = {
        "food_category": "GRAINS",
        "requested_quantity_kg": 20,
        "required_by": (now - timedelta(hours=1)).isoformat(),
    }
    assert client.post("/api/v1/demand-requests", json=past_dl, headers=headers).status_code == 422

    # 3. Invalid priority weight (out of 1-5 range)
    bad_weight = {
        "food_category": "GRAINS",
        "requested_quantity_kg": 20,
        "required_by": (now + timedelta(days=1)).isoformat(),
        "priority_weight": 10,
    }
    assert client.post("/api/v1/demand-requests", json=bad_weight, headers=headers).status_code == 422


def test_list_demands_pagination_and_filters(client):
    """Test pagination and filtering by category and status."""
    token, headers = create_receiver_with_profile(client, "demand_catalog@test.com")
    now = datetime.now(timezone.utc)

    for i in range(3):
        cat = "GRAINS" if i < 2 else "DAIRY"
        payload = {
            "food_category": cat,
            "item_name": f"Requirement {i}",
            "requested_quantity_kg": 15.0 + i,
            "required_by": (now + timedelta(days=2)).isoformat(),
            "storage_capability": "AMBIENT",
        }
        res = client.post("/api/v1/demand-requests", json=payload, headers=headers)
        assert res.status_code == 201

    # List all
    all_res = client.get("/api/v1/demand-requests", headers=headers)
    assert all_res.status_code == 200
    assert all_res.json()["total"] == 3

    # Filter by category
    grains_res = client.get("/api/v1/demand-requests?food_category=GRAINS", headers=headers)
    assert grains_res.status_code == 200
    assert grains_res.json()["total"] == 2

    # Pagination
    page_res = client.get("/api/v1/demand-requests?page=1&page_size=2", headers=headers)
    assert page_res.status_code == 200
    data = page_res.json()
    assert len(data["items"]) == 2
    assert data["pages"] == 2


def test_cross_receiver_isolation(client):
    """Receiver B cannot view, edit, or modify Receiver A's demand request."""
    _, headers_a = create_receiver_with_profile(client, "dem_owner_a@test.com")
    _, headers_b = create_receiver_with_profile(client, "dem_owner_b@test.com")

    now = datetime.now(timezone.utc)
    payload = {
        "food_category": "BAKERY",
        "item_name": "Sliced Sandwich Bread",
        "requested_quantity_kg": 25.0,
        "required_by": (now + timedelta(days=3)).isoformat(),
        "storage_capability": "AMBIENT",
    }
    create_res = client.post("/api/v1/demand-requests", json=payload, headers=headers_a)
    assert create_res.status_code == 201
    demand_id = create_res.json()["id"]

    # Receiver B attempts to view
    assert client.get(f"/api/v1/demand-requests/{demand_id}", headers=headers_b).status_code == 404

    # Receiver B attempts to update
    assert client.patch(
        f"/api/v1/demand-requests/{demand_id}",
        json={"requested_quantity_kg": 40.0},
        headers=headers_b,
    ).status_code == 404

    # Receiver B attempts to pause
    assert client.post(
        f"/api/v1/demand-requests/{demand_id}/pause",
        headers=headers_b,
    ).status_code == 404


def test_update_demand_request(client):
    """Update demand request parameters and check bounds."""
    token, headers = create_receiver_with_profile(client, "demand_updater@test.com")
    now = datetime.now(timezone.utc)

    payload = {
        "food_category": "COOKED_FOOD",
        "item_name": "Hot Soup",
        "requested_quantity_kg": 50.0,
        "required_by": (now + timedelta(hours=24)).isoformat(),
        "storage_capability": "REFRIGERATED",
    }
    create_res = client.post("/api/v1/demand-requests", json=payload, headers=headers)
    demand_id = create_res.json()["id"]

    # Valid partial update
    valid_res = client.patch(
        f"/api/v1/demand-requests/{demand_id}",
        json={"requested_quantity_kg": 75.0, "priority_weight": 5, "description": "High urgency evening soup"},
        headers=headers,
    )
    assert valid_res.status_code == 200
    assert float(valid_res.json()["requested_quantity_kg"]) == 75.0
    assert valid_res.json()["priority_weight"] == 5
    assert valid_res.json()["description"] == "High urgency evening soup"


def test_demand_lifecycle_pause_resume_cancel(client):
    """Test pause, resume, and cancellation state transitions for demand requests."""
    token, headers = create_receiver_with_profile(client, "demand_lifecycle@test.com")
    now = datetime.now(timezone.utc)

    payload = {
        "food_category": "FRUITS",
        "item_name": "Apples and Oranges",
        "requested_quantity_kg": 35.0,
        "required_by": (now + timedelta(days=2)).isoformat(),
        "storage_capability": "AMBIENT",
    }
    create_res = client.post("/api/v1/demand-requests", json=payload, headers=headers)
    demand_id = create_res.json()["id"]

    # 1. Pause open request
    pause_res = client.post(f"/api/v1/demand-requests/{demand_id}/pause", headers=headers)
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == "PAUSED"

    # 2. Cannot pause already paused request
    bad_pause = client.post(f"/api/v1/demand-requests/{demand_id}/pause", headers=headers)
    assert bad_pause.status_code == 400

    # 3. Resume paused request
    resume_res = client.post(f"/api/v1/demand-requests/{demand_id}/resume", headers=headers)
    assert resume_res.status_code == 200
    assert resume_res.json()["status"] == "OPEN"

    # 4. Cancel demand request
    cancel_res = client.post(f"/api/v1/demand-requests/{demand_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # 5. Cannot resume cancelled request
    assert client.post(f"/api/v1/demand-requests/{demand_id}/resume", headers=headers).status_code == 400
