import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

BASE_URL = "http://127.0.0.1:8000"

def run_benchmark():
    print("=== LIVE ENDPOINT BENCHMARK ===")
    
    # 1. Login as coordinator
    login_data = json.dumps({
        "email": "coordinator@fhd.org",
        "password": "CoordinatorPass123!"
    }).encode("utf-8")
    
    login_req = urllib.request.Request(
        f"{BASE_URL}/api/v1/auth/login",
        data=login_data,
        headers={"Content-Type": "application/json"}
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(login_req) as resp:
        token = json.loads(resp.read().decode("utf-8"))["access_token"]
    print(f"1. Coordinator login OK in {(time.perf_counter() - t0)*1000:.1f}ms")

    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 2. Get active listing ID from batch-active
    batch_req = urllib.request.Request(
        f"{BASE_URL}/api/v1/intelligence/perishability/batch-active",
        headers=auth_headers
    )
    with urllib.request.urlopen(batch_req) as resp:
        batch_resp = json.loads(resp.read().decode("utf-8"))
    
    items = batch_resp.get("items", [])
    if not items:
        raise RuntimeError("No active listings found in batch-active response")
    
    test_eval = items[0]
    listing_id = test_eval["listing_id"]
    print(f"2. Selected Listing ID: {listing_id} (Perishability urgency: {test_eval['urgency']}, storage: {test_eval['storage_condition']})")

    # 3. Benchmark GET /api/v1/matching/listings/{listing_id}/candidates?include_ineligible=true
    print(f"\n3. Benchmarking GET /api/v1/matching/listings/{listing_id}/candidates?include_ineligible=true ...")
    candidates_url = f"{BASE_URL}/api/v1/matching/listings/{listing_id}/candidates?include_ineligible=true&page_size=100"
    cand_req = urllib.request.Request(candidates_url, headers=auth_headers)
    
    t_start = time.perf_counter()
    with urllib.request.urlopen(cand_req) as resp:
        duration_cand = time.perf_counter() - t_start
        status_cand = resp.status
        cand_data = json.loads(resp.read().decode("utf-8"))

    print(f"   -> HTTP Status: {status_cand}")
    print(f"   -> Duration: {duration_cand:.3f}s")
    
    # Inspect candidate matching response
    candidates = cand_data.get("candidates", [])
    total_candidates = cand_data.get("total_candidates", len(candidates))
    eligible_count = cand_data.get("eligible_count", sum(1 for c in candidates if c.get("is_eligible")))
    ineligible_count = cand_data.get("ineligible_count", sum(1 for c in candidates if not c.get("is_eligible")))
    print(f"   -> Total Candidates Evaluated: {total_candidates} ({eligible_count} eligible, {ineligible_count} ineligible)")
    
    haversine_count = sum(1 for c in candidates if not c.get("is_eligible") and c.get("routing_provider") == "HAVERSINE_FALLBACK")
    osrm_count = sum(1 for c in candidates if c.get("is_eligible") and c.get("routing_provider") in ("OSRM", "OSRM_ONLINE", "OSRM_CACHE"))
    print(f"   -> Ineligible using HAVERSINE_FALLBACK (OSRM skipped): {haversine_count}/{ineligible_count}")
    print(f"   -> Eligible using OSRM / OSRM_CACHE: {osrm_count}/{eligible_count}")

    # 4. Benchmark POST /api/v1/optimization/allocation-proposals
    print(f"\n4. Benchmarking POST /api/v1/optimization/allocation-proposals ...")
    proposal_url = f"{BASE_URL}/api/v1/optimization/allocation-proposals"
    proposal_payload = json.dumps({
        "time_window_start": datetime.now(timezone.utc).isoformat(),
        "time_window_end": datetime.now(timezone.utc).isoformat(),
        "solver_timeout_seconds": 10
    }).encode("utf-8")
    
    prop_req = urllib.request.Request(proposal_url, data=proposal_payload, headers=auth_headers)
    
    t_prop_start = time.perf_counter()
    with urllib.request.urlopen(prop_req) as resp:
        duration_prop = time.perf_counter() - t_prop_start
        status_prop = resp.status
        prop_data = json.loads(resp.read().decode("utf-8"))

    print(f"   -> HTTP Status: {status_prop}")
    print(f"   -> Duration: {duration_prop:.3f}s")
    
    items = prop_data.get("items", [])
    total_kg = sum(item.get("allocated_quantity_kg", 0) for item in items)
    print(f"   -> Proposal ID: {prop_data.get('proposal_id')}")
    print(f"   -> Total Allocations: {len(items)}")
    print(f"   -> Total Food Rescued: {total_kg:.2f} kg")
    print(f"   -> Solver Status: {prop_data.get('solver_status')}")
    print(f"   -> Solve Time: {prop_data.get('execution_duration_ms')}ms")

    # 5. Summary Results Dictionary
    summary = {
        "candidate_matching": {
            "endpoint": f"GET /api/v1/matching/listings/{listing_id}/candidates?include_ineligible=true",
            "http_status": status_cand,
            "duration_seconds": round(duration_cand, 3),
            "eligible_candidates": eligible_count,
            "ineligible_candidates": ineligible_count,
            "total_candidates": total_candidates,
            "osrm_skipped_count": haversine_count,
            "within_extended_timeout": duration_cand < 60.0,
            "within_original_timeout": duration_cand < 8.0
        },
        "optimization_proposal": {
            "endpoint": "POST /api/v1/optimization/allocation-proposals",
            "http_status": status_prop,
            "duration_seconds": round(duration_prop, 3),
            "proposal_id": prop_data.get("proposal_id"),
            "allocations_count": len(items),
            "total_allocated_kg": round(total_kg, 2),
            "solver_status": prop_data.get("solver_status"),
            "solver_duration_ms": prop_data.get("execution_duration_ms"),
            "within_extended_timeout": duration_prop < 60.0
        }
    }
    
    with open("scratch/live_benchmark_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("\nBenchmark results saved to scratch/live_benchmark_results.json")

if __name__ == "__main__":
    run_benchmark()
