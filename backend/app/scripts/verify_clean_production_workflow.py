"""
Food Has a Deadline (FHD) — Clean Production Workflow Verification Script
Executes the full 14-step production workflow sequence on live PostgreSQL using
isolated verification records to validate end-to-end operational integrity.
"""

import sys
from pathlib import Path

# Add backend root to path
backend_root = Path(__file__).resolve().parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from starlette.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal, check_db_connection
from app.models.user import User
from app.core.security import create_access_token


def run_verification():
    print("=" * 70)
    print(" FOOD HAS A DEADLINE (FHD) — CLEAN PRODUCTION WORKFLOW VERIFICATION ")
    print("=" * 70)

    client = TestClient(app)
    uid = uuid.uuid4().hex[:6]
    now = datetime.now(timezone.utc)

    # -------------------------------------------------------------------------
    # STEP 1 & 2: Database Connection & Healthcheck
    # -------------------------------------------------------------------------
    print("\n[Step 1/14] Verifying PostgreSQL Health...")
    db_check = check_db_connection()
    print(f"  + PostgreSQL Status: {db_check['status']} (Connected: {db_check['connected']})")
    assert db_check["connected"] is True, "PostgreSQL connection failed!"

    print("\n[Step 2/14] Verifying Backend Application Health (/health)...")
    health_resp = client.get("/health")
    assert health_resp.status_code == 200, f"Health check failed: {health_resp.text}"
    health_data = health_resp.json()
    print(f"  + App: {health_data['app_name']} v{health_data['version']}")
    print(f"  + Database Health: {health_data['database']['status']}")
    print(f"  + AI Configured: {health_data['ai_configured']}")

    # -------------------------------------------------------------------------
    # STEP 3 & 4: Register Fresh Test Supplier & Setup Profile
    # -------------------------------------------------------------------------
    print("\n[Step 3/14] Registering Isolated Test Supplier...")
    sup_email = f"prod_verify_sup_{uid}@metrofresh.org"
    sup_reg = client.post(
        "/api/v1/auth/register",
        json={
            "name": f"Production Test Supplier {uid}",
            "email": sup_email,
            "password": "SecurePassword123!",
            "role": "SUPPLIER",
        },
    )
    assert sup_reg.status_code == 201, f"Supplier registration failed: {sup_reg.text}"
    print(f"  + Created Supplier User: {sup_email}")

    sup_login = client.post(
        "/api/v1/auth/login",
        json={"email": sup_email, "password": "SecurePassword123!"},
    )
    assert sup_login.status_code == 200
    sup_token = sup_login.json()["access_token"]
    sup_headers = {"Authorization": f"Bearer {sup_token}"}

    print("\n[Step 4/14] Creating Supplier Facility Profile...")
    sup_prof_resp = client.post(
        "/api/v1/suppliers/profile",
        json={
            "organization_name": f"VERIFY-Metro Fresh Depot {uid}",
            "contact_phone": "+1-415-555-0911",
            "facility_type": "RETAILER",
            "address": "100 California St, San Francisco, CA",
            "latitude": 37.7936,
            "longitude": -122.3990,
            "storage_capabilities": {"ambient": True, "refrigerated": True, "frozen": False},
        },
        headers=sup_headers,
    )
    assert sup_prof_resp.status_code == 201, sup_prof_resp.text
    supplier_profile_id = sup_prof_resp.json()["id"]
    print(f"  + Supplier Profile Created: {supplier_profile_id}")

    # -------------------------------------------------------------------------
    # STEP 5 & 6: Register Fresh Test Receiver & Setup Profile
    # -------------------------------------------------------------------------
    print("\n[Step 5/14] Registering Isolated Test Receiver...")
    rec_email = f"prod_verify_rec_{uid}@communitymeals.org"
    rec_reg = client.post(
        "/api/v1/auth/register",
        json={
            "name": f"Production Test Receiver {uid}",
            "email": rec_email,
            "password": "SecurePassword123!",
            "role": "RECEIVER",
        },
    )
    assert rec_reg.status_code == 201, f"Receiver registration failed: {rec_reg.text}"
    print(f"  + Created Receiver User: {rec_email}")

    rec_login = client.post(
        "/api/v1/auth/login",
        json={"email": rec_email, "password": "SecurePassword123!"},
    )
    assert rec_login.status_code == 200
    rec_token = rec_login.json()["access_token"]
    rec_headers = {"Authorization": f"Bearer {rec_token}"}

    print("\n[Step 6/14] Creating Receiver Facility Profile...")
    rec_prof_resp = client.post(
        "/api/v1/receivers/profile",
        json={
            "organization_name": f"VERIFY-Community Relief Kitchen {uid}",
            "contact_phone": "+1-415-555-0822",
            "receiver_category": "COMMUNITY_KITCHEN",
            "capacity_daily_kg": 200.0,
            "priority_level": 5,
            "address": "500 4th St, San Francisco, CA",
            "latitude": 37.7812,
            "longitude": -122.3995,
            "cold_storage_capabilities": {"ambient": True, "refrigerated": True, "frozen": False},
        },
        headers=rec_headers,
    )
    assert rec_prof_resp.status_code == 201, rec_prof_resp.text
    receiver_profile_id = rec_prof_resp.json()["id"]
    print(f"  + Receiver Profile Created: {receiver_profile_id}")

    # -------------------------------------------------------------------------
    # STEP 7: Create Surplus Inventory Listing (50 kg Dairy, expires in 6h)
    # -------------------------------------------------------------------------
    print("\n[Step 7/14] Registering Perishable Surplus Listing...")
    harvest_dt = (now - timedelta(hours=2)).isoformat()
    deadline_dt = (now + timedelta(hours=6)).isoformat()
    surplus_resp = client.post(
        "/api/v1/surplus-listings",
        json={
            "item_name": f"VERIFY-Organic Milk Batch {uid}",
            "food_category": "DAIRY",
            "initial_quantity_kg": 50.0,
            "storage_condition": "REFRIGERATED",
            "food_condition": "GOOD",
            "harvest_or_prep_date": harvest_dt,
            "estimated_deadline": deadline_dt,
            "pickup_address": "100 California St, Dock 1",
            "handling_instructions": "Maintain cold chain at 4C.",
        },
        headers=sup_headers,
    )
    assert surplus_resp.status_code == 201, surplus_resp.text
    surplus_data = surplus_resp.json()
    surplus_id = surplus_data["id"]
    assert float(surplus_data["remaining_quantity_kg"]) == 50.0
    print(f"  + Created Surplus Listing: {surplus_id} (50 kg, Deadline: +6h)")

    # -------------------------------------------------------------------------
    # STEP 8: Create Demand Request (30 kg Dairy, required in 5h)
    # -------------------------------------------------------------------------
    print("\n[Step 8/14] Registering Receiver Demand Request...")
    req_by_dt = (now + timedelta(hours=5)).isoformat()
    demand_resp = client.post(
        "/api/v1/demand-requests",
        json={
            "food_category": "DAIRY",
            "item_name": f"VERIFY-Fresh Milk Requirement {uid}",
            "requested_quantity_kg": 30.0,
            "storage_capability": "REFRIGERATED",
            "acceptable_food_condition": "FAIR",
            "required_by": req_by_dt,
            "delivery_address": "500 4th St, Receiving Door",
            "priority_weight": 5,
        },
        headers=rec_headers,
    )
    assert demand_resp.status_code == 201, demand_resp.text
    demand_data = demand_resp.json()
    demand_id = demand_data["id"]
    assert float(demand_data["fulfilled_quantity_kg"]) == 0.0
    print(f"  + Created Demand Request: {demand_id} (30 kg, Priority 5)")

    # -------------------------------------------------------------------------
    # STEP 9: Compute Perishability & Route Feasibility Intelligence
    # -------------------------------------------------------------------------
    print("\n[Step 9/14] Evaluating Perishability & Geospatial Routing...")
    intel_resp = client.get(
        f"/api/v1/intelligence/perishability/{surplus_id}",
        headers=sup_headers,
    )
    assert intel_resp.status_code == 200
    intel_data = intel_resp.json()
    print(f"  + Urgency Tier: {intel_data['urgency']} (Remaining Hours: {intel_data['remaining_hours']:.1f}h)")

    route_resp = client.post(
        "/api/v1/geospatial/route-estimate",
        json={
            "surplus_listing_id": surplus_id,
            "receiver_id": receiver_profile_id,
        },
        headers=sup_headers,
    )
    assert route_resp.status_code == 200
    route_data = route_resp.json()
    print(f"  + Road Distance: {route_data['road_distance_km']:.1f} km (Est. Transit: {route_data['estimated_travel_minutes']:.1f} min)")
    print(f"  + Temporal Feasibility: {route_data['feasibility']}")
    assert route_data["feasibility"] == "FEASIBLE"

    # -------------------------------------------------------------------------
    # STEP 10: Multi-Factor Candidate Compatibility Check
    # -------------------------------------------------------------------------
    print("\n[Step 10/14] Checking Multi-Factor Matching Compatibility...")
    match_resp = client.get(
        f"/api/v1/matching/listings/{surplus_id}/candidates",
        headers=sup_headers,
    )
    assert match_resp.status_code == 200
    match_data = match_resp.json()
    candidate = next((c for c in match_data["candidates"] if str(c["demand_request_id"]) == demand_id), None)
    assert candidate is not None
    assert candidate["is_eligible"] is True
    print(f"  + Matching Eligibility: {candidate['eligibility']} (Composite Score: {candidate['score']:.1f} / 100)")

    # -------------------------------------------------------------------------
    # STEP 11: Execute Google OR-Tools Allocation Optimizer
    # -------------------------------------------------------------------------
    print("\n[Step 11/14] Running Google OR-Tools CP-SAT Constrained Optimizer...")
    db = SessionLocal()
    coord_user_id = uuid.uuid4()
    coord_user = User(
        id=coord_user_id,
        email=f"verify_coord_{uid}@fhd.org",
        hashed_password="test_coordinator_pwd",
        role="COORDINATOR",
        is_active=True,
    )
    db.add(coord_user)
    db.commit()
    db.close()

    coord_token = create_access_token(subject=str(coord_user_id), role="COORDINATOR")
    coord_headers = {"Authorization": f"Bearer {coord_token}"}

    opt_resp = client.post(
        "/api/v1/optimization/allocation-proposals",
        json={
            "surplus_listing_ids": [surplus_id],
            "demand_request_ids": [demand_id],
            "timeout_seconds": 5.0,
        },
        headers=coord_headers,
    )
    assert opt_resp.status_code == 200, opt_resp.text
    opt_data = opt_resp.json()
    proposal_id = opt_data["proposal_id"]
    print(f"  + Solver Status: {opt_data['solver_status']} (Solve Time: {opt_data['solve_time_ms']:.1f}ms)")
    print(f"  + Total Allocated: {opt_data['total_allocated_kg']} kg (Proposal ID: {proposal_id})")
    assert opt_data["solver_status"] in ("OPTIMAL", "FEASIBLE")
    assert opt_data["total_allocated_kg"] == 30.0

    # -------------------------------------------------------------------------
    # STEP 12 & 13: Human Coordinator Approval & Atomic Inventory Decrement
    # -------------------------------------------------------------------------
    print("\n[Step 12/14] Coordinator Approves Proposal (Atomic Transaction Execution)...")
    approve_resp = client.post(
        f"/api/v1/optimization/proposals/{proposal_id}/approve",
        json={"dispatch_notes": "Priority dispatch via insulated van."},
        headers=coord_headers,
    )
    assert approve_resp.status_code == 200, approve_resp.text
    tx_data = approve_resp.json()
    transaction_id = tx_data["id"]
    tracking_code = tx_data["tracking_code"]
    print(f"  + Transaction Approved: ID {transaction_id}")
    print(f"  + Tracking Code: {tracking_code} (Status: {tx_data['status']})")

    print("\n[Step 13/14] Verifying Atomic PostgreSQL Inventory Mutations...")
    check_surplus = client.get(f"/api/v1/surplus-listings/{surplus_id}", headers=sup_headers).json()
    check_demand = client.get(f"/api/v1/demand-requests/{demand_id}", headers=rec_headers).json()

    print(f"  + Surplus Initial: 50.0 kg -> Remaining in DB: {check_surplus['remaining_quantity_kg']} kg (Status: {check_surplus['status']})")
    print(f"  + Demand Requested: 30.0 kg -> Fulfilled in DB: {check_demand['fulfilled_quantity_kg']} kg (Status: {check_demand['status']})")
    assert float(check_surplus["remaining_quantity_kg"]) == 20.0
    assert float(check_demand["fulfilled_quantity_kg"]) == 30.0
    assert check_demand["status"] == "FULFILLED"

    # -------------------------------------------------------------------------
    # STEP 14: Step Through Transaction Checkpoints to COMPLETED
    # -------------------------------------------------------------------------
    print("\n[Step 14/14] Stepping Through Physical Checkpoints to COMPLETED...")
    # Dispatch
    client.post(f"/api/v1/transactions/{transaction_id}/execute", headers=coord_headers)
    # Picked up
    client.patch(
        f"/api/v1/transactions/{transaction_id}/status",
        json={"status": "PICKED_UP", "reason": "Van 1 loaded 30 kg milk"},
        headers=coord_headers,
    )
    # In transit
    client.patch(
        f"/api/v1/transactions/{transaction_id}/status",
        json={"status": "IN_TRANSIT", "reason": "En route on California St"},
        headers=coord_headers,
    )
    # Delivered
    client.patch(
        f"/api/v1/transactions/{transaction_id}/status",
        json={"status": "DELIVERED", "reason": "Arrived at kitchen loading bay"},
        headers=coord_headers,
    )
    # Completed
    comp_resp = client.patch(
        f"/api/v1/transactions/{transaction_id}/status",
        json={"status": "COMPLETED", "reason": "Verified temperature and signed acceptance slip"},
        headers=coord_headers,
    )
    assert comp_resp.status_code == 200
    final_tx = comp_resp.json()
    assert final_tx["status"] == "COMPLETED"
    print(f"  + Final Transaction Status: {final_tx['status']}")
    print(f"  + Total Checkpoints in Audit Trail: {len(final_tx['status_history'])}")

    print("\n" + "=" * 70)
    print(" ALL 14 CLEAN PRODUCTION WORKFLOW STEPS VERIFIED 100% SUCCESSFULLY! ")
    print("=" * 70)


if __name__ == "__main__":
    run_verification()
