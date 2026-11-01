import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import require_role
from app.models.user import User
from app.schemas.demand import (
    DemandRequestCreate,
    DemandRequestUpdate,
    DemandRequestResponse,
    DemandPaginationResponse,
)
from app.services.demand_service import DemandService

router = APIRouter(prefix="/demand-requests", tags=["Demand Management"])


@router.post(
    "",
    response_model=DemandRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create food demand request",
    description="Register a new food requirement for the authenticated receiver.",
)
def create_demand_request(
    data: DemandRequestCreate,
    current_user: User = Depends(require_role("RECEIVER", "ADMIN")),
    db: Session = Depends(get_db),
) -> DemandRequestResponse:
    return DemandService.create_demand(db, current_user, data)


@router.get(
    "",
    response_model=DemandPaginationResponse,
    status_code=status.HTTP_200_OK,
    summary="List receiver demand requests",
    description="Retrieve paginated demand requests registered by the authenticated receiver with optional status and category filters.",
)
def list_demand_requests(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status (OPEN, PAUSED, PARTIALLY_FULFILLED, FULFILLED, EXPIRED, CANCELLED)"),
    food_category: Optional[str] = Query(None, description="Filter by food category"),
    current_user: User = Depends(require_role("RECEIVER", "ADMIN")),
    db: Session = Depends(get_db),
) -> DemandPaginationResponse:
    return DemandService.list_demands(
        db,
        current_user,
        page=page,
        page_size=page_size,
        status_filter=status,
        food_category=food_category,
    )


@router.get(
    "/{demand_id}",
    response_model=DemandRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Get demand request details",
    description="Retrieve full details for a specific demand request owned by the authenticated receiver.",
)
def get_demand_request(
    demand_id: uuid.UUID,
    current_user: User = Depends(require_role("RECEIVER", "ADMIN")),
    db: Session = Depends(get_db),
) -> DemandRequestResponse:
    return DemandService.get_demand(db, current_user, demand_id)


@router.patch(
    "/{demand_id}",
    response_model=DemandRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Update demand request",
    description="Modify allowed fields of an open or paused demand request.",
)
def update_demand_request(
    demand_id: uuid.UUID,
    data: DemandRequestUpdate,
    current_user: User = Depends(require_role("RECEIVER", "ADMIN")),
    db: Session = Depends(get_db),
) -> DemandRequestResponse:
    return DemandService.update_demand(db, current_user, demand_id, data)


@router.post(
    "/{demand_id}/pause",
    response_model=DemandRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Pause demand request",
    description="Temporarily pause incoming allocation matches for this demand request.",
)
def pause_demand_request(
    demand_id: uuid.UUID,
    current_user: User = Depends(require_role("RECEIVER", "ADMIN")),
    db: Session = Depends(get_db),
) -> DemandRequestResponse:
    return DemandService.pause_demand(db, current_user, demand_id)


@router.post(
    "/{demand_id}/resume",
    response_model=DemandRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Resume demand request",
    description="Resume a paused demand request if deadline and requirement are still valid.",
)
def resume_demand_request(
    demand_id: uuid.UUID,
    current_user: User = Depends(require_role("RECEIVER", "ADMIN")),
    db: Session = Depends(get_db),
) -> DemandRequestResponse:
    return DemandService.resume_demand(db, current_user, demand_id)


@router.post(
    "/{demand_id}/cancel",
    response_model=DemandRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel demand request",
    description="Permanently cancel a demand request.",
)
def cancel_demand_request(
    demand_id: uuid.UUID,
    current_user: User = Depends(require_role("RECEIVER", "ADMIN")),
    db: Session = Depends(get_db),
) -> DemandRequestResponse:
    return DemandService.cancel_demand(db, current_user, demand_id)
