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


def create_supplier_with_profile(client, email="supplier@test.com"):
    token = register_and_login(client, "Fresh Farm", email, "SUPPLIER")
    headers = {"Authorization": f"Bearer {token}"}
    profile_payload = {
        "organization_name": "Valley Organics",
        "contact_phone": "+1-555-4321",
        "address": "100 Orchard Way",
        "state": "California",
        "district": "Sonoma",
        "city": "Santa Rosa",
        "latitude": 38.4404,
        "longitude": -122.7141,
        "facility_type": "FARM",
        "operating_hours": {"mon_sun": "06:00-18:00"},
        "storage_capabilities": {"ambient": True, "refrigerated": True},
        "description": "Organic fruit and vegetable producer.",
    }
    client.post("/api/v1/suppliers/profile", json=profile_payload, headers=headers)
    return token, headers


def test_supplier_must_complete_profile_before_listing(client):
    """Supplier without a profile cannot list surplus inventory."""
    token = register_and_login(client, "No Profile", "noprofile@test.com", "SUPPLIER")
    headers = {"Authorization": f"Bearer {token}"}

    now = datetime.now(timezone.utc)
    payload = {
        "food_category": "FRUITS",
        "item_name": "Fresh Apples",
        "initial_quantity_kg": 25.5,
        "harvest_or_prep_date": (now - timedelta(hours=2)).isoformat(),
        "estimated_deadline": (now + timedelta(days=3)).isoformat(),
        "food_condition": "GOOD",
        "storage_condition": "AMBIENT",
    }
    res = client.post("/api/v1/surplus-listings", json=payload, headers=headers)
    assert res.status_code == 400
    assert "Supplier profile must be completed" in res.json()["detail"]


def test_receiver_cannot_access_surplus_endpoints(client):
    """Receivers are forbidden from managing surplus listings."""
    token = register_and_login(client, "Shelter Receiver", "shelter@test.com", "RECEIVER")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/surplus-listings", headers=headers)
    assert res.status_code == 403


def test_unauthenticated_surplus_access_rejected(client):
    """Anonymous requests must be rejected with 401."""
    res = client.get("/api/v1/surplus-listings")
    assert res.status_code == 401


def test_create_surplus_listing_success_and_defaults(client):
    """Supplier creates surplus listing and inherits default facility address."""
    token, headers = create_supplier_with_profile(client, "orchard@test.com")

    now = datetime.now(timezone.utc)
    payload = {
        "food_category": "VEGETABLES",
        "item_name": "Organic Heirloom Tomatoes",
        "description": "Surplus ripe tomatoes from morning harvest.",
        "initial_quantity_kg": 45.0,
        "harvest_or_prep_date": (now - timedelta(hours=4)).isoformat(),
        "estimated_deadline": (now + timedelta(days=2)).isoformat(),
        "food_condition": "EXCELLENT",
        "storage_condition": "AMBIENT",
        "handling_instructions": "Keep ventilated and shaded.",
    }
    res = client.post("/api/v1/surplus-listings", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()

    assert data["item_name"] == "Organic Heirloom Tomatoes"
    assert data["food_category"] == "VEGETABLES"
    assert float(data["initial_quantity_kg"]) == 45.0
    assert float(data["remaining_quantity_kg"]) == 45.0
    assert data["status"] == "ACTIVE"
    assert data["urgency_classification"] == "MODERATE"
    # Pickup address falls back to supplier profile address
    assert "100 Orchard Way" in data["pickup_address"]


def test_create_surplus_listing_validation_errors(client):
    """Validation handles negative quantity, past deadlines, and invalid categories."""
    token, headers = create_supplier_with_profile(client, "validator@test.com")
    now = datetime.now(timezone.utc)

    # 1. Non-positive quantity
    bad_qty = {
        "food_category": "FRUITS",
        "item_name": "Invalid Qty",
        "initial_quantity_kg": -10,
        "harvest_or_prep_date": (now - timedelta(hours=2)).isoformat(),
        "estimated_deadline": (now + timedelta(days=2)).isoformat(),
    }
    assert client.post("/api/v1/surplus-listings", json=bad_qty, headers=headers).status_code == 422

    # 2. Deadline in the past
    past_dl = {
        "food_category": "FRUITS",
        "item_name": "Expired Food",
        "initial_quantity_kg": 15,
        "harvest_or_prep_date": (now - timedelta(days=3)).isoformat(),
        "estimated_deadline": (now - timedelta(days=1)).isoformat(),
    }
    assert client.post("/api/v1/surplus-listings", json=past_dl, headers=headers).status_code == 422

    # 3. Invalid category
    bad_cat = {
        "food_category": "UNKNOWN_CATEGORY",
        "item_name": "Bad Food",
        "initial_quantity_kg": 15,
        "harvest_or_prep_date": (now - timedelta(hours=2)).isoformat(),
        "estimated_deadline": (now + timedelta(days=2)).isoformat(),
    }
    assert client.post("/api/v1/surplus-listings", json=bad_cat, headers=headers).status_code == 422


def test_list_surplus_listings_pagination_and_filters(client):
    """Test pagination and filtering by category and status."""
    token, headers = create_supplier_with_profile(client, "catalog@test.com")
    now = datetime.now(timezone.utc)

    for i in range(3):
        cat = "FRUITS" if i < 2 else "BAKERY"
        payload = {
            "food_category": cat,
            "item_name": f"Batch {i}",
            "initial_quantity_kg": 10.0 + i,
            "harvest_or_prep_date": (now - timedelta(hours=2)).isoformat(),
            "estimated_deadline": (now + timedelta(days=2)).isoformat(),
        }
        res = client.post("/api/v1/surplus-listings", json=payload, headers=headers)
        assert res.status_code == 201

    # List all
    all_res = client.get("/api/v1/surplus-listings", headers=headers)
    assert all_res.status_code == 200
    assert all_res.json()["total"] == 3

    # Filter by category
    fruits_res = client.get("/api/v1/surplus-listings?food_category=FRUITS", headers=headers)
    assert fruits_res.status_code == 200
    assert fruits_res.json()["total"] == 2

    # Pagination
    page_res = client.get("/api/v1/surplus-listings?page=1&page_size=2", headers=headers)
    assert page_res.status_code == 200
    data = page_res.json()
    assert len(data["items"]) == 2
    assert data["pages"] == 2


def test_cross_supplier_isolation(client):
    """Supplier B cannot view, edit, or modify Supplier A's listing."""
    _, headers_a = create_supplier_with_profile(client, "owner_a@test.com")
    _, headers_b = create_supplier_with_profile(client, "owner_b@test.com")

    now = datetime.now(timezone.utc)
    payload = {
        "food_category": "DAIRY",
        "item_name": "Greek Yogurt",
        "initial_quantity_kg": 20.0,
        "harvest_or_prep_date": (now - timedelta(hours=1)).isoformat(),
        "estimated_deadline": (now + timedelta(days=5)).isoformat(),
        "storage_condition": "REFRIGERATED",
    }
    create_res = client.post("/api/v1/surplus-listings", json=payload, headers=headers_a)
    assert create_res.status_code == 201
    listing_id = create_res.json()["id"]

    # Supplier B attempts to view
    assert client.get(f"/api/v1/surplus-listings/{listing_id}", headers=headers_b).status_code == 404

    # Supplier B attempts to update
    assert client.patch(
        f"/api/v1/surplus-listings/{listing_id}",
        json={"remaining_quantity_kg": 5.0},
        headers=headers_b,
    ).status_code == 404

    # Supplier B attempts to pause
    assert client.post(
        f"/api/v1/surplus-listings/{listing_id}/pause",
        headers=headers_b,
    ).status_code == 404


def test_update_surplus_listing(client):
    """Update listing remaining quantity and boundary checks."""
    token, headers = create_supplier_with_profile(client, "updater@test.com")
    now = datetime.now(timezone.utc)

    payload = {
        "food_category": "GRAINS",
        "item_name": "Surplus Rice Sacks",
        "initial_quantity_kg": 100.0,
        "harvest_or_prep_date": (now - timedelta(hours=1)).isoformat(),
        "estimated_deadline": (now + timedelta(days=10)).isoformat(),
    }
    create_res = client.post("/api/v1/surplus-listings", json=payload, headers=headers)
    listing_id = create_res.json()["id"]

    # 1. Exceeding initial quantity fails
    exceed_res = client.patch(
        f"/api/v1/surplus-listings/{listing_id}",
        json={"remaining_quantity_kg": 120.0},
        headers=headers,
    )
    assert exceed_res.status_code == 400
    assert "cannot exceed initial" in exceed_res.json()["detail"]

    # 2. Valid partial update
    valid_res = client.patch(
        f"/api/v1/surplus-listings/{listing_id}",
        json={"remaining_quantity_kg": 60.0, "description": "Updated description"},
        headers=headers,
    )
    assert valid_res.status_code == 200
    assert float(valid_res.json()["remaining_quantity_kg"]) == 60.0
    assert valid_res.json()["description"] == "Updated description"

    # 3. Setting remaining quantity to 0 transitions status to DEPLETED
    deplete_res = client.patch(
        f"/api/v1/surplus-listings/{listing_id}",
        json={"remaining_quantity_kg": 0.0},
        headers=headers,
    )
    assert deplete_res.status_code == 200
    assert deplete_res.json()["status"] == "DEPLETED"


def test_surplus_lifecycle_pause_resume_cancel(client):
    """Test pause, resume, and cancellation state transitions."""
    token, headers = create_supplier_with_profile(client, "lifecycle@test.com")
    now = datetime.now(timezone.utc)

    payload = {
        "food_category": "COOKED_FOOD",
        "item_name": "Prepared Meals",
        "initial_quantity_kg": 30.0,
        "harvest_or_prep_date": (now - timedelta(hours=1)).isoformat(),
        "estimated_deadline": (now + timedelta(hours=12)).isoformat(),
        "storage_condition": "REFRIGERATED",
    }
    create_res = client.post("/api/v1/surplus-listings", json=payload, headers=headers)
    listing_id = create_res.json()["id"]

    # 1. Pause active listing
    pause_res = client.post(f"/api/v1/surplus-listings/{listing_id}/pause", headers=headers)
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == "PAUSED"

    # 2. Cannot pause already paused listing
    bad_pause = client.post(f"/api/v1/surplus-listings/{listing_id}/pause", headers=headers)
    assert bad_pause.status_code == 400

    # 3. Resume paused listing
    resume_res = client.post(f"/api/v1/surplus-listings/{listing_id}/resume", headers=headers)
    assert resume_res.status_code == 200
    assert resume_res.json()["status"] == "ACTIVE"

    # 4. Cancel listing
    cancel_res = client.post(f"/api/v1/surplus-listings/{listing_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # 5. Cannot resume cancelled listing
    assert client.post(f"/api/v1/surplus-listings/{listing_id}/resume", headers=headers).status_code == 400
