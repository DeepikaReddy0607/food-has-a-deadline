import uuid
from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User
from app.intelligence.models import PerishabilityEvaluation, BatchEvaluationResponse
from app.services.surplus_service import SurplusService

router = APIRouter(prefix="/intelligence", tags=["Perishability Intelligence"])


@router.get(
    "/perishability/batch-active",
    response_model=BatchEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch evaluate active surplus listings",
    description=(
        "Run deterministic perishability evaluation across all active and paused surplus listings. "
        "Suppliers receive evaluations for their own active inventory; coordinators/admins evaluate system-wide."
    ),
)
def batch_evaluate_active_listings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BatchEvaluationResponse:
    return SurplusService.batch_evaluate_active(db, current_user)


@router.get(
    "/perishability/{listing_id}",
    response_model=PerishabilityEvaluation,
    status_code=status.HTTP_200_OK,
    summary="Get listing perishability intelligence",
    description=(
        "Compute deterministic perishability intelligence and urgency classification for a surplus inventory listing. "
        "Suppliers may only access their own listings; coordinators and admins may evaluate any active listing."
    ),
)
def get_listing_perishability(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PerishabilityEvaluation:
    return SurplusService.get_listing_perishability(db, current_user, listing_id)
