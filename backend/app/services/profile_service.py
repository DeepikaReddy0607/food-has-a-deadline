from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User, SupplierProfile, ReceiverProfile
from app.repositories.profile_repo import SupplierProfileRepository, ReceiverProfileRepository
from app.schemas.profile import (
    SupplierProfileCreate,
    SupplierProfileUpdate,
    ReceiverProfileCreate,
    ReceiverProfileUpdate,
)


class SupplierProfileService:
    @staticmethod
    def create_profile(db: Session, user: User, data: SupplierProfileCreate) -> SupplierProfile:
        if user.role != "SUPPLIER" and user.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only users with the SUPPLIER role can create a supplier profile.",
            )

        existing = SupplierProfileRepository.get_by_user_id(db, user.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supplier profile already exists for this account. Use PATCH to update existing details.",
            )

        return SupplierProfileRepository.create(db, user.id, data)

    @staticmethod
    def get_profile(db: Session, user: User) -> SupplierProfile:
        profile = SupplierProfileRepository.get_by_user_id(db, user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier profile not found. Please complete your profile setup.",
            )
        return profile

    @staticmethod
    def update_profile(db: Session, user: User, data: SupplierProfileUpdate) -> SupplierProfile:
        profile = SupplierProfileRepository.get_by_user_id(db, user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier profile not found. Please complete your profile setup before editing.",
            )
        return SupplierProfileRepository.update(db, profile, data)


class ReceiverProfileService:
    @staticmethod
    def create_profile(db: Session, user: User, data: ReceiverProfileCreate) -> ReceiverProfile:
        if user.role != "RECEIVER" and user.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only users with the RECEIVER role can create a receiver profile.",
            )

        existing = ReceiverProfileRepository.get_by_user_id(db, user.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Receiver profile already exists for this account. Use PATCH to update existing details.",
            )

        return ReceiverProfileRepository.create(db, user.id, data)

    @staticmethod
    def get_profile(db: Session, user: User) -> ReceiverProfile:
        profile = ReceiverProfileRepository.get_by_user_id(db, user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiver profile not found. Please complete your profile setup.",
            )
        return profile

    @staticmethod
    def update_profile(db: Session, user: User, data: ReceiverProfileUpdate) -> ReceiverProfile:
        profile = ReceiverProfileRepository.get_by_user_id(db, user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiver profile not found. Please complete your profile setup before editing.",
            )
        return ReceiverProfileRepository.update(db, profile, data)
