import pytest
from decimal import Decimal


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


def test_supplier_profile_crud_lifecycle(client):
    """Test full CRUD lifecycle for Supplier profile."""
    token = register_and_login(client, "Super Fresh", "supplier1@test.com", "SUPPLIER")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Profile initially not found
    get_init = client.get("/api/v1/suppliers/profile", headers=headers)
    assert get_init.status_code == 404

    # 2. Create Profile
    create_payload = {
        "organization_name": "Super Fresh Grocers",
        "contact_phone": "+1-555-0123",
        "address": "123 Market St, Suite 4",
        "state": "California",
        "district": "San Francisco",
        "city": "San Francisco",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "facility_type": "RETAILER",
        "operating_hours": {"mon_fri": "08:00-20:00"},
        "storage_capabilities": {"ambient": True, "refrigerated": True, "frozen": False},
        "description": "Daily fresh grocery retailer with surplus produce.",
    }
    create_res = client.post("/api/v1/suppliers/profile", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["organization_name"] == "Super Fresh Grocers"
    assert created_data["facility_type"] == "RETAILER"
    assert created_data["storage_capabilities"]["refrigerated"] is True

    # 3. Prevent duplicate profile creation
    dup_res = client.post("/api/v1/suppliers/profile", json=create_payload, headers=headers)
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]

    # 4. Retrieve Profile
    get_res = client.get("/api/v1/suppliers/profile", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == created_data["id"]

    # 5. Partial Update (PATCH)
    patch_payload = {
        "contact_phone": "+1-555-9999",
        "description": "Updated description with new loading dock instructions.",
    }
    patch_res = client.patch("/api/v1/suppliers/profile", json=patch_payload, headers=headers)
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert updated_data["contact_phone"] == "+1-555-9999"
    assert updated_data["description"] == "Updated description with new loading dock instructions."
    # Check that untouched fields are preserved
    assert updated_data["organization_name"] == "Super Fresh Grocers"
    assert updated_data["facility_type"] == "RETAILER"


def test_receiver_profile_crud_lifecycle(client):
    """Test full CRUD lifecycle for Receiver profile."""
    token = register_and_login(client, "City Shelter", "shelter1@test.com", "RECEIVER")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Profile initially not found
    get_init = client.get("/api/v1/receivers/profile", headers=headers)
    assert get_init.status_code == 404

    # 2. Create Profile
    create_payload = {
        "organization_name": "Hope Community Shelter",
        "contact_phone": "+1-555-4567",
        "address": "456 Mission Ave",
        "state": "California",
        "district": "San Francisco",
        "city": "San Francisco",
        "latitude": 37.7833,
        "longitude": -122.4167,
        "receiver_category": "SHELTER",
        "capacity_daily_kg": 350.5,
        "cold_storage_capabilities": {"refrigeration": True, "freezer": True},
        "dietary_handling_capabilities": ["VEGETARIAN", "HALAL"],
        "operating_hours": {"intake_hours": "09:00-17:00"},
        "priority_level": 4,
        "description": "Residential shelter providing 200 daily meals.",
    }
    create_res = client.post("/api/v1/receivers/profile", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["organization_name"] == "Hope Community Shelter"
    assert created_data["priority_level"] == 4
    assert float(created_data["capacity_daily_kg"]) == 350.5

    # 3. Prevent duplicate creation
    dup_res = client.post("/api/v1/receivers/profile", json=create_payload, headers=headers)
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]

    # 4. Retrieve Profile
    get_res = client.get("/api/v1/receivers/profile", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == created_data["id"]

    # 5. Partial Update (PATCH)
    patch_payload = {
        "capacity_daily_kg": 500.0,
        "priority_level": 5,
    }
    patch_res = client.patch("/api/v1/receivers/profile", json=patch_payload, headers=headers)
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert float(updated_data["capacity_daily_kg"]) == 500.0
    assert updated_data["priority_level"] == 5
    # Untouched field preserved
    assert updated_data["organization_name"] == "Hope Community Shelter"


def test_cross_role_access_prevention(client):
    """Verify that a SUPPLIER cannot access RECEIVER profile endpoints, and vice versa."""
    supplier_token = register_and_login(client, "Farm A", "farmA@test.com", "SUPPLIER")
    receiver_token = register_and_login(client, "Shelter A", "shelterA@test.com", "RECEIVER")

    # Supplier calls receiver endpoints -> 403 Forbidden
    res1 = client.get(
        "/api/v1/receivers/profile",
        headers={"Authorization": f"Bearer {supplier_token}"},
    )
    assert res1.status_code == 403
    assert "Operation not permitted" in res1.json()["detail"]

    res2 = client.post(
        "/api/v1/receivers/profile",
        json={"organization_name": "Invalid"},
        headers={"Authorization": f"Bearer {supplier_token}"},
    )
    assert res2.status_code == 403

    # Receiver calls supplier endpoints -> 403 Forbidden
    res3 = client.get(
        "/api/v1/suppliers/profile",
        headers={"Authorization": f"Bearer {receiver_token}"},
    )
    assert res3.status_code == 403

    res4 = client.post(
        "/api/v1/suppliers/profile",
        json={"organization_name": "Invalid"},
        headers={"Authorization": f"Bearer {receiver_token}"},
    )
    assert res4.status_code == 403


def test_unauthenticated_profile_access_prevention(client):
    """Verify endpoints reject unauthenticated requests with 401."""
    assert client.get("/api/v1/suppliers/profile").status_code == 401
    assert client.post("/api/v1/suppliers/profile", json={}).status_code == 401
    assert client.get("/api/v1/receivers/profile").status_code == 401
    assert client.post("/api/v1/receivers/profile", json={}).status_code == 401


def test_profile_validation_constraints(client):
    """Test validation errors for invalid coordinates, phone numbers, capacities, and priority."""
    supplier_token = register_and_login(client, "Bad Data Supplier", "bad_sup@test.com", "SUPPLIER")
    s_headers = {"Authorization": f"Bearer {supplier_token}"}

    receiver_token = register_and_login(client, "Bad Data Receiver", "bad_rec@test.com", "RECEIVER")
    r_headers = {"Authorization": f"Bearer {receiver_token}"}

    # 1. Invalid Latitude (> 90)
    res_lat = client.post(
        "/api/v1/suppliers/profile",
        json={
            "organization_name": "Invalid Lat Co",
            "contact_phone": "+1-555-1234",
            "address": "123 Way",
            "latitude": 95.5,
            "longitude": -122.4,
            "facility_type": "FARM",
        },
        headers=s_headers,
    )
    assert res_lat.status_code == 422
    assert "Latitude must be between -90.0 and 90.0" in res_lat.text

    # 2. Invalid Longitude (< -180)
    res_lon = client.post(
        "/api/v1/suppliers/profile",
        json={
            "organization_name": "Invalid Lon Co",
            "contact_phone": "+1-555-1234",
            "address": "123 Way",
            "latitude": 37.7,
            "longitude": -195.0,
            "facility_type": "FARM",
        },
        headers=s_headers,
    )
    assert res_lon.status_code == 422
    assert "Longitude must be between -180.0 and 180.0" in res_lon.text

    # 3. Invalid Phone Number
    res_phone = client.post(
        "/api/v1/suppliers/profile",
        json={
            "organization_name": "Invalid Phone Co",
            "contact_phone": "abc-no-digits",
            "address": "123 Way",
            "latitude": 37.7,
            "longitude": -122.4,
            "facility_type": "FARM",
        },
        headers=s_headers,
    )
    assert res_phone.status_code == 422
    assert "Invalid phone number format" in res_phone.text

    # 4. Invalid Capacity (<= 0)
    res_cap = client.post(
        "/api/v1/receivers/profile",
        json={
            "organization_name": "Zero Capacity Shelter",
            "contact_phone": "+1-555-1234",
            "address": "123 Way",
            "latitude": 37.7,
            "longitude": -122.4,
            "receiver_category": "SHELTER",
            "capacity_daily_kg": 0.0,
            "priority_level": 3,
        },
        headers=r_headers,
    )
    assert res_cap.status_code == 422

    # 5. Invalid Priority (> 5)
    res_prio = client.post(
        "/api/v1/receivers/profile",
        json={
            "organization_name": "Super Priority Shelter",
            "contact_phone": "+1-555-1234",
            "address": "123 Way",
            "latitude": 37.7,
            "longitude": -122.4,
            "receiver_category": "SHELTER",
            "capacity_daily_kg": 100.0,
            "priority_level": 10,
        },
        headers=r_headers,
    )
    assert res_prio.status_code == 422
