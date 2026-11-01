import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List
from fastapi import HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from app.models.user import User, SupplierProfile, ReceiverProfile
from app.repositories.profile_repo import SupplierProfileRepository, ReceiverProfileRepository
from app.schemas.verification import (
    OrganizationVerificationItem,
    OrganizationVerificationStatusResponse,
)

UPLOAD_DIR = Path("uploads/verification_docs")
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/jpg",
    "application/octet-stream",  # Fallback for some clients
}


class VerificationService:
    @classmethod
    def get_user_status(cls, db: Session, current_user: User) -> OrganizationVerificationStatusResponse:
        """Retrieve the verification status and details for the authenticated user's organization."""
        org_id = None
        org_name = None
        status_val = current_user.verification_status or "PENDING_VERIFICATION"
        license_num = None
        rep_name = None
        doc_name = None
        has_doc = False
        sub_at = None
        ver_at = None
        rej_reason = None

        if current_user.role == "SUPPLIER":
            profile = SupplierProfileRepository.get_by_user_id(db, current_user.id)
            if profile:
                org_id = profile.id
                org_name = profile.organization_name
                status_val = profile.verification_status
                license_num = profile.license_number
                rep_name = profile.representative_name
                has_doc = bool(profile.verification_document_path)
                doc_name = profile.verification_document_name
                sub_at = profile.verification_submitted_at
                ver_at = profile.verified_at
                rej_reason = profile.rejection_reason
        elif current_user.role == "RECEIVER":
            profile = ReceiverProfileRepository.get_by_user_id(db, current_user.id)
            if profile:
                org_id = profile.id
                org_name = profile.organization_name
                status_val = profile.verification_status
                license_num = profile.license_number
                rep_name = profile.representative_name
                has_doc = bool(profile.verification_document_path)
                doc_name = profile.verification_document_name
                sub_at = profile.verification_submitted_at
                ver_at = profile.verified_at
                rej_reason = profile.rejection_reason

        return OrganizationVerificationStatusResponse(
            org_id=org_id,
            user_id=current_user.id,
            org_name=org_name,
            org_type=current_user.role,
            verification_status=status_val,
            is_verified=(status_val == "VERIFIED"),
            license_number=license_num,
            representative_name=rep_name,
            has_document=has_doc,
            document_name=doc_name,
            submitted_at=sub_at,
            verified_at=ver_at,
            rejection_reason=rej_reason,
        )

    @classmethod
    def submit_verification(
        cls,
        db: Session,
        current_user: User,
        representative_name: str,
        license_number: Optional[str],
        address: Optional[str],
        document: UploadFile,
    ) -> OrganizationVerificationStatusResponse:
        """Securely ingest organization credentials and documents for coordinator review."""
        if current_user.role not in ("SUPPLIER", "RECEIVER"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only supplier or receiver organizations can submit verification documents.",
            )

        if not representative_name or len(representative_name.strip()) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorized representative name must be at least 2 characters.",
            )

        # Validate file extension
        ext = Path(document.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type '{ext}'. Only PDF, JPG, and PNG documents are accepted.",
            )

        # Read and validate size
        file_bytes = document.file.read()
        if len(file_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded document file is empty.",
            )
        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document file size ({len(file_bytes) // 1024} KB) exceeds the 5 MB limit.",
            )

        # Fetch profile
        if current_user.role == "SUPPLIER":
            profile = SupplierProfileRepository.get_by_user_id(db, current_user.id)
            if not profile:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Supplier organization profile must be created before submitting verification.",
                )
        else:
            profile = ReceiverProfileRepository.get_by_user_id(db, current_user.id)
            if not profile:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Receiver organization profile must be created before submitting verification.",
                )

        # Save document securely
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        safe_filename = f"{profile.id}_{uuid.uuid4().hex[:8]}{ext}"
        saved_path = UPLOAD_DIR / safe_filename
        with open(saved_path, "wb") as f:
            f.write(file_bytes)

        # Update profile attributes
        now = datetime.now(timezone.utc)
        profile.representative_name = representative_name.strip()
        profile.license_number = license_number.strip() if license_number else None
        if address and address.strip():
            profile.address = address.strip()
        profile.verification_document_path = str(saved_path)
        profile.verification_document_name = document.filename
        profile.verification_status = "DOCUMENTS_SUBMITTED"
        profile.verification_submitted_at = now
        profile.rejection_reason = None

        current_user.verification_status = "DOCUMENTS_SUBMITTED"
        current_user.is_verified = False

        db.commit()
        db.refresh(profile)
        db.refresh(current_user)

        return cls.get_user_status(db, current_user)

    @classmethod
    def list_verifications(
        cls,
        db: Session,
        status_filter: Optional[str] = None,
        org_type_filter: Optional[str] = None,
    ) -> List[OrganizationVerificationItem]:
        """Coordinator view: aggregate all suppliers and receivers for verification review."""
        items: List[OrganizationVerificationItem] = []

        # 1. Fetch Suppliers
        if not org_type_filter or org_type_filter.upper() == "SUPPLIER":
            supp_query = select(SupplierProfile).options(joinedload(SupplierProfile.user))
            suppliers = list(db.scalars(supp_query).unique().all())
            for s in suppliers:
                if status_filter and s.verification_status != status_filter:
                    continue
                user_email = s.user.email if s.user else "N/A"
                reg_date = s.user.created_at if s.user else s.created_at
                items.append(
                    OrganizationVerificationItem(
                        org_id=s.id,
                        user_id=s.user_id,
                        org_name=s.organization_name,
                        org_type="SUPPLIER",
                        email=user_email,
                        registered_at=reg_date,
                        verification_status=s.verification_status,
                        license_number=s.license_number,
                        representative_name=s.representative_name,
                        address=s.address,
                        city=s.city,
                        has_document=bool(s.verification_document_path),
                        document_name=s.verification_document_name,
                        submitted_at=s.verification_submitted_at,
                        verified_at=s.verified_at,
                        rejection_reason=s.rejection_reason,
                    )
                )

        # 2. Fetch Receivers
        if not org_type_filter or org_type_filter.upper() == "RECEIVER":
            recv_query = select(ReceiverProfile).options(joinedload(ReceiverProfile.user))
            receivers = list(db.scalars(recv_query).unique().all())
            for r in receivers:
                if status_filter and r.verification_status != status_filter:
                    continue
                user_email = r.user.email if r.user else "N/A"
                reg_date = r.user.created_at if r.user else r.created_at
                items.append(
                    OrganizationVerificationItem(
                        org_id=r.id,
                        user_id=r.user_id,
                        org_name=r.organization_name,
                        org_type="RECEIVER",
                        email=user_email,
                        registered_at=reg_date,
                        verification_status=r.verification_status,
                        license_number=r.license_number,
                        representative_name=r.representative_name,
                        address=r.address,
                        city=r.city,
                        has_document=bool(r.verification_document_path),
                        document_name=r.verification_document_name,
                        submitted_at=r.verification_submitted_at,
                        verified_at=r.verified_at,
                        rejection_reason=r.rejection_reason,
                    )
                )

        # Sort: pending / submitted first, then newest
        def sort_key(it: OrganizationVerificationItem):
            priority = 0
            if it.verification_status == "DOCUMENTS_SUBMITTED":
                priority = 3
            elif it.verification_status == "PENDING_VERIFICATION":
                priority = 2
            elif it.verification_status == "REJECTED":
                priority = 1
            return (priority, it.submitted_at or it.registered_at)

        items.sort(key=sort_key, reverse=True)
        return items

    @classmethod
    def approve_verification(
        cls,
        db: Session,
        org_type: str,
        profile_id: uuid.UUID,
        coordinator: User,
    ) -> OrganizationVerificationItem:
        """Coordinator action: Approve an organization, setting status to VERIFIED."""
        now = datetime.now(timezone.utc)
        clean_type = org_type.upper().strip()

        if clean_type == "SUPPLIER":
            profile = SupplierProfileRepository.get_by_id(db, profile_id)
        elif clean_type == "RECEIVER":
            profile = ReceiverProfileRepository.get_by_id(db, profile_id)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid organization type '{org_type}'.")

        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization profile not found.")

        # Self-approval prevention
        if coordinator.id == profile.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Coordinators cannot approve their own organization.",
            )

        profile.verification_status = "VERIFIED"
        profile.verified_at = now
        profile.verified_by_user_id = coordinator.id
        profile.rejection_reason = None

        user = db.get(User, profile.user_id)
        if user:
            user.is_verified = True
            user.verification_status = "VERIFIED"

        db.commit()
        db.refresh(profile)

        user_email = user.email if user else "N/A"
        return OrganizationVerificationItem(
            org_id=profile.id,
            user_id=profile.user_id,
            org_name=profile.organization_name,
            org_type=clean_type,
            email=user_email,
            registered_at=user.created_at if user else profile.created_at,
            verification_status="VERIFIED",
            license_number=profile.license_number,
            representative_name=profile.representative_name,
            address=profile.address,
            city=profile.city,
            has_document=bool(profile.verification_document_path),
            document_name=profile.verification_document_name,
            submitted_at=profile.verification_submitted_at,
            verified_at=profile.verified_at,
            rejection_reason=None,
        )

    @classmethod
    def reject_verification(
        cls,
        db: Session,
        org_type: str,
        profile_id: uuid.UUID,
        reason: str,
        coordinator: User,
    ) -> OrganizationVerificationItem:
        """Coordinator action: Reject an organization with a mandatory justification."""
        now = datetime.now(timezone.utc)
        clean_type = org_type.upper().strip()

        if not reason or len(reason.strip()) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid rejection reason (minimum 3 characters) is required.",
            )

        if clean_type == "SUPPLIER":
            profile = SupplierProfileRepository.get_by_id(db, profile_id)
        elif clean_type == "RECEIVER":
            profile = ReceiverProfileRepository.get_by_id(db, profile_id)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid organization type '{org_type}'.")

        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization profile not found.")

        # Self-rejection prevention
        if coordinator.id == profile.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Coordinators cannot reject their own organization.",
            )

        profile.verification_status = "REJECTED"
        profile.verified_at = now
        profile.verified_by_user_id = coordinator.id
        profile.rejection_reason = reason.strip()

        user = db.get(User, profile.user_id)
        if user:
            user.is_verified = False
            user.verification_status = "REJECTED"

        db.commit()
        db.refresh(profile)

        user_email = user.email if user else "N/A"
        return OrganizationVerificationItem(
            org_id=profile.id,
            user_id=profile.user_id,
            org_name=profile.organization_name,
            org_type=clean_type,
            email=user_email,
            registered_at=user.created_at if user else profile.created_at,
            verification_status="REJECTED",
            license_number=profile.license_number,
            representative_name=profile.representative_name,
            address=profile.address,
            city=profile.city,
            has_document=bool(profile.verification_document_path),
            document_name=profile.verification_document_name,
            submitted_at=profile.verification_submitted_at,
            verified_at=profile.verified_at,
            rejection_reason=profile.rejection_reason,
        )

    @classmethod
    def get_document(
        cls,
        db: Session,
        org_type: str,
        profile_id: uuid.UUID,
        current_user: User,
    ) -> FileResponse:
        """Securely stream uploaded verification document. Accessible only to coordinator/admin or owner."""
        clean_type = org_type.upper().strip()
        if clean_type == "SUPPLIER":
            profile = SupplierProfileRepository.get_by_id(db, profile_id)
        elif clean_type == "RECEIVER":
            profile = ReceiverProfileRepository.get_by_id(db, profile_id)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid organization type.")

        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

        # RBAC and Ownership Check
        if current_user.role not in ("COORDINATOR", "ADMIN") and current_user.id != profile.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this organization's verification documents.",
            )

        if not profile.verification_document_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No verification document has been uploaded for this organization.",
            )

        file_path = Path(profile.verification_document_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Verification document file could not be found on server storage.",
            )

        ext = file_path.suffix.lower()
        media_type = "application/pdf" if ext == ".pdf" else f"image/{ext.lstrip('.')}"
        if ext == ".jpg":
            media_type = "image/jpeg"

        return FileResponse(
            path=str(file_path),
            filename=profile.verification_document_name or file_path.name,
            media_type=media_type,
        )
