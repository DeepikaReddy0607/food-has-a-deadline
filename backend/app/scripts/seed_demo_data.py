"""
Food Has a Deadline (FHD) — Demonstration Seed Data Script
Generates clean, identifiable demonstration records for hackathon presentation and live evaluations.
All demonstration entities use the 'DEMO-' prefix for clear identification.

Entities Created:
- Users & Profiles:
  1. Supplier: Bakery ("DEMO-Golden Gate Artisan Bakery")
  2. Supplier: Farm Hub ("DEMO-Sonoma Organic Farms Hub")
  3. Supplier: Wholesaler ("DEMO-Bay Area Produce Depot")
  4. Receiver: Kitchen ("DEMO-Mission Community Kitchen", Priority 5, Cold Storage)
  5. Receiver: Shelter ("DEMO-St. Vincent Family Shelter", Priority 4, Cold Storage)
  6. Receiver: Pantry ("DEMO-Downtown Food Pantry", Priority 3, Ambient)
  7. Coordinator: ("coordinator@fhd.org", Role: COORDINATOR)
  8. Administrator: ("admin@fhd.org", Role: ADMIN)

- Surplus Inventory (Active):
  1. DEMO-SR-01: "Artisan Sourdough & Pastries" (BAKERY, AMBIENT, 50 kg, deadline: +4h, CRITICAL)
  2. DEMO-SR-02: "Fresh Organic Whole Milk & Yogurt" (DAIRY, REFRIGERATED, 120 kg, deadline: +8h, HIGH)
  3. DEMO-SR-03: "Hydroponic Mixed Greens & Spinach" (PRODUCE, REFRIGERATED, 80 kg, deadline: +16h, MODERATE)
  4. DEMO-SR-04: "Prepared Roasted Chicken Meal Trays" (PREPARED_MEALS, REFRIGERATED, 45 kg, deadline: +5h, CRITICAL)

- Demand Requests (Open):
  1. DEMO-DM-01: "Fresh Bread & Baked Goods" (BAKERY, AMBIENT, 40 kg, Priority 4, required: +6h)
  2. DEMO-DM-02: "Refrigerated Milk / Dairy" (DAIRY, REFRIGERATED, 100 kg, Priority 5, required: +10h)
  3. DEMO-DM-03: "Fresh Salad Greens" (PRODUCE, REFRIGERATED, 60 kg, Priority 3, required: +18h)
  4. DEMO-DM-04: "Ready-to-eat Prepared Meals" (PREPARED_MEALS, REFRIGERATED, 45 kg, Priority 5, required: +6h)
"""

import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.models.user import User, SupplierProfile, ReceiverProfile
from app.models.food import SurplusListing, DemandRequest
from app.core.security import hash_password


def seed_demo_environment():
    db: Session = SessionLocal()
    print("==================================================================")
    print("    FOOD HAS A DEADLINE (FHD) — SEEDING DEMONSTRATION DATA       ")
    print("==================================================================")

    now = datetime.now(timezone.utc)
    demo_password = hash_password("DemoPass123!")
    coord_password = hash_password("CoordinatorPass123!")
    admin_password = hash_password("AdminPass123!")

    # -------------------------------------------------------------------------
    # 1. COORDINATOR & ADMIN ACCOUNTS
    # -------------------------------------------------------------------------
    print("\n[1/4] Ensuring Coordinator and Admin Users...")
    coordinator = db.query(User).filter(User.email == "coordinator@fhd.org").first()
    if not coordinator:
        coordinator = User(
            id=uuid.uuid4(),
            email="coordinator@fhd.org",
            hashed_password=coord_password,
            role="COORDINATOR",
            is_active=True,
            is_verified=True,
        )
        db.add(coordinator)
        print("  + Created Coordinator: coordinator@fhd.org (Password: CoordinatorPass123!)")
    else:
        print("  - Coordinator already exists: coordinator@fhd.org")

    admin = db.query(User).filter(User.email == "admin@fhd.org").first()
    if not admin:
        admin = User(
            id=uuid.uuid4(),
            email="admin@fhd.org",
            hashed_password=admin_password,
            role="ADMIN",
            is_active=True,
            is_verified=True,
        )
        db.add(admin)
        print("  + Created Administrator: admin@fhd.org (Password: AdminPass123!)")
    else:
        print("  - Administrator already exists: admin@fhd.org")

    db.commit()

    # -------------------------------------------------------------------------
    # 2. SUPPLIERS AND PROFILES
    # -------------------------------------------------------------------------
    print("\n[2/4] Ensuring Demonstration Suppliers...")
    suppliers_data = [
        {
            "email": "demo_bakery@fhd.org",
            "name": "DEMO-Golden Gate Artisan Bakery",
            "facility_type": "RESTAURANT",
            "phone": "+1-415-555-0111",
            "address": "450 Geary St, San Francisco, CA",
            "lat": 37.7869,
            "lon": -122.4103,
            "storage": {"ambient": True, "refrigerated": False, "frozen": False},
        },
        {
            "email": "demo_farm@fhd.org",
            "name": "DEMO-Sonoma Organic Farms Hub",
            "facility_type": "FARM",
            "phone": "+1-415-555-0222",
            "address": "1000 Market St, San Francisco, CA",
            "lat": 37.7801,
            "lon": -122.4118,
            "storage": {"ambient": True, "refrigerated": True, "frozen": False},
        },
        {
            "email": "demo_dist@fhd.org",
            "name": "DEMO-Bay Area Produce Depot",
            "facility_type": "WHOLESALER",
            "phone": "+1-415-555-0333",
            "address": "2000 Folsom St, San Francisco, CA",
            "lat": 37.7645,
            "lon": -122.4155,
            "storage": {"ambient": True, "refrigerated": True, "frozen": True},
        },
    ]

    supplier_profiles: Dict[str, SupplierProfile] = {}
    for s_info in suppliers_data:
        user = db.query(User).filter(User.email == s_info["email"]).first()
        if not user:
            user = User(
                id=uuid.uuid4(),
                email=s_info["email"],
                hashed_password=demo_password,
                role="SUPPLIER",
                is_active=True,
                is_verified=True,
                verification_status="VERIFIED",
            )
            db.add(user)
            db.flush()
        else:
            user.is_verified = True
            user.verification_status = "VERIFIED"

        profile = db.query(SupplierProfile).filter(SupplierProfile.user_id == user.id).first()
        if not profile:
            profile = SupplierProfile(
                id=uuid.uuid4(),
                user_id=user.id,
                organization_name=s_info["name"],
                contact_phone=s_info["phone"],
                latitude=s_info["lat"],
                longitude=s_info["lon"],
                address=s_info["address"],
                state="California",
                district="San Francisco County",
                city="San Francisco",
                facility_type=s_info["facility_type"],
                storage_capabilities=s_info["storage"],
                description=f"Demonstration perishable supplier facility ({s_info['facility_type']}).",
                verification_status="VERIFIED",
            )
            db.add(profile)
            db.flush()
            print(f"  + Created Supplier Profile: {s_info['name']}")
        else:
            profile.verification_status = "VERIFIED"
            print(f"  - Supplier Profile exists: {s_info['name']}")

        supplier_profiles[s_info["email"]] = profile

    db.commit()

    # -------------------------------------------------------------------------
    # 3. RECEIVERS AND PROFILES
    # -------------------------------------------------------------------------
    print("\n[3/4] Ensuring Demonstration Receivers...")
    receivers_data = [
        {
            "email": "demo_kitchen@fhd.org",
            "name": "DEMO-Mission Community Kitchen",
            "category": "COMMUNITY_KITCHEN",
            "priority": 5,
            "capacity": 300.0,
            "phone": "+1-415-555-0444",
            "address": "2500 Mission St, San Francisco, CA",
            "lat": 37.7589,
            "lon": -122.4190,
            "cold_storage": {"ambient": True, "refrigerated": True, "frozen": True},
        },
        {
            "email": "demo_shelter@fhd.org",
            "name": "DEMO-St. Vincent Family Shelter",
            "category": "SHELTER",
            "priority": 4,
            "capacity": 150.0,
            "phone": "+1-415-555-0555",
            "address": "1049 Howard St, San Francisco, CA",
            "lat": 37.7812,
            "lon": -122.4069,
            "cold_storage": {"ambient": True, "refrigerated": True, "frozen": False},
        },
        {
            "email": "demo_pantry@fhd.org",
            "name": "DEMO-Downtown Food Pantry",
            "category": "FOOD_BANK",
            "priority": 3,
            "capacity": 500.0,
            "phone": "+1-415-555-0666",
            "address": "65 9th St, San Francisco, CA",
            "lat": 37.7768,
            "lon": -122.4162,
            "cold_storage": {"ambient": True, "refrigerated": False, "frozen": False},
        },
    ]

    receiver_profiles: Dict[str, ReceiverProfile] = {}
    for r_info in receivers_data:
        user = db.query(User).filter(User.email == r_info["email"]).first()
        if not user:
            user = User(
                id=uuid.uuid4(),
                email=r_info["email"],
                hashed_password=demo_password,
                role="RECEIVER",
                is_active=True,
                is_verified=True,
                verification_status="VERIFIED",
            )
            db.add(user)
            db.flush()
        else:
            user.is_verified = True
            user.verification_status = "VERIFIED"

        profile = db.query(ReceiverProfile).filter(ReceiverProfile.user_id == user.id).first()
        if not profile:
            profile = ReceiverProfile(
                id=uuid.uuid4(),
                user_id=user.id,
                organization_name=r_info["name"],
                contact_phone=r_info["phone"],
                latitude=r_info["lat"],
                longitude=r_info["lon"],
                address=r_info["address"],
                state="California",
                district="San Francisco County",
                city="San Francisco",
                receiver_category=r_info["category"],
                capacity_daily_kg=Decimal(str(r_info["capacity"])),
                priority_level=r_info["priority"],
                cold_storage_capabilities=r_info["cold_storage"],
                description=f"Demonstration food relief receiver ({r_info['category']}).",
                verification_status="VERIFIED",
            )
            db.add(profile)
            db.flush()
            print(f"  + Created Receiver Profile: {r_info['name']}")
        else:
            profile.verification_status = "VERIFIED"
            print(f"  - Receiver Profile exists: {r_info['name']}")

        receiver_profiles[r_info["email"]] = profile

    db.commit()

    # -------------------------------------------------------------------------
    # 4. SURPLUS LISTINGS AND DEMAND REQUESTS
    # -------------------------------------------------------------------------
    print("\n[4/4] Ensuring Demonstration Surplus & Demand Records...")
    surplus_records = [
        {
            "supplier_email": "demo_bakery@fhd.org",
            "item_name": "DEMO-SR-01: Artisan Sourdough & Pastries",
            "category": "BAKERY",
            "qty": 50.0,
            "storage": "AMBIENT",
            "condition": "FAIR",
            "hours_left": 4.0,
            "urgency": "CRITICAL",
            "address": "450 Geary St, Loading Bay A",
        },
        {
            "supplier_email": "demo_farm@fhd.org",
            "item_name": "DEMO-SR-02: Fresh Organic Whole Milk & Yogurt",
            "category": "DAIRY",
            "qty": 120.0,
            "storage": "REFRIGERATED",
            "condition": "GOOD",
            "hours_left": 8.0,
            "urgency": "HIGH",
            "address": "1000 Market St, Dock 2",
        },
        {
            "supplier_email": "demo_dist@fhd.org",
            "item_name": "DEMO-SR-03: Hydroponic Mixed Greens & Spinach",
            "category": "PRODUCE",
            "qty": 80.0,
            "storage": "REFRIGERATED",
            "condition": "EXCELLENT",
            "hours_left": 16.0,
            "urgency": "MODERATE",
            "address": "2000 Folsom St, Cold Bay 3",
        },
        {
            "supplier_email": "demo_bakery@fhd.org",
            "item_name": "DEMO-SR-04: Prepared Roasted Chicken Meal Trays",
            "category": "PREPARED_MEALS",
            "qty": 45.0,
            "storage": "REFRIGERATED",
            "condition": "GOOD",
            "hours_left": 5.0,
            "urgency": "CRITICAL",
            "address": "450 Geary St, Kitchen Dispatch",
        },
    ]

    for item in surplus_records:
        supp_prof = supplier_profiles[item["supplier_email"]]
        existing = (
            db.query(SurplusListing)
            .filter(SurplusListing.item_name == item["item_name"])
            .first()
        )
        if not existing:
            harvest_dt = now - timedelta(hours=2)
            deadline_dt = now + timedelta(hours=item["hours_left"])
            listing = SurplusListing(
                id=uuid.uuid4(),
                supplier_id=supp_prof.id,
                food_category=item["category"],
                item_name=item["item_name"],
                description=f"Fresh rescue consignment for demonstration. Must be routed within {int(item['hours_left'])} hours.",
                initial_quantity_kg=Decimal(str(item["qty"])),
                remaining_quantity_kg=Decimal(str(item["qty"])),
                storage_condition=item["storage"],
                food_condition=item["condition"],
                harvest_or_prep_date=harvest_dt,
                estimated_deadline=deadline_dt,
                pickup_address=item["address"],
                handling_instructions="Maintain clean temperature compliance.",
                urgency_classification=item["urgency"],
                status="ACTIVE",
            )
            db.add(listing)
            print(f"  + Added Active Surplus: {item['item_name']} ({item['qty']} kg, {item['urgency']})")
        else:
            print(f"  - Surplus listing already exists: {item['item_name']}")

    demand_records = [
        {
            "receiver_email": "demo_pantry@fhd.org",
            "item_name": "DEMO-DM-01: Fresh Bread & Baked Goods",
            "category": "BAKERY",
            "qty": 40.0,
            "storage": "AMBIENT",
            "priority": 4,
            "hours_req": 6.0,
            "address": "65 9th St, Delivery Dock",
        },
        {
            "receiver_email": "demo_kitchen@fhd.org",
            "item_name": "DEMO-DM-02: Refrigerated Milk / Dairy",
            "category": "DAIRY",
            "qty": 100.0,
            "storage": "REFRIGERATED",
            "priority": 5,
            "hours_req": 10.0,
            "address": "2500 Mission St, Kitchen Entrance",
        },
        {
            "receiver_email": "demo_shelter@fhd.org",
            "item_name": "DEMO-DM-03: Fresh Salad Greens",
            "category": "PRODUCE",
            "qty": 60.0,
            "storage": "REFRIGERATED",
            "priority": 3,
            "hours_req": 18.0,
            "address": "1049 Howard St, Receiving Bay",
        },
        {
            "receiver_email": "demo_kitchen@fhd.org",
            "item_name": "DEMO-DM-04: Ready-to-eat Prepared Meals",
            "category": "PREPARED_MEALS",
            "qty": 45.0,
            "storage": "REFRIGERATED",
            "priority": 5,
            "hours_req": 6.0,
            "address": "2500 Mission St, Kitchen Entrance",
        },
    ]

    for req in demand_records:
        rec_prof = receiver_profiles[req["receiver_email"]]
        existing = (
            db.query(DemandRequest)
            .filter(DemandRequest.item_name == req["item_name"])
            .first()
        )
        if not existing:
            req_by_dt = now + timedelta(hours=req["hours_req"])
            demand = DemandRequest(
                id=uuid.uuid4(),
                receiver_id=rec_prof.id,
                food_category=req["category"],
                item_name=req["item_name"],
                description=f"Open demand requirement for high-priority redistribution demo.",
                requested_quantity_kg=Decimal(str(req["qty"])),
                fulfilled_quantity_kg=Decimal("0.00"),
                acceptable_food_condition="FAIR",
                dietary_requirements=[],
                storage_capability=req["storage"],
                delivery_address=req["address"],
                required_by=req_by_dt,
                priority_weight=req["priority"],
                status="OPEN",
            )
            db.add(demand)
            print(f"  + Added Open Demand: {req['item_name']} ({req['qty']} kg, Priority {req['priority']})")
        else:
            print(f"  - Demand request already exists: {req['item_name']}")

    db.commit()
    db.close()

    print("\n==================================================================")
    print("      DEMONSTRATION SEEDING COMPLETED SUCCESSFULLY!             ")
    print("==================================================================")
    print("\nPre-configured Demonstration Credentials:")
    print("  * Coordinator:  coordinator@fhd.org  /  CoordinatorPass123!")
    print("  * Admin:        admin@fhd.org        /  AdminPass123!")
    print("  * Supplier 1:   demo_bakery@fhd.org  /  DemoPass123!")
    print("  * Supplier 2:   demo_farm@fhd.org    /  DemoPass123!")
    print("  * Supplier 3:   demo_dist@fhd.org    /  DemoPass123!")
    print("  * Receiver 1:   demo_kitchen@fhd.org /  DemoPass123!")
    print("  * Receiver 2:   demo_shelter@fhd.org /  DemoPass123!")
    print("  * Receiver 3:   demo_pantry@fhd.org  /  DemoPass123!")
    print("==================================================================")


if __name__ == "__main__":
    seed_demo_environment()
