import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Form, File, UploadFile, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.verification import (
    OrganizationVerificationItem,
    OrganizationVerificationStatusResponse,
    VerificationRejectionRequest,
)
from app.services.verification_service import VerificationService

router = APIRouter(prefix="/verifications", tags=["Organization Verification"])


@router.get(
    "/status",
    response_model=OrganizationVerificationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current organization verification status",
    description="Retrieve the organization verification review status, submitted details, and badges for the authenticated user.",
)
def get_verification_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganizationVerificationStatusResponse:
    return VerificationService.get_user_status(db, current_user)


@router.post(
    "/submit",
    response_model=OrganizationVerificationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit organization verification documents",
    description="Upload identity/registration documents and representative details for coordinator review.",
)
def submit_verification(
    representative_name: str = Form(..., description="Authorized organization representative name"),
    license_number: Optional[str] = Form(None, description="Registration / trade license / tax number"),
    address: Optional[str] = Form(None, description="Physical organization address"),
    document: UploadFile = File(..., description="Supporting registration document (PDF, JPG, PNG, max 5MB)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganizationVerificationStatusResponse:
    return VerificationService.submit_verification(
        db=db,
        current_user=current_user,
        representative_name=representative_name,
        license_number=license_number,
        address=address,
        document=document,
    )


@router.get(
    "",
    response_model=List[OrganizationVerificationItem],
    status_code=status.HTTP_200_OK,
    summary="List organization verification requests",
    description="Coordinator/Admin view to list registered organizations and their verification statuses.",
)
def list_verifications(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (PENDING_VERIFICATION, DOCUMENTS_SUBMITTED, VERIFIED, REJECTED)"),
    org_type: Optional[str] = Query(None, description="Filter by organization type (SUPPLIER, RECEIVER)"),
    current_user: User = Depends(require_role("COORDINATOR", "ADMIN")),
    db: Session = Depends(get_db),
) -> List[OrganizationVerificationItem]:
    return VerificationService.list_verifications(
        db=db,
        status_filter=status_filter,
        org_type_filter=org_type,
    )


@router.post(
    "/{org_type}/{profile_id}/approve",
    response_model=OrganizationVerificationItem,
    status_code=status.HTTP_200_OK,
    summary="Approve organization verification",
    description="Coordinator action to approve an organization and grant VERIFIED status.",
)
def approve_verification(
    org_type: str,
    profile_id: uuid.UUID,
    current_user: User = Depends(require_role("COORDINATOR", "ADMIN")),
    db: Session = Depends(get_db),
) -> OrganizationVerificationItem:
    return VerificationService.approve_verification(
        db=db,
        org_type=org_type,
        profile_id=profile_id,
        coordinator=current_user,
    )


@router.post(
    "/{org_type}/{profile_id}/reject",
    response_model=OrganizationVerificationItem,
    status_code=status.HTTP_200_OK,
    summary="Reject organization verification",
    description="Coordinator action to reject an organization with a mandatory justification.",
)
def reject_verification(
    org_type: str,
    profile_id: uuid.UUID,
    rejection: VerificationRejectionRequest,
    current_user: User = Depends(require_role("COORDINATOR", "ADMIN")),
    db: Session = Depends(get_db),
) -> OrganizationVerificationItem:
    return VerificationService.reject_verification(
        db=db,
        org_type=org_type,
        profile_id=profile_id,
        reason=rejection.reason,
        coordinator=current_user,
    )


@router.get(
    "/{org_type}/{profile_id}/document",
    summary="Download verification document",
    description="Securely access submitted verification document. Restricted to coordinators, admins, or the owning organization.",
)
def get_verification_document(
    org_type: str,
    profile_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    return VerificationService.get_document(
        db=db,
        org_type=org_type,
        profile_id=profile_id,
        current_user=current_user,
    )
