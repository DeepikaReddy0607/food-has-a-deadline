import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.repositories.profile_repo import SupplierProfileRepository, ReceiverProfileRepository
from app.repositories.surplus_repo import SurplusRepository
from app.geospatial.models import RouteEstimateRequest, RouteEstimateResult
from app.geospatial.routing_service import routing_service

router = APIRouter(prefix="/geospatial", tags=["Geospatial Routing"])


@router.post(
    "/route-estimate",
    response_model=RouteEstimateResult,
    status_code=status.HTTP_200_OK,
    summary="Estimate route and transportation feasibility",
    description=(
        "Calculate straight-line distance, road travel distance, transit duration, and temporal shelf-life "
        "feasibility between a registered surplus food listing and a receiver destination. "
        "Coordinates are strictly retrieved from PostgreSQL facility profiles."
    ),
)
def estimate_route_feasibility(
    data: RouteEstimateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RouteEstimateResult:
    # 1. Retrieve Surplus Listing
    listing = SurplusRepository.get_by_id(db, data.surplus_listing_id)
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Surplus listing not found.",
        )

    # 2. Retrieve Supplier Profile
    supplier = SupplierProfileRepository.get_by_id(db, listing.supplier_id)
    if not supplier or supplier.latitude is None or supplier.longitude is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supplier facility location coordinates are missing or incomplete.",
        )

    # 3. Retrieve Receiver Profile
    receiver = ReceiverProfileRepository.get_by_id(db, data.receiver_id)
    if not receiver or receiver.latitude is None or receiver.longitude is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver facility profile not found or location coordinates are incomplete.",
        )

    # 4. Access Control
    if current_user.role == "SUPPLIER":
        user_supplier_profile = SupplierProfileRepository.get_by_user_id(db, current_user.id)
        if not user_supplier_profile or listing.supplier_id != user_supplier_profile.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surplus listing not found.",
            )
    elif current_user.role == "RECEIVER":
        user_receiver_profile = ReceiverProfileRepository.get_by_user_id(db, current_user.id)
        if not user_receiver_profile or data.receiver_id != user_receiver_profile.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiver facility profile not found.",
            )
    elif current_user.role not in ["COORDINATOR", "ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to access geospatial routing services.",
        )

    # 5. Compute Route Estimate
    result = routing_service.estimate_route(
        supplier_id=supplier.id,
        receiver_id=receiver.id,
        supplier_lat=float(supplier.latitude),
        supplier_lon=float(supplier.longitude),
        dest_lat=float(receiver.latitude),
        dest_lon=float(receiver.longitude),
        estimated_usable_deadline=listing.estimated_deadline,
        handling_buffer_minutes=data.handling_buffer_minutes or 30,
        supplier_name=supplier.organization_name,
        receiver_name=receiver.organization_name,
    )

    return result
