import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import require_role
from app.models.user import User
from app.schemas.surplus import (
    SurplusListingCreate,
    SurplusListingUpdate,
    SurplusListingResponse,
    SurplusPaginationResponse,
)
from app.services.surplus_service import SurplusService

router = APIRouter(prefix="/surplus-listings", tags=["Surplus Inventory"])


@router.post(
    "",
    response_model=SurplusListingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create surplus food listing",
    description="Register a new surplus perishable food listing for the authenticated supplier.",
)
def create_surplus_listing(
    data: SurplusListingCreate,
    current_user: User = Depends(require_role("SUPPLIER", "ADMIN")),
    db: Session = Depends(get_db),
) -> SurplusListingResponse:
    return SurplusService.create_listing(db, current_user, data)


@router.get(
    "",
    response_model=SurplusPaginationResponse,
    status_code=status.HTTP_200_OK,
    summary="List supplier surplus listings",
    description="Retrieve paginated listings registered by the authenticated supplier with optional status and category filters.",
)
def list_surplus_listings(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, PAUSED, DEPLETED, EXPIRED, CANCELLED)"),
    food_category: Optional[str] = Query(None, description="Filter by food category"),
    current_user: User = Depends(require_role("SUPPLIER", "ADMIN")),
    db: Session = Depends(get_db),
) -> SurplusPaginationResponse:
    return SurplusService.list_listings(
        db,
        current_user,
        page=page,
        page_size=page_size,
        status_filter=status,
        food_category=food_category,
    )


@router.get(
    "/{listing_id}",
    response_model=SurplusListingResponse,
    status_code=status.HTTP_200_OK,
    summary="Get surplus listing details",
    description="Retrieve full details for a specific surplus listing owned by the authenticated supplier.",
)
def get_surplus_listing(
    listing_id: uuid.UUID,
    current_user: User = Depends(require_role("SUPPLIER", "ADMIN")),
    db: Session = Depends(get_db),
) -> SurplusListingResponse:
    return SurplusService.get_listing(db, current_user, listing_id)


@router.patch(
    "/{listing_id}",
    response_model=SurplusListingResponse,
    status_code=status.HTTP_200_OK,
    summary="Update surplus listing",
    description="Modify allowed fields of an active or paused surplus listing.",
)
def update_surplus_listing(
    listing_id: uuid.UUID,
    data: SurplusListingUpdate,
    current_user: User = Depends(require_role("SUPPLIER", "ADMIN")),
    db: Session = Depends(get_db),
) -> SurplusListingResponse:
    return SurplusService.update_listing(db, current_user, listing_id, data)


@router.post(
    "/{listing_id}/pause",
    response_model=SurplusListingResponse,
    status_code=status.HTTP_200_OK,
    summary="Pause surplus listing",
    description="Temporarily pause redistribution offers for this surplus listing.",
)
def pause_surplus_listing(
    listing_id: uuid.UUID,
    current_user: User = Depends(require_role("SUPPLIER", "ADMIN")),
    db: Session = Depends(get_db),
) -> SurplusListingResponse:
    return SurplusService.pause_listing(db, current_user, listing_id)


@router.post(
    "/{listing_id}/resume",
    response_model=SurplusListingResponse,
    status_code=status.HTTP_200_OK,
    summary="Resume surplus listing",
    description="Resume a paused surplus listing if deadline and remaining quantity are still valid.",
)
def resume_surplus_listing(
    listing_id: uuid.UUID,
    current_user: User = Depends(require_role("SUPPLIER", "ADMIN")),
    db: Session = Depends(get_db),
) -> SurplusListingResponse:
    return SurplusService.resume_listing(db, current_user, listing_id)


@router.post(
    "/{listing_id}/cancel",
    response_model=SurplusListingResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel surplus listing",
    description="Permanently cancel a surplus listing.",
)
def cancel_surplus_listing(
    listing_id: uuid.UUID,
    current_user: User = Depends(require_role("SUPPLIER", "ADMIN")),
    db: Session = Depends(get_db),
) -> SurplusListingResponse:
    return SurplusService.cancel_listing(db, current_user, listing_id)
