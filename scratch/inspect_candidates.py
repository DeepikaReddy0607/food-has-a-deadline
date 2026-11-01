import json
import urllib.request
import urllib.parse

BASE_URL = "http://127.0.0.1:8000"

login_data = json.dumps({
    "email": "coordinator@fhd.org",
    "password": "CoordinatorPass123!"
}).encode("utf-8")

login_req = urllib.request.Request(
    f"{BASE_URL}/api/v1/auth/login",
    data=login_data,
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(login_req) as resp:
    token = json.loads(resp.read().decode("utf-8"))["access_token"]

auth_headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

listing_id = "2fa8426f-21fb-434e-9522-a2aacce78426"
candidates_url = f"{BASE_URL}/api/v1/matching/listings/{listing_id}/candidates?include_ineligible=true&page_size=100"
cand_req = urllib.request.Request(candidates_url, headers=auth_headers)

with urllib.request.urlopen(cand_req) as resp:
    cand_data = json.loads(resp.read().decode("utf-8"))

candidates = cand_data.get("candidates", [])
providers = {}
reasons = {}
for c in candidates:
    prov = c.get("routing_provider", "UNKNOWN")
    providers[prov] = providers.get(prov, 0) + 1
    for r in c.get("rejection_reasons", []):
        cat = r.split(":")[0] if ":" in r else r
        reasons[cat] = reasons.get(cat, 0) + 1

print("Routing Providers:", providers)
print("Rejection Reasons Breakdown:", reasons)
