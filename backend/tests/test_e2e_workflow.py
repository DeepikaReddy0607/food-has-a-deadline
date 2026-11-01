import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.database.session import check_db_connection, SessionLocal
from app.models.user import User


db_status = check_db_connection()
is_postgres_available = db_status.get("connected", False)

pytestmark = pytest.mark.skipif(
    not is_postgres_available,
    reason="Live PostgreSQL database not available on localhost:5432",
)


@pytest.fixture
def api_client():
    return TestClient(app)


def test_complete_end_to_end_fhd_journey(api_client):
    """
    Executes the entire 8-step Food Has a Deadline journey via HTTP REST endpoints
    on live PostgreSQL records:
    1. Supplier registration & surplus listing creation
    2. Receiver registration & demand request creation
    3. Perishability urgency & geospatial feasibility intelligence
    4. Multi-factor candidate matching and eligibility breakdown
    5. Google OR-Tools constrained allocation proposal generation
    6. AI Agent multi-turn coordination & deterministic fallback
    7. Human coordinator proposal review & atomic approval
    8. Complete transaction tracking milestones through COMPLETED
    """
    uid = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)

    # -------------------------------------------------------------------------
    # STEP 1: SUPPLIER WORKFLOW
    # -------------------------------------------------------------------------
    supplier_email = f"e2e_supplier_{uid}@metrofresh.org"
    sup_reg = api_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Metro Fresh Dispatch Manager",
            "email": supplier_email,
            "password": "SecurePassword123!",
            "role": "SUPPLIER",
        },
    )
    assert sup_reg.status_code == 201, sup_reg.text
    supplier_user_id = sup_reg.json()["user_id"]

    # Login Supplier
    sup_login = api_client.post(
        "/api/v1/auth/login",
        json={"email": supplier_email, "password": "SecurePassword123!"},
    )
    assert sup_login.status_code == 200
    sup_token = sup_login.json()["access_token"]
    sup_headers = {"Authorization": f"Bearer {sup_token}"}

    # Setup Supplier Profile
    sup_prof = api_client.post(
        "/api/v1/suppliers/profile",
        json={
            "organization_name": f"Metro Fresh Distribution Hub {uid}",
            "contact_phone": "+1-415-555-0199",
            "facility_type": "RETAILER",
            "address": "742 Evergreen Terrace, San Francisco, CA",
            "latitude": 37.774929,
            "longitude": -122.419416,
            "description": "High-volume organic perishable distributor.",
        },
        headers=sup_headers,
    )
    assert sup_prof.status_code == 201, sup_prof.text
    supplier_profile_id = sup_prof.json()["id"]

    # Add Surplus Food (80 kg of dairy expiring in 6 hours)
    harvest_date = (now - timedelta(hours=2)).isoformat()
    deadline_date = (now + timedelta(hours=6)).isoformat()
    surplus_resp = api_client.post(
        "/api/v1/surplus-listings",
        json={
            "item_name": "Organic Whole Milk & Yogurt",
            "food_category": "DAIRY",
            "initial_quantity_kg": 80.0,
            "storage_condition": "REFRIGERATED",
            "food_condition": "GOOD",
            "harvest_or_prep_date": harvest_date,
            "estimated_deadline": deadline_date,
            "pickup_address": "742 Evergreen Terrace, Dock B",
            "handling_instructions": "Keep below 4 degrees C at all times.",
        },
        headers=sup_headers,
    )
    assert surplus_resp.status_code == 201, surplus_resp.text
    surplus_id = surplus_resp.json()["id"]
    assert float(surplus_resp.json()["remaining_quantity_kg"]) == 80.0
    assert surplus_resp.json()["status"] == "ACTIVE"

    # View Calculated Urgency Intelligence
    intel_resp = api_client.get(
        f"/api/v1/intelligence/perishability/{surplus_id}",
        headers=sup_headers,
    )
    assert intel_resp.status_code == 200
    intel_data = intel_resp.json()
    assert intel_data["urgency"] in ("CRITICAL", "HIGH", "MODERATE")
    assert intel_data["remaining_hours"] <= 6.5
    assert "explanation" in intel_data

    # -------------------------------------------------------------------------
    # STEP 2: RECEIVER WORKFLOW
    # -------------------------------------------------------------------------
    receiver_email = f"e2e_receiver_{uid}@hopekitchen.org"
    rec_reg = api_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Hope Kitchen Director",
            "email": receiver_email,
            "password": "SecurePassword123!",
            "role": "RECEIVER",
        },
    )
    assert rec_reg.status_code == 201, rec_reg.text
    receiver_user_id = rec_reg.json()["user_id"]

    rec_login = api_client.post(
        "/api/v1/auth/login",
        json={"email": receiver_email, "password": "SecurePassword123!"},
    )
    assert rec_login.status_code == 200
    rec_token = rec_login.json()["access_token"]
    rec_headers = {"Authorization": f"Bearer {rec_token}"}

    # Setup Receiver Profile with confirmed cold storage
    rec_prof = api_client.post(
        "/api/v1/receivers/profile",
        json={
            "organization_name": f"Hope Community Kitchen {uid}",
            "contact_phone": "+1-415-555-0288",
            "receiver_category": "COMMUNITY_KITCHEN",
            "capacity_daily_kg": 250.0,
            "address": "1200 Mission St, San Francisco, CA",
            "latitude": 37.778519,
            "longitude": -122.411758,
            "cold_storage_capabilities": {"refrigeration": True, "freezer": True},
            "priority_level": 4,
            "description": "Daily meal shelter providing hot meals.",
        },
        headers=rec_headers,
    )
    assert rec_prof.status_code == 201
    receiver_profile_id = rec_prof.json()["id"]

    # Submit Actual Demand (60 kg Dairy needed by 5 hours)
    required_by_date = (now + timedelta(hours=5)).isoformat()
    demand_resp = api_client.post(
        "/api/v1/demand-requests",
        json={
            "food_category": "DAIRY",
            "item_name": "Refrigerated Milk/Dairy",
            "requested_quantity_kg": 60.0,
            "storage_capability": "REFRIGERATED",
            "acceptable_food_condition": "FAIR",
            "required_by": required_by_date,
            "delivery_address": "1200 Mission St, Back Gate",
            "priority_weight": 4,
        },
        headers=rec_headers,
    )
    assert demand_resp.status_code == 201
    demand_id = demand_resp.json()["id"]
    assert float(demand_resp.json()["fulfilled_quantity_kg"]) == 0.0
    assert demand_resp.json()["status"] in ("OPEN", "ACTIVE")

    # -------------------------------------------------------------------------
    # STEP 2b: COORDINATOR VERIFICATION WORKFLOW
    # -------------------------------------------------------------------------
    coord_email = f"e2e_coord_{uid}@fhd.org"
    coord_user_id = uuid.uuid4()
    # Seed coordinator user directly in database
    db = SessionLocal()
    coord_user = User(
        id=coord_user_id,
        email=coord_email,
        hashed_password="hashed_coordinator_pwd",
        role="COORDINATOR",
        is_active=True,
    )
    db.add(coord_user)
    db.commit()
    db.close()

    from app.core.security import create_access_token
    coord_token = create_access_token(subject=str(coord_user_id), role="COORDINATOR")
    coord_headers = {"Authorization": f"Bearer {coord_token}"}

    # Approve supplier
    sup_appr = api_client.post(
        f"/api/v1/verifications/SUPPLIER/{supplier_profile_id}/approve",
        headers=coord_headers,
    )
    assert sup_appr.status_code == 200
    assert sup_appr.json()["verification_status"] == "VERIFIED"

    # Approve receiver
    rec_appr = api_client.post(
        f"/api/v1/verifications/RECEIVER/{receiver_profile_id}/approve",
        headers=coord_headers,
    )
    assert rec_appr.status_code == 200
    assert rec_appr.json()["verification_status"] == "VERIFIED"

    # -------------------------------------------------------------------------
    # STEP 3: GEOSPATIAL INTELLIGENCE & ROUTING
    # -------------------------------------------------------------------------
    route_resp = api_client.post(
        "/api/v1/geospatial/route-estimate",
        json={
            "surplus_listing_id": surplus_id,
            "receiver_id": receiver_profile_id,
        },
        headers=sup_headers,
    )
    assert route_resp.status_code == 200
    route_data = route_resp.json()
    assert route_data["road_distance_km"] > 0
    assert route_data["estimated_travel_minutes"] > 0
    assert route_data["feasibility"] == "FEASIBLE"

    # -------------------------------------------------------------------------
    # STEP 4: MULTI-FACTOR MATCHING ENGINE
    # -------------------------------------------------------------------------
    match_resp = api_client.get(
        f"/api/v1/matching/listings/{surplus_id}/candidates",
        headers=sup_headers,
    )
    assert match_resp.status_code == 200
    match_data = match_resp.json()
    assert match_data["total_candidates"] >= 1
    # Receiver must be found eligible
    eligible_match = next((c for c in match_data["candidates"] if str(c["demand_request_id"]) == demand_id), None)
    assert eligible_match is not None
    assert eligible_match["is_eligible"] is True
    assert eligible_match["score"] > 50.0

    # -------------------------------------------------------------------------
    # STEP 5 & 6: COORDINATOR OPTIMIZATION & AI AGENT
    # -------------------------------------------------------------------------
    # Run Google OR-Tools Allocation Optimizer
    opt_resp = api_client.post(
        "/api/v1/optimization/allocation-proposals",
        json={
            "surplus_listing_ids": [surplus_id],
            "demand_request_ids": [demand_id],
            "timeout_seconds": 5.0,
        },
        headers=coord_headers,
    )
    assert opt_resp.status_code == 200
    opt_data = opt_resp.json()
    assert opt_data["solver_status"] in ("OPTIMAL", "FEASIBLE")
    assert opt_data["proposal_id"] is not None
    assert opt_data["status"] == "PENDING_REVIEW"
    proposal_id = opt_data["proposal_id"]

    # Verify proposed flow connects our surplus to our demand
    allocated_item = next((i for i in opt_data["items"] if str(i["surplus_listing_id"]) == surplus_id), None)
    assert allocated_item is not None
    assert float(allocated_item["allocated_quantity_kg"]) == 60.0  # Exactly satisfies the 60 kg demand!

    # Test AI Agent Copilot
    chat_resp = api_client.post(
        "/api/v1/agent/chat",
        json={"message": "What is the most urgent surplus food currently registered and what receiver can take it?"},
        headers=coord_headers,
    )
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert chat_data["conversation_id"] is not None
    assert len(chat_data["response_text"]) > 10
    # Must run safely in either live Gemini or deterministic fallback mode
    assert "Gemini" in chat_data["ai_provider"] or "Fallback" in chat_data["ai_provider"]

    # -------------------------------------------------------------------------
    # STEP 7: HUMAN APPROVAL & ATOMIC TRANSACTION CREATION
    # -------------------------------------------------------------------------
    approve_resp = api_client.post(
        f"/api/v1/optimization/proposals/{proposal_id}/approve",
        json={"dispatch_notes": "Priority rescue: dispatch insulated van 4."},
        headers=coord_headers,
    )
    assert approve_resp.status_code == 200, approve_resp.text
    tx_data = approve_resp.json()
    assert tx_data["status"] == "APPROVED"
    assert tx_data["tracking_code"].startswith("FHD-TX-")
    transaction_id = tx_data["id"]

    # Verify atomic inventory updates in PostgreSQL
    surplus_check = api_client.get(f"/api/v1/surplus-listings/{surplus_id}", headers=sup_headers)
    assert surplus_check.status_code == 200
    # Initial was 80 kg; allocated 60 kg -> remaining must be exactly 20 kg!
    assert float(surplus_check.json()["remaining_quantity_kg"]) == 20.0
    assert surplus_check.json()["status"] == "ACTIVE"

    demand_check = api_client.get(f"/api/v1/demand-requests/{demand_id}", headers=rec_headers)
    assert demand_check.status_code == 200
    # Requested 60 kg; fulfilled 60 kg -> status must be FULFILLED!
    assert float(demand_check.json()["fulfilled_quantity_kg"]) == 60.0
    assert demand_check.json()["status"] == "FULFILLED"

    # -------------------------------------------------------------------------
    # STEP 8: TRANSACTION TRACKING LIFECYCLE
    # -------------------------------------------------------------------------
    # 1. Schedule Dispatch
    exec_resp = api_client.post(f"/api/v1/transactions/{transaction_id}/execute", headers=coord_headers)
    assert exec_resp.status_code == 200
    assert exec_resp.json()["status"] == "PICKUP_SCHEDULED"

    # 2. Driver Picked Up
    pickup_resp = api_client.patch(
        f"/api/v1/transactions/{transaction_id}/status",
        json={"status": "PICKED_UP", "reason": "Van 4 arrived, loaded 60 kg dairy"},
        headers=coord_headers,
    )
    assert pickup_resp.status_code == 200
    assert pickup_resp.json()["status"] == "PICKED_UP"

    # 3. In Transit
    transit_resp = api_client.patch(
        f"/api/v1/transactions/{transaction_id}/status",
        json={"status": "IN_TRANSIT", "reason": "Departed supplier dock en route to receiver"},
        headers=coord_headers,
    )
    assert transit_resp.status_code == 200
    assert transit_resp.json()["status"] == "IN_TRANSIT"

    # 4. Delivered
    deliv_resp = api_client.patch(
        f"/api/v1/transactions/{transaction_id}/status",
        json={"status": "DELIVERED", "reason": "Arrived at Hope Community Kitchen, unloaded at cold room"},
        headers=coord_headers,
    )
    assert deliv_resp.status_code == 200
    assert deliv_resp.json()["status"] == "DELIVERED"

    # 5. Completed
    comp_resp = api_client.patch(
        f"/api/v1/transactions/{transaction_id}/status",
        json={"status": "COMPLETED", "reason": "Receiver signed delivery slip, temperature verified"},
        headers=coord_headers,
    )
    assert comp_resp.status_code == 200
    assert comp_resp.json()["status"] == "COMPLETED"

    # Final Verification: Query Transaction Details & Complete Audit Trail
    tx_final = api_client.get(f"/api/v1/transactions/{transaction_id}", headers=coord_headers)
    assert tx_final.status_code == 200
    final_data = tx_final.json()
    assert final_data["status"] == "COMPLETED"
    assert len(final_data["items"]) == 1
    assert final_data["items"][0]["item_name"] == "Organic Whole Milk & Yogurt"
    assert float(final_data["items"][0]["allocated_quantity_kg"]) == 60.0
    # Audit trail must show at least 6 chronological checkpoints
    assert len(final_data["status_history"]) >= 6
    history_statuses = [h["new_status"] for h in final_data["status_history"]]
    assert history_statuses == ["APPROVED", "PICKUP_SCHEDULED", "PICKED_UP", "IN_TRANSIT", "DELIVERED", "COMPLETED"]
