from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import require_role, get_current_user
from app.models.user import User
from app.schemas.profile import (
    ReceiverProfileCreate,
    ReceiverProfileUpdate,
    ReceiverProfileResponse,
)
from app.repositories.profile_repo import ReceiverProfileRepository
from app.services.profile_service import ReceiverProfileService

router = APIRouter(prefix="/receivers", tags=["Receiver Management"])


@router.get(
    "/directory",
    response_model=List[ReceiverProfileResponse],
    status_code=status.HTTP_200_OK,
    summary="List receiver directory",
    description="Retrieve list of registered receiver organizations with facility coordinates and capacities.",
)
def list_receivers_directory(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[ReceiverProfileResponse]:
    return ReceiverProfileRepository.list_all(db)


@router.post(
    "/profile",
    response_model=ReceiverProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create receiver profile",
    description="Create an organization intake profile for an authenticated RECEIVER account.",
)
def create_receiver_profile(
    data: ReceiverProfileCreate,
    current_user: User = Depends(require_role("RECEIVER", "ADMIN")),
    db: Session = Depends(get_db),
) -> ReceiverProfileResponse:
    return ReceiverProfileService.create_profile(db, current_user, data)


@router.get(
    "/profile",
    response_model=ReceiverProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get receiver profile",
    description="Retrieve the organization profile of the currently authenticated RECEIVER.",
)
def get_receiver_profile(
    current_user: User = Depends(require_role("RECEIVER", "ADMIN")),
    db: Session = Depends(get_db),
) -> ReceiverProfileResponse:
    return ReceiverProfileService.get_profile(db, current_user)


@router.patch(
    "/profile",
    response_model=ReceiverProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update receiver profile",
    description="Selectively update fields in the authenticated receiver's organization profile.",
)
def update_receiver_profile(
    data: ReceiverProfileUpdate,
    current_user: User = Depends(require_role("RECEIVER", "ADMIN")),
    db: Session = Depends(get_db),
) -> ReceiverProfileResponse:
    return ReceiverProfileService.update_profile(db, current_user, data)
