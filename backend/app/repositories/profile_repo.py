import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.user import SupplierProfile, ReceiverProfile
from app.schemas.profile import (
    SupplierProfileCreate,
    SupplierProfileUpdate,
    ReceiverProfileCreate,
    ReceiverProfileUpdate,
)


class SupplierProfileRepository:
    @staticmethod
    def get_by_user_id(db: Session, user_id: uuid.UUID) -> Optional[SupplierProfile]:
        return db.scalar(select(SupplierProfile).where(SupplierProfile.user_id == user_id))

    @staticmethod
    def get_by_id(db: Session, profile_id: uuid.UUID) -> Optional[SupplierProfile]:
        return db.scalar(select(SupplierProfile).where(SupplierProfile.id == profile_id))

    @staticmethod
    def list_all(db: Session, limit: int = 100) -> List[SupplierProfile]:
        return list(
            db.scalars(
                select(SupplierProfile)
                .order_by(SupplierProfile.organization_name)
                .limit(limit)
            ).all()
        )

    @staticmethod
    def create(
        db: Session,
        user_id: uuid.UUID,
        data: SupplierProfileCreate,
        verification_status: str = "PENDING_VERIFICATION",
    ) -> SupplierProfile:
        profile = SupplierProfile(
            user_id=user_id,
            organization_name=data.organization_name,
            contact_phone=data.contact_phone,
            address=data.address,
            state=data.state,
            district=data.district,
            city=data.city,
            latitude=data.latitude,
            longitude=data.longitude,
            facility_type=data.facility_type,
            operating_hours=data.operating_hours or {},
            storage_capabilities=data.storage_capabilities or {},
            description=data.description,
            verification_status=verification_status,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def update(db: Session, profile: SupplierProfile, data: SupplierProfileUpdate) -> SupplierProfile:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
        db.commit()
        db.refresh(profile)
        return profile


class ReceiverProfileRepository:
    @staticmethod
    def get_by_user_id(db: Session, user_id: uuid.UUID) -> Optional[ReceiverProfile]:
        return db.scalar(select(ReceiverProfile).where(ReceiverProfile.user_id == user_id))

    @staticmethod
    def get_by_id(db: Session, profile_id: uuid.UUID) -> Optional[ReceiverProfile]:
        return db.scalar(select(ReceiverProfile).where(ReceiverProfile.id == profile_id))

    @staticmethod
    def list_all(db: Session, limit: int = 100) -> List[ReceiverProfile]:
        return list(
            db.scalars(
                select(ReceiverProfile)
                .order_by(ReceiverProfile.organization_name)
                .limit(limit)
            ).all()
        )

    @staticmethod
    def create(
        db: Session,
        user_id: uuid.UUID,
        data: ReceiverProfileCreate,
        verification_status: str = "PENDING_VERIFICATION",
    ) -> ReceiverProfile:
        profile = ReceiverProfile(
            user_id=user_id,
            organization_name=data.organization_name,
            contact_phone=data.contact_phone,
            address=data.address,
            state=data.state,
            district=data.district,
            city=data.city,
            latitude=data.latitude,
            longitude=data.longitude,
            receiver_category=data.receiver_category,
            capacity_daily_kg=data.capacity_daily_kg,
            cold_storage_capabilities=data.cold_storage_capabilities or {"refrigeration": False, "freezer": False},
            dietary_handling_capabilities=data.dietary_handling_capabilities or [],
            operating_hours=data.operating_hours or {},
            priority_level=data.priority_level,
            description=data.description,
            verification_status=verification_status,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def update(db: Session, profile: ReceiverProfile, data: ReceiverProfileUpdate) -> ReceiverProfile:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
        db.commit()
        db.refresh(profile)
        return profile
