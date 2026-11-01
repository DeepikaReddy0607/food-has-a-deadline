import uuid
from datetime import datetime, timezone, timedelta
import pytest

from app.intelligence.urgency_classifier import (
    UrgencyClassifier,
    CRITICAL_THRESHOLD_SECONDS,
    HIGH_THRESHOLD_SECONDS,
    MODERATE_THRESHOLD_SECONDS,
)
from app.intelligence.condition_assessor import ConditionAssessor
from app.intelligence.storage_assessor import StorageAssessor
from app.intelligence.perishability_engine import PerishabilityEngine
from app.intelligence.reference_data import FOOD_SAFETY_DISCLAIMER


# =========================================================================
# 1. DETERMINISTIC URGENCY CLASSIFIER BOUNDARY TESTS
# =========================================================================

def test_urgency_classifier_boundaries():
    """Verify exact mathematical boundary conditions for urgency classification."""
    # Negative time (past deadline) -> CRITICAL
    assert UrgencyClassifier.classify(-3600.0) == "CRITICAL"

    # Exactly 0 seconds -> CRITICAL
    assert UrgencyClassifier.classify(0.0) == "CRITICAL"

    # 1 hour (3,600s) -> CRITICAL
    assert UrgencyClassifier.classify(3600.0) == "CRITICAL"

    # 5 hours 59 minutes (21,540s) -> CRITICAL
    assert UrgencyClassifier.classify(21540.0) == "CRITICAL"

    # 1 second before 6 hours (21,599s) -> CRITICAL
    assert UrgencyClassifier.classify(21599.0) == "CRITICAL"

    # Exactly 6 hours (21,600s) -> HIGH
    assert UrgencyClassifier.classify(21600.0) == "HIGH"
    assert UrgencyClassifier.classify(float(CRITICAL_THRESHOLD_SECONDS)) == "HIGH"

    # 12 hours (43,200s) -> HIGH
    assert UrgencyClassifier.classify(43200.0) == "HIGH"

    # 23 hours 59 minutes (86,340s) -> HIGH
    assert UrgencyClassifier.classify(86340.0) == "HIGH"

    # 1 second before 24 hours (86,399s) -> HIGH
    assert UrgencyClassifier.classify(86399.0) == "HIGH"

    # Exactly 24 hours (86,400s) -> MODERATE
    assert UrgencyClassifier.classify(86400.0) == "MODERATE"
    assert UrgencyClassifier.classify(float(HIGH_THRESHOLD_SECONDS)) == "MODERATE"

    # 48 hours (172,800s) -> MODERATE
    assert UrgencyClassifier.classify(172800.0) == "MODERATE"

    # 71 hours 59 minutes (259,140s) -> MODERATE
    assert UrgencyClassifier.classify(259140.0) == "MODERATE"

    # 1 second before 72 hours (259,199s) -> MODERATE
    assert UrgencyClassifier.classify(259199.0) == "MODERATE"

    # Exactly 72 hours (259,200s) -> LOW
    assert UrgencyClassifier.classify(259200.0) == "LOW"
    assert UrgencyClassifier.classify(float(MODERATE_THRESHOLD_SECONDS)) == "LOW"

    # Multiple days: 5 days (432,000s) -> LOW
    assert UrgencyClassifier.classify(432000.0) == "LOW"

    # None or NaN -> PENDING
    assert UrgencyClassifier.classify(None) == "PENDING"
    assert UrgencyClassifier.classify(float("nan")) == "PENDING"


def test_urgency_explanation_content():
    """Verify human-readable justifications for all tiers."""
    # Critical past
    exp_past = UrgencyClassifier.explain("CRITICAL", -1800.0)
    assert "cut-off passed" in exp_past.lower()

    # Critical active
    exp_crit = UrgencyClassifier.explain("CRITICAL", 7200.0)
    assert "2.0 hours remaining" in exp_crit
    assert "same-day" in exp_crit

    # High
    exp_high = UrgencyClassifier.explain("HIGH", 43200.0)
    assert "upcoming redistribution cycle" in exp_high

    # Moderate
    exp_mod = UrgencyClassifier.explain("MODERATE", 172800.0)
    assert "standard scheduled allocation" in exp_mod

    # Low
    exp_low = UrgencyClassifier.explain("LOW", 345600.0)
    assert "stable" in exp_low

    # Pending
    exp_pend = UrgencyClassifier.explain("PENDING", None)
    assert "pending" in exp_pend.lower()


# =========================================================================
# 2. FOOD CONDITION ASSESSOR TESTS
# =========================================================================

def test_condition_assessor_all_states():
    """Test all supported food conditions and warning generation."""
    # 1. IMMINENT_DECAY generates high priority alert and flag
    res_decay = ConditionAssessor.assess("IMMINENT_DECAY")
    assert res_decay["is_valid"] is True
    assert res_decay["requires_immediate_action"] is True
    assert any("HIGH PRIORITY" in w for w in res_decay["warnings"])
    assert any("IMMINENT DECAY" in w for w in res_decay["warnings"])

    # 2. RIPE generates handling warning
    res_ripe = ConditionAssessor.assess("RIPE")
    assert res_ripe["is_valid"] is True
    assert any("HANDLING WARNING" in w for w in res_ripe["warnings"])
    assert any("RIPE" in w for w in res_ripe["warnings"])

    # 3. IMPERFECT does not mean unsafe
    res_imperf = ConditionAssessor.assess("IMPERFECT")
    assert res_imperf["is_valid"] is True
    assert len(res_imperf["warnings"]) == 0
    assert "cosmetic" in res_imperf["notes"].lower()
    assert "safe" in res_imperf["notes"].lower()

    # 4. FAIR advisory
    res_fair = ConditionAssessor.assess("FAIR")
    assert res_fair["is_valid"] is True
    assert any("FAIR" in w for w in res_fair["warnings"])

    # 5. GOOD and EXCELLENT (no warnings)
    assert len(ConditionAssessor.assess("GOOD")["warnings"]) == 0
    assert len(ConditionAssessor.assess("EXCELLENT")["warnings"]) == 0

    # 6. Unrecognized and missing conditions
    res_missing = ConditionAssessor.assess(None)
    assert res_missing["is_valid"] is False
    assert any("unspecified" in w.lower() for w in res_missing["warnings"])

    res_unknown = ConditionAssessor.assess("MOLDY_UNKNOWN")
    assert res_unknown["is_valid"] is False
    assert any("unrecognized" in w.lower() for w in res_unknown["warnings"])


# =========================================================================
# 3. STORAGE CONDITION ASSESSOR TESTS
# =========================================================================

def test_storage_assessor_all_states():
    """Test all storage conditions and cold chain compliance alerts."""
    # 1. REFRIGERATED requires cold chain and disclaims label proof
    res_refrig = StorageAssessor.assess("REFRIGERATED")
    assert res_refrig["is_valid"] is True
    assert res_refrig["requires_cold_chain"] is True
    assert any("COLD CHAIN REQUIRED" in w for w in res_refrig["warnings"])
    assert any("label alone does not verify" in w for w in res_refrig["warnings"])

    # 2. FROZEN requires freezer chain and no-refreeze warning
    res_frozen = StorageAssessor.assess("FROZEN")
    assert res_frozen["is_valid"] is True
    assert res_frozen["requires_cold_chain"] is True
    assert any("FREEZER CHAIN REQUIRED" in w for w in res_frozen["warnings"])
    assert any("Do not refreeze" in w for w in res_frozen["warnings"])

    # 3. AMBIENT
    res_ambient = StorageAssessor.assess("AMBIENT")
    assert res_ambient["is_valid"] is True
    assert res_ambient["requires_cold_chain"] is False
    assert len(res_ambient["warnings"]) == 0

    # 4. Missing or unknown storage
    res_none = StorageAssessor.assess(None)
    assert res_none["is_valid"] is False
    assert any("DATA QUALITY WARNING" in w for w in res_none["warnings"])


# =========================================================================
# 4. PERISHABILITY ENGINE COORDINATOR & DATA QUALITY TESTS
# =========================================================================

def test_engine_controllable_clock_and_data_quality():
    """Verify engine evaluates correctly against injected evaluation timestamps."""
    fixed_eval_time = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)

    # 1. 5 hours remaining -> CRITICAL
    deadline_crit = fixed_eval_time + timedelta(hours=5)
    ev_crit = PerishabilityEngine.evaluate(
        estimated_deadline=deadline_crit,
        harvest_or_prep_date=fixed_eval_time - timedelta(hours=12),
        food_condition="GOOD",
        storage_condition="REFRIGERATED",
        evaluation_time=fixed_eval_time,
    )
    assert ev_crit.urgency == "CRITICAL"
    assert ev_crit.remaining_hours == 5.0
    assert ev_crit.data_quality == "COMPLETE"
    assert ev_crit.disclaimer == FOOD_SAFETY_DISCLAIMER

    # 2. Exactly 6 hours remaining -> HIGH
    deadline_high = fixed_eval_time + timedelta(hours=6)
    ev_high = PerishabilityEngine.evaluate(
        estimated_deadline=deadline_high,
        harvest_or_prep_date=fixed_eval_time - timedelta(hours=6),
        food_condition="EXCELLENT",
        storage_condition="AMBIENT",
        evaluation_time=fixed_eval_time,
    )
    assert ev_high.urgency == "HIGH"
    assert ev_high.remaining_hours == 6.0

    # 3. Missing deadline -> PENDING, INVALID
    ev_missing = PerishabilityEngine.evaluate(
        estimated_deadline=None,
        evaluation_time=fixed_eval_time,
    )
    assert ev_missing.urgency == "PENDING"
    assert ev_missing.data_quality == "INVALID"

    # 4. Inconsistent dates (deadline <= harvest_prep_date) -> SUSPECT
    ev_suspect = PerishabilityEngine.evaluate(
        estimated_deadline=fixed_eval_time + timedelta(hours=10),
        harvest_or_prep_date=fixed_eval_time + timedelta(hours=12),
        food_condition="GOOD",
        storage_condition="AMBIENT",
        evaluation_time=fixed_eval_time,
    )
    assert ev_suspect.data_quality == "SUSPECT"
    assert any("INCONSISTENCY" in w for w in ev_suspect.warnings)


# =========================================================================
# 5. SERVICE & API INTEGRATION TESTS
# =========================================================================

def register_and_login(client, name: str, email: str, role: str) -> str:
    client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": "StrongPassword123!", "role": role},
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPassword123!"},
    )
    return res.json()["access_token"]


def create_supplier_profile(client, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    profile_payload = {
        "organization_name": "Sunrise Bakery",
        "contact_phone": "+1-555-7788",
        "address": "789 Flour Mill Rd",
        "state": "California",
        "district": "Oakland",
        "city": "Oakland",
        "latitude": 37.8044,
        "longitude": -122.2712,
        "facility_type": "FOOD_PROCESSOR",
        "storage_capabilities": {"ambient": True, "refrigerated": True},
    }
    client.post("/api/v1/suppliers/profile", json=profile_payload, headers=headers)


def test_listing_creation_automatically_calculates_urgency(client):
    """Creating a listing evaluates and persists urgency classification immediately."""
    token = register_and_login(client, "Bakery Owner", "baker@test.com", "SUPPLIER")
    create_supplier_profile(client, token)
    headers = {"Authorization": f"Bearer {token}"}
    now = datetime.now(timezone.utc)

    # 1. 4-hour batch -> CRITICAL
    crit_payload = {
        "food_category": "BAKERY",
        "item_name": "Fresh Warm Croissants",
        "initial_quantity_kg": 15.0,
        "harvest_or_prep_date": (now - timedelta(hours=2)).isoformat(),
        "estimated_deadline": (now + timedelta(hours=4)).isoformat(),
        "food_condition": "GOOD",
        "storage_condition": "AMBIENT",
    }
    res_crit = client.post("/api/v1/surplus-listings", json=crit_payload, headers=headers)
    assert res_crit.status_code == 201
    assert res_crit.json()["urgency_classification"] == "CRITICAL"

    # 2. 18-hour batch -> HIGH
    high_payload = {
        "food_category": "DAIRY",
        "item_name": "Fresh Milk Gallons",
        "initial_quantity_kg": 40.0,
        "harvest_or_prep_date": (now - timedelta(hours=4)).isoformat(),
        "estimated_deadline": (now + timedelta(hours=18)).isoformat(),
        "food_condition": "GOOD",
        "storage_condition": "REFRIGERATED",
    }
    res_high = client.post("/api/v1/surplus-listings", json=high_payload, headers=headers)
    assert res_high.status_code == 201
    assert res_high.json()["urgency_classification"] == "HIGH"


def test_listing_deadline_update_recalculates_urgency(client):
    """Updating usable deadline recalculates and updates stored urgency classification."""
    token = register_and_login(client, "Dairy Co", "dairy@test.com", "SUPPLIER")
    create_supplier_profile(client, token)
    headers = {"Authorization": f"Bearer {token}"}
    now = datetime.now(timezone.utc)

    # Initial: 30 hours -> MODERATE
    init_payload = {
        "food_category": "DAIRY",
        "item_name": "Artisan Cheese",
        "initial_quantity_kg": 25.0,
        "harvest_or_prep_date": (now - timedelta(hours=4)).isoformat(),
        "estimated_deadline": (now + timedelta(hours=30)).isoformat(),
        "food_condition": "GOOD",
        "storage_condition": "REFRIGERATED",
    }
    create_res = client.post("/api/v1/surplus-listings", json=init_payload, headers=headers)
    assert create_res.status_code == 201
    listing_id = create_res.json()["id"]
    assert create_res.json()["urgency_classification"] == "MODERATE"

    # Update deadline to 5 hours -> should transition to CRITICAL
    patch_res = client.patch(
        f"/api/v1/surplus-listings/{listing_id}",
        json={"estimated_deadline": (now + timedelta(hours=5)).isoformat()},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["urgency_classification"] == "CRITICAL"


def test_perishability_intelligence_api_endpoint(client):
    """Verify GET /api/v1/intelligence/perishability/{listing_id} endpoint."""
    token = register_and_login(client, "Produce Market", "produce@test.com", "SUPPLIER")
    create_supplier_profile(client, token)
    headers = {"Authorization": f"Bearer {token}"}
    now = datetime.now(timezone.utc)

    payload = {
        "food_category": "FRUITS",
        "item_name": "Ripe Bananas",
        "initial_quantity_kg": 50.0,
        "harvest_or_prep_date": (now - timedelta(hours=10)).isoformat(),
        "estimated_deadline": (now + timedelta(hours=15)).isoformat(),
        "food_condition": "RIPE",
        "storage_condition": "AMBIENT",
    }
    create_res = client.post("/api/v1/surplus-listings", json=payload, headers=headers)
    listing_id = create_res.json()["id"]

    # Call intelligence endpoint
    intel_res = client.get(f"/api/v1/intelligence/perishability/{listing_id}", headers=headers)
    assert intel_res.status_code == 200
    data = intel_res.json()

    assert data["listing_id"] == listing_id
    assert data["urgency"] == "HIGH"
    assert data["condition"] == "RIPE"
    assert data["storage_condition"] == "AMBIENT"
    assert data["data_quality"] == "COMPLETE"
    assert any("HANDLING WARNING" in w for w in data["warnings"])
    assert "disclaimer" in data
    assert FOOD_SAFETY_DISCLAIMER in data["disclaimer"]


def test_cross_tenant_isolation_on_intelligence_endpoint(client):
    """Supplier B cannot access Supplier A's perishability intelligence."""
    token_a = register_and_login(client, "Supplier A", "supp_a@test.com", "SUPPLIER")
    create_supplier_profile(client, token_a)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    token_b = register_and_login(client, "Supplier B", "supp_b@test.com", "SUPPLIER")
    create_supplier_profile(client, token_b)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    now = datetime.now(timezone.utc)
    create_res = client.post(
        "/api/v1/surplus-listings",
        json={
            "food_category": "VEGETABLES",
            "item_name": "Carrots",
            "initial_quantity_kg": 30.0,
            "harvest_or_prep_date": (now - timedelta(hours=2)).isoformat(),
            "estimated_deadline": (now + timedelta(days=3)).isoformat(),
        },
        headers=headers_a,
    )
    listing_id = create_res.json()["id"]

    # Supplier B attempts to view Supplier A's intelligence -> 404
    forbidden_res = client.get(
        f"/api/v1/intelligence/perishability/{listing_id}", headers=headers_b
    )
    assert forbidden_res.status_code == 404


def test_batch_active_perishability_endpoint(client):
    """Verify batch evaluation endpoint returns counts and evaluations for supplier."""
    token = register_and_login(client, "Batch Supplier", "batch_supp@test.com", "SUPPLIER")
    create_supplier_profile(client, token)
    headers = {"Authorization": f"Bearer {token}"}
    now = datetime.now(timezone.utc)

    # Create 2 listings: 1 CRITICAL (3h) and 1 MODERATE (36h)
    client.post(
        "/api/v1/surplus-listings",
        json={
            "food_category": "COOKED_FOOD",
            "item_name": "Lunch Soup",
            "initial_quantity_kg": 20.0,
            "harvest_or_prep_date": (now - timedelta(hours=1)).isoformat(),
            "estimated_deadline": (now + timedelta(hours=3)).isoformat(),
            "storage_condition": "REFRIGERATED",
        },
        headers=headers,
    )

    client.post(
        "/api/v1/surplus-listings",
        json={
            "food_category": "GRAINS",
            "item_name": "Oats",
            "initial_quantity_kg": 50.0,
            "harvest_or_prep_date": (now - timedelta(hours=2)).isoformat(),
            "estimated_deadline": (now + timedelta(hours=36)).isoformat(),
        },
        headers=headers,
    )

    batch_res = client.get("/api/v1/intelligence/perishability/batch-active", headers=headers)
    assert batch_res.status_code == 200
    data = batch_res.json()

    assert data["total_evaluated"] >= 2
    assert data["counts_by_urgency"]["CRITICAL"] >= 1
    assert data["counts_by_urgency"]["MODERATE"] >= 1
