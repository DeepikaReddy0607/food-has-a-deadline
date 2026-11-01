import io
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from app.models.user import User, SupplierProfile, ReceiverProfile
from app.core.security import create_access_token


def register_user(client, name: str, email: str, role: str) -> tuple[str, dict]:
    reg = client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": "Password123!", "role": role},
    )
    assert reg.status_code == 201, reg.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}


def create_coordinator(db_session, email_prefix: str = "coord") -> tuple[User, str, dict]:
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"{email_prefix}_{uid.hex[:6]}@fhd.org",
        hashed_password="hashed_coordinator_pwd",
        role="COORDINATOR",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token(subject=user.id, role="COORDINATOR")
    return user, token, {"Authorization": f"Bearer {token}"}


class TestOrganizationVerificationSystem:
    def test_01_new_registration_defaults_to_pending_verification(self, client):
        """New supplier and receiver registrations must default to PENDING_VERIFICATION."""
        # Supplier
        _, s_headers = register_user(client, "Fresh Orchard", "fresh@orchard.org", "SUPPLIER")
        s_prof = client.post(
            "/api/v1/suppliers/profile",
            json={
                "organization_name": "Fresh Orchard Inc.",
                "contact_phone": "+1-555-1001",
                "address": "123 Farm Rd",
                "city": "Fresno",
                "state": "California",
                "latitude": 36.7468,
                "longitude": -119.7726,
                "facility_type": "FARM",
            },
            headers=s_headers,
        )
        assert s_prof.status_code == 201
        s_data = s_prof.json()
        assert s_data["verification_status"] == "PENDING_VERIFICATION"
        assert s_data["is_verified"] is False

        # Receiver
        _, r_headers = register_user(client, "Hope Kitchen", "hope@kitchen.org", "RECEIVER")
        r_prof = client.post(
            "/api/v1/receivers/profile",
            json={
                "organization_name": "Hope Community Kitchen",
                "contact_phone": "+1-555-2002",
                "address": "456 Center St",
                "city": "Fresno",
                "state": "California",
                "latitude": 36.7400,
                "longitude": -119.7700,
                "receiver_category": "COMMUNITY_KITCHEN",
                "capacity_daily_kg": 400.0,
                "priority_level": 4,
            },
            headers=r_headers,
        )
        assert r_prof.status_code == 201
        r_data = r_prof.json()
        assert r_data["verification_status"] == "PENDING_VERIFICATION"
        assert r_data["is_verified"] is False

    def test_02_supplier_document_submission_transitions_status(self, client):
        """Supplier document submission updates metadata and transitions status to DOCUMENTS_SUBMITTED."""
        _, s_headers = register_user(client, "Harvest Hub", "harvest@hub.org", "SUPPLIER")
        s_prof = client.post(
            "/api/v1/suppliers/profile",
            json={
                "organization_name": "Harvest Hub LLC",
                "contact_phone": "+1-555-1002",
                "address": "789 Field Rd",
                "city": "Modesto",
                "state": "California",
                "latitude": 37.6391,
                "longitude": -120.9969,
                "facility_type": "FOOD_PROCESSOR",
            },
            headers=s_headers,
        )
        assert s_prof.status_code == 201

        # Check status before submission
        st_before = client.get("/api/v1/verifications/status", headers=s_headers)
        assert st_before.status_code == 200
        assert st_before.json()["verification_status"] == "PENDING_VERIFICATION"

        # Submit verification document
        fake_pdf = io.BytesIO(b"%PDF-1.4 Fake PDF Content for Organization Registration Certificate")
        files = {"document": ("cert.pdf", fake_pdf, "application/pdf")}
        data = {
            "license_number": "AGR-CA-994821",
            "representative_name": "Jane Doe, Director of Logistics",
        }
        sub_res = client.post("/api/v1/verifications/submit", data=data, files=files, headers=s_headers)
        assert sub_res.status_code == 200, sub_res.text
        sub_body = sub_res.json()
        assert sub_body["verification_status"] == "DOCUMENTS_SUBMITTED"
        assert sub_body["license_number"] == "AGR-CA-994821"
        assert sub_body["representative_name"] == "Jane Doe, Director of Logistics"
        assert sub_body["document_name"] == "cert.pdf"
        assert sub_body["submitted_at"] is not None

        # Confirm status endpoint reflects submission
        st_after = client.get("/api/v1/verifications/status", headers=s_headers)
        assert st_after.status_code == 200
        assert st_after.json()["verification_status"] == "DOCUMENTS_SUBMITTED"

    def test_03_receiver_document_submission_transitions_status(self, client):
        """Receiver document submission transitions status to DOCUMENTS_SUBMITTED."""
        _, r_headers = register_user(client, "Nourish Shelter", "nourish@shelter.org", "RECEIVER")
        r_prof = client.post(
            "/api/v1/receivers/profile",
            json={
                "organization_name": "Nourish Shelter",
                "contact_phone": "+1-555-2003",
                "address": "101 Shelter St",
                "city": "Modesto",
                "state": "California",
                "latitude": 37.6400,
                "longitude": -120.9900,
                "receiver_category": "SHELTER",
                "capacity_daily_kg": 250.0,
                "priority_level": 3,
            },
            headers=r_headers,
        )
        assert r_prof.status_code == 201

        fake_png = io.BytesIO(b"\x89PNG\r\n\x1a\nFake PNG Document Content")
        files = {"document": ("501c3_doc.png", fake_png, "image/png")}
        data = {
            "license_number": "501C3-88201",
            "representative_name": "Mark Evans, Program Director",
        }
        sub_res = client.post("/api/v1/verifications/submit", data=data, files=files, headers=r_headers)
        assert sub_res.status_code == 200
        sub_body = sub_res.json()
        assert sub_body["verification_status"] == "DOCUMENTS_SUBMITTED"
        assert sub_body["license_number"] == "501C3-88201"
        assert sub_body["document_name"] == "501c3_doc.png"

    def test_04_unauthorized_users_forbidden_from_approval_or_rejection(self, client):
        """Suppliers and Receivers cannot invoke verification approval or rejection endpoints."""
        _, s_headers = register_user(client, "Supp User", "sup_rbac@org.org", "SUPPLIER")
        _, r_headers = register_user(client, "Recv User", "rec_rbac@org.org", "RECEIVER")

        fake_id = uuid.uuid4()
        # Supplier attempts approval
        res1 = client.post(f"/api/v1/verifications/SUPPLIER/{fake_id}/approve", headers=s_headers)
        assert res1.status_code == 403

        # Receiver attempts rejection
        res2 = client.post(
            f"/api/v1/verifications/RECEIVER/{fake_id}/reject",
            json={"reason": "Suspicious organization"},
            headers=r_headers,
        )
        assert res2.status_code == 403

    def test_05_coordinator_approves_verification(self, client, db_session):
        """Coordinator can inspect pending queue and approve submitted organization."""
        coord_user, _, c_headers = create_coordinator(db_session, "approver")
        _, s_headers = register_user(client, "Green Valley", "gv@farm.org", "SUPPLIER")
        s_prof = client.post(
            "/api/v1/suppliers/profile",
            json={
                "organization_name": "Green Valley Growers",
                "contact_phone": "+1-555-3001",
                "address": "12 Produce Ln",
                "city": "Salinas",
                "state": "California",
                "latitude": 36.6777,
                "longitude": -121.6555,
                "facility_type": "FARM",
            },
            headers=s_headers,
        ).json()
        profile_id = s_prof["id"]

        # Submit document
        fake_pdf = io.BytesIO(b"%PDF-1.4 Tax Exempt & License")
        files = {"document": ("cert.pdf", fake_pdf, "application/pdf")}
        client.post(
            "/api/v1/verifications/submit",
            data={"license_number": "LIC-9988", "representative_name": "Sarah Miller"},
            files=files,
            headers=s_headers,
        )

        # Coordinator views pending list
        queue_res = client.get("/api/v1/verifications?status=DOCUMENTS_SUBMITTED", headers=c_headers)
        assert queue_res.status_code == 200
        items = queue_res.json()
        target = next((item for item in items if str(item["org_id"]) == str(profile_id)), None)
        assert target is not None
        assert target["org_name"] == "Green Valley Growers"
        assert target["license_number"] == "LIC-9988"

        # Coordinator approves
        appr_res = client.post(f"/api/v1/verifications/SUPPLIER/{profile_id}/approve", headers=c_headers)
        assert appr_res.status_code == 200
        appr_data = appr_res.json()
        assert appr_data["verification_status"] == "VERIFIED"
        assert appr_data["verified_at"] is not None

    def test_06_coordinator_rejects_verification_with_mandatory_reason(self, client, db_session):
        """Coordinator can reject verification; rejection reason is required and persisted."""
        _, _, c_headers = create_coordinator(db_session, "rejecter")
        _, r_headers = register_user(client, "Sketchy Pantry", "sketchy@fake.org", "RECEIVER")
        r_prof = client.post(
            "/api/v1/receivers/profile",
            json={
                "organization_name": "Suspicious Pantry",
                "contact_phone": "+1-555-9999",
                "address": "00 Unknown St",
                "city": "Nowhere",
                "state": "California",
                "latitude": 37.0,
                "longitude": -121.0,
                "receiver_category": "FOOD_BANK",
                "capacity_daily_kg": 100.0,
                "priority_level": 1,
            },
            headers=r_headers,
        ).json()
        profile_id = r_prof["id"]

        # Submit invalid document
        fake_pdf = io.BytesIO(b"Not a real document")
        files = {"document": ("doc.pdf", fake_pdf, "application/pdf")}
        client.post(
            "/api/v1/verifications/submit",
            data={"license_number": "00000", "representative_name": "Ghost"},
            files=files,
            headers=r_headers,
        )

        # Attempt rejection without reason -> 422
        bad_rej = client.post(
            f"/api/v1/verifications/RECEIVER/{profile_id}/reject",
            json={"reason": "  "},
            headers=c_headers,
        )
        assert bad_rej.status_code == 422

        # Proper rejection
        rej_res = client.post(
            f"/api/v1/verifications/RECEIVER/{profile_id}/reject",
            json={"reason": "Submitted registration document is unreadable and license number is invalid."},
            headers=c_headers,
        )
        assert rej_res.status_code == 200
        rej_data = rej_res.json()
        assert rej_data["verification_status"] == "REJECTED"
        assert rej_data["rejection_reason"] == "Submitted registration document is unreadable and license number is invalid."

    def test_07_rejected_organization_cannot_publish_surplus_or_demand(self, client, db_session):
        """Organizations with REJECTED status are strictly forbidden from publishing listings or demands (403)."""
        _, _, c_headers = create_coordinator(db_session, "gatekeeper")
        now = datetime.now(timezone.utc)

        # 1. Supplier rejection
        _, s_headers = register_user(client, "Rejected Farm", "farm@reject.org", "SUPPLIER")
        s_prof = client.post(
            "/api/v1/suppliers/profile",
            json={
                "organization_name": "Rejected Farm LLC",
                "contact_phone": "+1-555-4001",
                "address": "90 Bad Way",
                "city": "Salinas",
                "state": "California",
                "latitude": 36.6,
                "longitude": -121.6,
                "facility_type": "FARM",
            },
            headers=s_headers,
        ).json()
        client.post(
            f"/api/v1/verifications/SUPPLIER/{s_prof['id']}/reject",
            json={"reason": "Sanitation permit revoked by county department."},
            headers=c_headers,
        )

        # Attempt surplus listing publication
        res_surplus = client.post(
            "/api/v1/surplus-listings",
            json={
                "food_category": "VEGETABLES",
                "item_name": "Lettuce",
                "initial_quantity_kg": 50.0,
                "harvest_or_prep_date": now.isoformat(),
                "estimated_deadline": (now + timedelta(hours=24)).isoformat(),
                "food_condition": "GOOD",
                "storage_condition": "AMBIENT",
            },
            headers=s_headers,
        )
        assert res_surplus.status_code == 403
        assert "Rejected organizations cannot publish" in res_surplus.json()["detail"]

        # 2. Receiver rejection
        _, r_headers = register_user(client, "Rejected Kitchen", "kitchen@reject.org", "RECEIVER")
        r_prof = client.post(
            "/api/v1/receivers/profile",
            json={
                "organization_name": "Rejected Kitchen Inc.",
                "contact_phone": "+1-555-4002",
                "address": "91 Bad Way",
                "city": "Salinas",
                "state": "California",
                "latitude": 36.61,
                "longitude": -121.61,
                "receiver_category": "COMMUNITY_KITCHEN",
                "capacity_daily_kg": 200.0,
                "priority_level": 2,
            },
            headers=r_headers,
        ).json()
        client.post(
            f"/api/v1/verifications/RECEIVER/{r_prof['id']}/reject",
            json={"reason": "Entity dissolved."},
            headers=c_headers,
        )

        # Attempt demand request publication
        res_demand = client.post(
            "/api/v1/demand-requests",
            json={
                "food_category": "VEGETABLES",
                "item_name": "Lettuce",
                "requested_quantity_kg": 30.0,
                "required_by": (now + timedelta(hours=12)).isoformat(),
                "storage_capability": "AMBIENT",
                "priority_weight": 2,
            },
            headers=r_headers,
        )
        assert res_demand.status_code == 403
        assert "Rejected organizations cannot publish" in res_demand.json()["detail"]

    def test_08_unverified_organization_ineligible_for_matching(self, client):
        """Organizations with PENDING_VERIFICATION or DOCUMENTS_SUBMITTED cannot be matched as eligible candidates."""
        now = datetime.now(timezone.utc)
        # Supplier setup (PENDING_VERIFICATION)
        _, s_headers = register_user(client, "Pending Farm", "pend_farm@test.org", "SUPPLIER")
        client.post(
            "/api/v1/suppliers/profile",
            json={
                "organization_name": "Pending Farm",
                "contact_phone": "+1-555-5001",
                "address": "10 Apple Rd",
                "city": "Napa",
                "state": "California",
                "latitude": 38.3,
                "longitude": -122.3,
                "facility_type": "FARM",
            },
            headers=s_headers,
        )
        l_res = client.post(
            "/api/v1/surplus-listings",
            json={
                "food_category": "FRUITS",
                "item_name": "Apples",
                "initial_quantity_kg": 100.0,
                "harvest_or_prep_date": now.isoformat(),
                "estimated_deadline": (now + timedelta(hours=24)).isoformat(),
                "food_condition": "GOOD",
                "storage_condition": "AMBIENT",
            },
            headers=s_headers,
        )
        listing_id = l_res.json()["id"]

        # Receiver setup (PENDING_VERIFICATION)
        _, r_headers = register_user(client, "Pending Kitchen", "pend_kit@test.org", "RECEIVER")
        client.post(
            "/api/v1/receivers/profile",
            json={
                "organization_name": "Pending Kitchen",
                "contact_phone": "+1-555-5002",
                "address": "12 Apple Rd",
                "city": "Napa",
                "state": "California",
                "latitude": 38.31,
                "longitude": -122.31,
                "receiver_category": "COMMUNITY_KITCHEN",
                "capacity_daily_kg": 300.0,
                "priority_level": 3,
            },
            headers=r_headers,
        )
        d_res = client.post(
            "/api/v1/demand-requests",
            json={
                "food_category": "FRUITS",
                "item_name": "Apples",
                "requested_quantity_kg": 50.0,
                "required_by": (now + timedelta(hours=18)).isoformat(),
                "storage_capability": "AMBIENT",
                "priority_weight": 3,
            },
            headers=r_headers,
        )
        demand_id = d_res.json()["id"]

        # Run candidate matching with transparent reasons included
        cand_res = client.get(
            f"/api/v1/matching/listings/{listing_id}/candidates?include_ineligible=true",
            headers=s_headers,
        )
        assert cand_res.status_code == 200
        cand_data = cand_res.json()
        target = next((c for c in cand_data["candidates"] if str(c["demand_request_id"]) == demand_id), None)
        assert target is not None
        assert target["is_eligible"] is False
        assert target["eligibility"] == "INELIGIBLE"
        assert target["score"] == 0.0
        # Reason must clearly identify lack of verification
        assert any("Supplier organization is not verified" in r for r in target["rejection_reasons"])
        assert any("Receiver organization is not verified" in r for r in target["rejection_reasons"])

    def test_09_verified_organizations_match_and_allocate_normally(self, client, db_session):
        """When coordinator approves both organizations, matching identifies them as ELIGIBLE."""
        _, _, c_headers = create_coordinator(db_session, "matcher")
        now = datetime.now(timezone.utc)

        # Supplier
        _, s_headers = register_user(client, "Verified Farm", "v_farm@test.org", "SUPPLIER")
        s_prof = client.post(
            "/api/v1/suppliers/profile",
            json={
                "organization_name": "Verified Farm Ltd",
                "contact_phone": "+1-555-6001",
                "address": "100 Green Rd",
                "city": "Napa",
                "state": "California",
                "latitude": 38.3000,
                "longitude": -122.2850,
                "facility_type": "FARM",
            },
            headers=s_headers,
        ).json()
        l_res = client.post(
            "/api/v1/surplus-listings",
            json={
                "food_category": "FRUITS",
                "item_name": "Fresh Pears",
                "initial_quantity_kg": 100.0,
                "harvest_or_prep_date": now.isoformat(),
                "estimated_deadline": (now + timedelta(hours=24)).isoformat(),
                "food_condition": "GOOD",
                "storage_condition": "AMBIENT",
            },
            headers=s_headers,
        )
        listing_id = l_res.json()["id"]

        # Receiver
        _, r_headers = register_user(client, "Verified Kitchen", "v_kit@test.org", "RECEIVER")
        r_prof = client.post(
            "/api/v1/receivers/profile",
            json={
                "organization_name": "Verified Kitchen Co",
                "contact_phone": "+1-555-6002",
                "address": "102 Green Rd",
                "city": "Napa",
                "state": "California",
                "latitude": 38.3050,
                "longitude": -122.2800,
                "receiver_category": "COMMUNITY_KITCHEN",
                "capacity_daily_kg": 300.0,
                "priority_level": 4,
            },
            headers=r_headers,
        ).json()
        d_res = client.post(
            "/api/v1/demand-requests",
            json={
                "food_category": "FRUITS",
                "item_name": "Fresh Pears",
                "requested_quantity_kg": 50.0,
                "required_by": (now + timedelta(hours=18)).isoformat(),
                "storage_capability": "AMBIENT",
                "priority_weight": 4,
            },
            headers=r_headers,
        )
        demand_id = d_res.json()["id"]

        # Approve both
        client.post(f"/api/v1/verifications/SUPPLIER/{s_prof['id']}/approve", headers=c_headers)
        client.post(f"/api/v1/verifications/RECEIVER/{r_prof['id']}/approve", headers=c_headers)

        # Match candidates
        cand_res = client.get(
            f"/api/v1/matching/listings/{listing_id}/candidates",
            headers=s_headers,
        )
        assert cand_res.status_code == 200
        cand_data = cand_res.json()
        target = next((c for c in cand_data["candidates"] if str(c["demand_request_id"]) == demand_id), None)
        assert target is not None
        assert target["is_eligible"] is True
        assert target["eligibility"] == "ELIGIBLE"
        assert target["score"] > 50.0

    def test_10_verification_status_in_profiles_and_directory(self, client, db_session):
        """Verification status is accurately reported across directory endpoints and profile responses."""
        _, _, c_headers = create_coordinator(db_session, "auditor")
        _, s_headers = register_user(client, "Directory Farm", "dir_farm@test.org", "SUPPLIER")
        s_prof = client.post(
            "/api/v1/suppliers/profile",
            json={
                "organization_name": "Directory Farm",
                "contact_phone": "+1-555-7001",
                "address": "50 Directory Way",
                "city": "Sacramento",
                "state": "California",
                "latitude": 38.5816,
                "longitude": -121.4944,
                "facility_type": "FARM",
            },
            headers=s_headers,
        ).json()
        profile_id = s_prof["id"]

        # Check directory: defaults to PENDING_VERIFICATION
        dir_res = client.get("/api/v1/suppliers/directory", headers=s_headers)
        assert dir_res.status_code == 200
        sup_entry = next((item for item in dir_res.json() if item["id"] == profile_id), None)
        assert sup_entry is not None
        assert sup_entry["verification_status"] == "PENDING_VERIFICATION"
        assert sup_entry["is_verified"] is False

        # Approve and recheck directory
        client.post(f"/api/v1/verifications/SUPPLIER/{profile_id}/approve", headers=c_headers)
        dir_res_after = client.get("/api/v1/suppliers/directory", headers=s_headers)
        assert dir_res_after.status_code == 200
        sup_entry_after = next((item for item in dir_res_after.json() if item["id"] == profile_id), None)
        assert sup_entry_after is not None
        assert sup_entry_after["verification_status"] == "VERIFIED"
        assert sup_entry_after["is_verified"] is True
