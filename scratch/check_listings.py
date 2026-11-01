import sys
sys.path.insert(0, "backend")
from app.database.session import SessionLocal
from app.models.food import SurplusListing, DemandRequest

db = SessionLocal()
from sqlalchemy import func
active_listing = db.query(SurplusListing).filter(SurplusListing.status == "ACTIVE").first()
print(f"Active listing: {active_listing.id}, {active_listing.item_name}, category: {active_listing.food_category}, remaining: {active_listing.remaining_quantity_kg}")
from app.matching.matching_service import MatchingService
from app.models.user import User
coord = db.query(User).filter(User.role == "COORDINATOR").first()
result = MatchingService.find_candidates_for_listing(db, active_listing.id, coord, include_ineligible=True)
print(f"Candidates for listing: eligible={len(result.eligible_candidates)}, ineligible={len(result.ineligible_candidates)}")
if result.ineligible_candidates:
    print("Sample ineligible provider:", result.ineligible_candidates[0].routing_provider)
    print("Sample ineligible reasons:", result.ineligible_candidates[0].rejection_reasons)
if result.eligible_candidates:
    print("Sample eligible provider:", result.eligible_candidates[0].routing_provider)
db.close()
