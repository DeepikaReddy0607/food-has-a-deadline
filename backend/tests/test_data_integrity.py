import uuid
from datetime import datetime, timezone, timedelta
import pytest
from app.models.user import User, SupplierProfile, ReceiverProfile
from app.models.food import SurplusListing, DemandRequest


def register_user(client, name: str, email: str, role: str, password: str = "StrongPassword123!"):
    """Helper to register a user via public API endpoint."""
    return client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": password, "role": role},
    )


def login_user(client, email: str, password: str = "StrongPassword123!"):
    """Helper to authenticate a user and return the Bearer token."""
    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


class TestRegistrationAndPersistence:
    """Verifies that registration persists real PostgreSQL records with Argon2id hashing."""

    def test_registration_creates_real_user_and_hashes_password(self, client, db_session):
        email = f"audit_supplier_{uuid.uuid4().hex[:6]}@example.com"
        password = "AuditedSecretPassword2026!"

        resp = register_user(client, "Audit Supplier Org", email, "SUPPLIER", password)
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == email
        assert data["role"] == "SUPPLIER"
        assert "password" not in data
        assert "password_hash" not in data

        # Query database session directly to verify storage and hashing
        user_in_db = db_session.query(User).filter_by(email=email).first()
        assert user_in_db is not None
        assert user_in_db.email == email
        assert user_in_db.role == "SUPPLIER"
        assert user_in_db.is_active is True

        # Password must be hashed with Argon2id ($argon2id$...)
        assert user_in_db.hashed_password.startswith("$argon2id$")
        # Plain text password must NEVER appear in the hash or anywhere in the record
        assert password not in user_in_db.hashed_password

    def test_registration_rejects_duplicate_email(self, client, db_session):
        email = f"dup_{uuid.uuid4().hex[:6]}@example.com"
        resp1 = register_user(client, "First User", email, "SUPPLIER")
        assert resp1.status_code == 201

        # Second attempt with same email must fail with 400
        resp2 = register_user(client, "Second User", email, "RECEIVER")
        assert resp2.status_code == 400
        assert "already exists" in resp2.json()["detail"].lower()

    def test_supplier_profile_persisted_with_correct_foreign_key(self, client, db_session):
        email = f"supp_prof_{uuid.uuid4().hex[:6]}@example.com"
        register_user(client, "Real Bakery Ltd", email, "SUPPLIER")
        token = login_user(client, email)

        profile_payload = {
            "organization_name": "Real Bakery Organic",
            "contact_phone": "+1-415-555-0199",
            "address": "789 Sourdough Way",
            "state": "California",
            "district": "San Francisco",
            "city": "San Francisco",
            "latitude": 37.7601,
            "longitude": -122.4201,
            "facility_type": "RESTAURANT",
            "operating_hours": {"mon_sun": "06:00-22:00"},
            "storage_capabilities": {"ambient": True, "refrigerated": True},
            "description": "Authentic organic bakery surplus.",
        }

        resp = client.post("/api/v1/suppliers/profile", json=profile_payload, headers=auth_header(token))
        assert resp.status_code == 201
        prof_data = resp.json()
        assert prof_data["organization_name"] == "Real Bakery Organic"

        # Verify database record
        user_in_db = db_session.query(User).filter_by(email=email).first()
        prof_in_db = db_session.query(SupplierProfile).filter_by(user_id=user_in_db.id).first()
        assert prof_in_db is not None
        assert prof_in_db.organization_name == "Real Bakery Organic"
        assert prof_in_db.user_id == user_in_db.id
        assert float(prof_in_db.latitude) == pytest.approx(37.7601, rel=1e-3)

    def test_receiver_profile_persisted_with_correct_foreign_key(self, client, db_session):
        email = f"recv_prof_{uuid.uuid4().hex[:6]}@example.com"
        register_user(client, "Hope Shelter Org", email, "RECEIVER")
        token = login_user(client, email)

        profile_payload = {
            "organization_name": "Hope Community Shelter",
            "contact_phone": "+1-415-555-0244",
            "address": "456 Civic Center Plaza",
            "state": "California",
            "district": "San Francisco",
            "city": "San Francisco",
            "latitude": 37.7795,
            "longitude": -122.4180,
            "receiver_category": "SHELTER",
            "capacity_daily_kg": 250.0,
            "cold_storage_capabilities": {"refrigeration": True, "freezer": True},
            "dietary_handling_capabilities": ["VEGETARIAN", "HALAL"],
            "operating_hours": {"mon_sun": "07:00-21:00"},
            "priority_level": 4,
            "description": "Providing nutritious meals to unhoused community members.",
        }

        resp = client.post("/api/v1/receivers/profile", json=profile_payload, headers=auth_header(token))
        assert resp.status_code == 201
        prof_data = resp.json()
        assert prof_data["organization_name"] == "Hope Community Shelter"

        # Verify database record
        user_in_db = db_session.query(User).filter_by(email=email).first()
        prof_in_db = db_session.query(ReceiverProfile).filter_by(user_id=user_in_db.id).first()
        assert prof_in_db is not None
        assert prof_in_db.organization_name == "Hope Community Shelter"
        assert prof_in_db.capacity_daily_kg == 250.0
        assert prof_in_db.priority_level == 4


class TestMemberDirectories:
    """Verifies that member directories retrieve live PostgreSQL records and separate actor types."""

    def test_suppliers_directory_live_retrieval(self, client, db_session):
        email = f"dir_supp_{uuid.uuid4().hex[:6]}@example.com"
        register_user(client, "Dir Supplier User", email, "SUPPLIER")
        token = login_user(client, email)

        res_p = client.post(
            "/api/v1/suppliers/profile",
            json={
                "organization_name": "Bay Produce Wholesale",
                "contact_phone": "+1-415-555-0301",
                "address": "100 Warehouse Way",
                "city": "Oakland",
                "latitude": 37.8044,
                "longitude": -122.2712,
                "facility_type": "WHOLESALER",
            },
            headers=auth_header(token),
        )
        assert res_p.status_code == 201

        # Retrieve directory
        dir_resp = client.get("/api/v1/suppliers/directory", headers=auth_header(token))
        assert dir_resp.status_code == 200
        directory = dir_resp.json()
        assert isinstance(directory, list)

        matching = [s for s in directory if s["organization_name"] == "Bay Produce Wholesale"]
        assert len(matching) == 1
        assert matching[0]["facility_type"] == "WHOLESALER"
        assert matching[0]["city"] == "Oakland"

    def test_receivers_directory_live_retrieval(self, client, db_session):
        email = f"dir_recv_{uuid.uuid4().hex[:6]}@example.com"
        register_user(client, "Dir Receiver User", email, "RECEIVER")
        token = login_user(client, email)

        res_p = client.post(
            "/api/v1/receivers/profile",
            json={
                "organization_name": "Tenderloin Community Kitchen",
                "contact_phone": "+1-415-555-0302",
                "address": "200 Eddy Street",
                "city": "San Francisco",
                "latitude": 37.7844,
                "longitude": -122.4142,
                "receiver_category": "COMMUNITY_KITCHEN",
                "capacity_daily_kg": 180.0,
                "priority_level": 3,
            },
            headers=auth_header(token),
        )
        assert res_p.status_code == 201

        dir_resp = client.get("/api/v1/receivers/directory", headers=auth_header(token))
        assert dir_resp.status_code == 200
        directory = dir_resp.json()
        assert isinstance(directory, list)

        matching = [r for r in directory if r["organization_name"] == "Tenderloin Community Kitchen"]
        assert len(matching) == 1
        assert matching[0]["receiver_category"] == "COMMUNITY_KITCHEN"
        assert float(matching[0]["capacity_daily_kg"]) == 180.0

    def test_separation_of_suppliers_and_receivers_in_directories(self, client, db_session):
        """Verifies suppliers do not appear in receiver directory and vice versa."""
        supp_email = f"sep_supp_{uuid.uuid4().hex[:6]}@example.com"
        register_user(client, "Unique Farmer", supp_email, "SUPPLIER")
        supp_token = login_user(client, supp_email)
        res_s = client.post(
            "/api/v1/suppliers/profile",
            json={
                "organization_name": "Valley Orchard Produce",
                "contact_phone": "+1-555-0399",
                "address": "100 Orchard Ln",
                "latitude": 37.5,
                "longitude": -122.1,
                "facility_type": "FARM",
            },
            headers=auth_header(supp_token),
        )
        assert res_s.status_code == 201

        recv_email = f"sep_recv_{uuid.uuid4().hex[:6]}@example.com"
        register_user(client, "Unique Foodbank", recv_email, "RECEIVER")
        recv_token = login_user(client, recv_email)
        res_r = client.post(
            "/api/v1/receivers/profile",
            json={
                "organization_name": "Harbor Relief Mission",
                "contact_phone": "+1-555-0388",
                "address": "200 Harbor Dr",
                "latitude": 37.8,
                "longitude": -122.3,
                "receiver_category": "SHELTER",
                "capacity_daily_kg": 300.0,
            },
            headers=auth_header(recv_token),
        )
        assert res_r.status_code == 201

        # Verify Valley Orchard Produce is ONLY in suppliers directory
        supp_dir = client.get("/api/v1/suppliers/directory", headers=auth_header(supp_token)).json()
        recv_dir = client.get("/api/v1/receivers/directory", headers=auth_header(supp_token)).json()

        assert any(s["organization_name"] == "Valley Orchard Produce" for s in supp_dir)
        assert not any(r["organization_name"] == "Valley Orchard Produce" for r in recv_dir)

        # Verify Harbor Relief Mission is ONLY in receivers directory
        assert any(r["organization_name"] == "Harbor Relief Mission" for r in recv_dir)
        assert not any(s["organization_name"] == "Harbor Relief Mission" for s in supp_dir)


class TestTenantIsolation:
    """Verifies that tenants cannot access or manipulate other tenants' listings or demands."""

    def test_supplier_tenant_isolation_on_surplus_listings(self, client, db_session):
        # Register Supplier A
        email_a = f"supp_a_{uuid.uuid4().hex[:6]}@example.com"
        register_user(client, "Supplier A Org", email_a, "SUPPLIER")
        token_a = login_user(client, email_a)
        res_pa = client.post(
            "/api/v1/suppliers/profile",
            json={
                "organization_name": "Supplier A Org",
                "contact_phone": "+1-555-0401",
                "address": "101 A St",
                "latitude": 37.77,
                "longitude": -122.42,
                "facility_type": "RETAILER",
            },
            headers=auth_header(token_a),
        )
        assert res_pa.status_code == 201

        # Supplier A creates a surplus listing
        now = datetime.now(timezone.utc)
        listing_payload = {
            "food_category": "VEGETABLES",
            "item_name": "Fresh Romaine Lettuce",
            "initial_quantity_kg": 50.0,
            "harvest_or_prep_date": (now - timedelta(hours=6)).isoformat(),
            "estimated_deadline": (now + timedelta(hours=36)).isoformat(),
            "storage_condition": "REFRIGERATED",
            "food_condition": "EXCELLENT",
        }
        res_create = client.post("/api/v1/surplus-listings", json=listing_payload, headers=auth_header(token_a))
        assert res_create.status_code == 201
        listing_a_id = res_create.json()["id"]

        # Register Supplier B
        email_b = f"supp_b_{uuid.uuid4().hex[:6]}@example.com"
        register_user(client, "Supplier B Org", email_b, "SUPPLIER")
        token_b = login_user(client, email_b)
        res_pb = client.post(
            "/api/v1/suppliers/profile",
            json={
                "organization_name": "Supplier B Org",
                "contact_phone": "+1-555-0402",
                "address": "202 B St",
                "latitude": 37.78,
                "longitude": -122.43,
                "facility_type": "RETAILER",
            },
            headers=auth_header(token_b),
        )
        assert res_pb.status_code == 201

        # Supplier B attempts to GET Supplier A's listing
        get_res = client.get(f"/api/v1/surplus-listings/{listing_a_id}", headers=auth_header(token_b))
        assert get_res.status_code == 404
        assert "not found" in get_res.json()["detail"].lower()

        # Supplier B attempts to PATCH Supplier A's listing
        patch_res = client.patch(
            f"/api/v1/surplus-listings/{listing_a_id}",
            json={"food_condition": "FAIR"},
            headers=auth_header(token_b),
        )
        assert patch_res.status_code == 404

        # Supplier B attempts to PAUSE Supplier A's listing
        pause_res = client.post(
            f"/api/v1/surplus-listings/{listing_a_id}/pause",
            headers=auth_header(token_b),
        )
        assert pause_res.status_code == 404

        # Supplier B attempts to CANCEL Supplier A's listing
        cancel_res = client.post(
            f"/api/v1/surplus-listings/{listing_a_id}/cancel",
            headers=auth_header(token_b),
        )
        assert cancel_res.status_code == 404

    def test_receiver_tenant_isolation_on_demand_requests(self, client, db_session):
        # Register Receiver A
        email_a = f"recv_a_{uuid.uuid4().hex[:6]}@example.com"
        register_user(client, "Receiver A Org", email_a, "RECEIVER")
        token_a = login_user(client, email_a)
        res_pa = client.post(
            "/api/v1/receivers/profile",
            json={
                "organization_name": "Receiver A Org",
                "contact_phone": "+1-555-0501",
                "address": "301 A St",
                "latitude": 37.77,
                "longitude": -122.42,
                "receiver_category": "SHELTER",
                "capacity_daily_kg": 200.0,
            },
            headers=auth_header(token_a),
        )
        assert res_pa.status_code == 201

        # Receiver A creates a demand request
        now = datetime.now(timezone.utc)
        demand_payload = {
            "food_category": "VEGETABLES",
            "requested_quantity_kg": 40.0,
            "required_by": (now + timedelta(hours=24)).isoformat(),
            "priority_weight": 4,
            "storage_capability": "REFRIGERATED",
        }
        res_create = client.post("/api/v1/demand-requests", json=demand_payload, headers=auth_header(token_a))
        assert res_create.status_code == 201
        demand_a_id = res_create.json()["id"]

        # Register Receiver B
        email_b = f"recv_b_{uuid.uuid4().hex[:6]}@example.com"
        register_user(client, "Receiver B Org", email_b, "RECEIVER")
        token_b = login_user(client, email_b)
        res_pb = client.post(
            "/api/v1/receivers/profile",
            json={
                "organization_name": "Receiver B Org",
                "contact_phone": "+1-555-0502",
                "address": "402 B St",
                "latitude": 37.78,
                "longitude": -122.43,
                "receiver_category": "COMMUNITY_KITCHEN",
                "capacity_daily_kg": 150.0,
            },
            headers=auth_header(token_b),
        )
        assert res_pb.status_code == 201

        # Receiver B attempts to GET Receiver A's demand
        get_res = client.get(f"/api/v1/demand-requests/{demand_a_id}", headers=auth_header(token_b))
        assert get_res.status_code == 404
        assert "not found" in get_res.json()["detail"].lower()

        # Receiver B attempts to PATCH Receiver A's demand
        patch_res = client.patch(
            f"/api/v1/demand-requests/{demand_a_id}",
            json={"requested_quantity_kg": 20.0},
            headers=auth_header(token_b),
        )
        assert patch_res.status_code == 404

        # Receiver B attempts to CANCEL Receiver A's demand
        cancel_res = client.post(
            f"/api/v1/demand-requests/{demand_a_id}/cancel",
            headers=auth_header(token_b),
        )
        assert cancel_res.status_code == 404


class TestEmptyStateHandling:
    """Verifies that empty results return accurate empty collections without synthetic data."""

    def test_surplus_pagination_empty_state_returns_zero_total(self, client, db_session):
        email = f"empty_supp_{uuid.uuid4().hex[:6]}@example.com"
        register_user(client, "Empty Supplier", email, "SUPPLIER")
        token = login_user(client, email)
        res_p = client.post(
            "/api/v1/suppliers/profile",
            json={
                "organization_name": "Empty Supplier Org",
                "contact_phone": "+1-555-0601",
                "address": "500 Empty Way",
                "latitude": 37.77,
                "longitude": -122.42,
                "facility_type": "RETAILER",
            },
            headers=auth_header(token),
        )
        assert res_p.status_code == 201

        # Query listings for this new supplier who has no listings
        resp = client.get("/api/v1/surplus-listings", headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["pages"] == 1

    def test_demand_pagination_empty_state_returns_zero_total(self, client, db_session):
        email = f"empty_recv_{uuid.uuid4().hex[:6]}@example.com"
        register_user(client, "Empty Receiver", email, "RECEIVER")
        token = login_user(client, email)
        res_p = client.post(
            "/api/v1/receivers/profile",
            json={
                "organization_name": "Empty Receiver Org",
                "contact_phone": "+1-555-0602",
                "address": "600 Empty Way",
                "latitude": 37.77,
                "longitude": -122.42,
                "receiver_category": "COMMUNITY_KITCHEN",
                "capacity_daily_kg": 100.0,
            },
            headers=auth_header(token),
        )
        assert res_p.status_code == 201

        # Query demands for this new receiver who has no demands
        resp = client.get("/api/v1/demand-requests", headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["pages"] == 1
