import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.matching.models import MatchingQueryResponse
from app.matching.matching_service import MatchingService

router = APIRouter(prefix="/matching", tags=["Supply-Demand Matching"])


@router.get(
    "/listings/{listing_id}/candidates",
    response_model=MatchingQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Find compatible receiver candidates for surplus listing",
    description=(
        "Retrieve ranked receiver demand candidates for a registered surplus food listing. "
        "Evaluates product category, dietary requirements, condition threshold, cold chain capability, "
        "and physical transit feasibility. Authoritative records fetched from PostgreSQL."
    ),
)
def get_candidates_for_listing(
    listing_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    include_ineligible: bool = Query(
        False, description="Include candidates failing hard constraints (for transparency/audit)"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MatchingQueryResponse:
    return MatchingService.find_candidates_for_listing(
        db=db,
        listing_id=listing_id,
        current_user=current_user,
        page=page,
        page_size=page_size,
        include_ineligible=include_ineligible,
    )


@router.get(
    "/demands/{demand_id}/candidates",
    response_model=MatchingQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Find compatible surplus candidates for receiver demand",
    description=(
        "Retrieve ranked surplus inventory listings capable of fulfilling a registered receiver demand request. "
        "Evaluates volume alignment, remaining shelf-life, storage requirements, and road transit feasibility. "
        "Authoritative records fetched from PostgreSQL."
    ),
)
def get_candidates_for_demand(
    demand_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    include_ineligible: bool = Query(
        False, description="Include candidates failing hard constraints (for transparency/audit)"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MatchingQueryResponse:
    return MatchingService.find_candidates_for_demand(
        db=db,
        demand_id=demand_id,
        current_user=current_user,
        page=page,
        page_size=page_size,
        include_ineligible=include_ineligible,
    )
