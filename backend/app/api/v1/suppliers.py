from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import require_role, get_current_user
from app.models.user import User
from app.schemas.profile import (
    SupplierProfileCreate,
    SupplierProfileUpdate,
    SupplierProfileResponse,
)
from app.repositories.profile_repo import SupplierProfileRepository
from app.services.profile_service import SupplierProfileService

router = APIRouter(prefix="/suppliers", tags=["Supplier Management"])


@router.get(
    "/directory",
    response_model=List[SupplierProfileResponse],
    status_code=status.HTTP_200_OK,
    summary="List supplier directory",
    description="Retrieve list of registered supplier organizations with facility locations and types.",
)
def list_suppliers_directory(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[SupplierProfileResponse]:
    return SupplierProfileRepository.list_all(db)


@router.post(
    "/profile",
    response_model=SupplierProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create supplier profile",
    description="Create an organization profile for an authenticated SUPPLIER account.",
)
def create_supplier_profile(
    data: SupplierProfileCreate,
    current_user: User = Depends(require_role("SUPPLIER", "ADMIN")),
    db: Session = Depends(get_db),
) -> SupplierProfileResponse:
    return SupplierProfileService.create_profile(db, current_user, data)


@router.get(
    "/profile",
    response_model=SupplierProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get supplier profile",
    description="Retrieve the organization profile of the currently authenticated SUPPLIER.",
)
def get_supplier_profile(
    current_user: User = Depends(require_role("SUPPLIER", "ADMIN")),
    db: Session = Depends(get_db),
) -> SupplierProfileResponse:
    return SupplierProfileService.get_profile(db, current_user)


@router.patch(
    "/profile",
    response_model=SupplierProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update supplier profile",
    description="Selectively update fields in the authenticated supplier's organization profile.",
)
def update_supplier_profile(
    data: SupplierProfileUpdate,
    current_user: User = Depends(require_role("SUPPLIER", "ADMIN")),
    db: Session = Depends(get_db),
) -> SupplierProfileResponse:
    return SupplierProfileService.update_profile(db, current_user, data)
