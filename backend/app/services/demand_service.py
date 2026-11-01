import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.food import DemandRequest
from app.repositories.profile_repo import ReceiverProfileRepository
from app.repositories.demand_repo import DemandRepository
from app.schemas.demand import DemandRequestCreate, DemandRequestUpdate


class DemandService:
    @staticmethod
    def _get_verified_receiver_profile(db: Session, user: User):
        if user.role != "RECEIVER" and user.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only registered receivers can manage food demand requests.",
            )
        profile = ReceiverProfileRepository.get_by_user_id(db, user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Receiver profile must be completed before creating food demand requests.",
            )
        return profile

    @classmethod
    def create_demand(
        cls, db: Session, user: User, data: DemandRequestCreate
    ) -> DemandRequest:
        profile = cls._get_verified_receiver_profile(db, user)

        # Fallback to receiver profile address if delivery_address is empty
        if not data.delivery_address or not data.delivery_address.strip():
            data.delivery_address = (
                f"{profile.address}, {profile.city}, {profile.district}, {profile.state}"
            )

        return DemandRepository.create(db, profile.id, data)

    @classmethod
    def list_demands(
        cls,
        db: Session,
        user: User,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None,
        food_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        profile = cls._get_verified_receiver_profile(db, user)
        items, total = DemandRepository.list_by_receiver(
            db,
            profile.id,
            page=page,
            page_size=page_size,
            status=status_filter,
            food_category=food_category,
        )
        pages = (total + page_size - 1) // page_size if total > 0 else 1
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        }

    @classmethod
    def get_demand(
        cls, db: Session, user: User, demand_id: uuid.UUID
    ) -> DemandRequest:
        profile = cls._get_verified_receiver_profile(db, user)
        demand = DemandRepository.get_by_id(db, demand_id)
        if not demand or demand.receiver_id != profile.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Demand request not found.",
            )
        return demand

    @classmethod
    def update_demand(
        cls, db: Session, user: User, demand_id: uuid.UUID, data: DemandRequestUpdate
    ) -> DemandRequest:
        demand = cls.get_demand(db, user, demand_id)

        if demand.status in ["CANCELLED", "FULFILLED", "EXPIRED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update demand request with status '{demand.status}'.",
            )

        if data.requested_quantity_kg is not None:
            if data.requested_quantity_kg < demand.fulfilled_quantity_kg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Requested quantity cannot be less than already fulfilled quantity.",
                )
            if data.requested_quantity_kg == demand.fulfilled_quantity_kg:
                demand.status = "FULFILLED"
            elif demand.status == "FULFILLED" and data.requested_quantity_kg > demand.fulfilled_quantity_kg:
                demand.status = (
                    "PARTIALLY_FULFILLED" if demand.fulfilled_quantity_kg > 0 else "OPEN"
                )

        if data.required_by is not None:
            now = datetime.now(timezone.utc)
            rb = data.required_by
            if rb.tzinfo is None:
                rb = rb.replace(tzinfo=timezone.utc)
            if rb <= now:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Required-by deadline cannot be in the past.",
                )

        return DemandRepository.update(db, demand, data)

    @classmethod
    def pause_demand(
        cls, db: Session, user: User, demand_id: uuid.UUID
    ) -> DemandRequest:
        demand = cls.get_demand(db, user, demand_id)
        if demand.status not in ["OPEN", "PARTIALLY_FULFILLED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot pause demand request with status '{demand.status}'. Only OPEN or PARTIALLY_FULFILLED requests can be paused.",
            )
        demand.status = "PAUSED"
        return DemandRepository.save(db, demand)

    @classmethod
    def resume_demand(
        cls, db: Session, user: User, demand_id: uuid.UUID
    ) -> DemandRequest:
        demand = cls.get_demand(db, user, demand_id)
        if demand.status != "PAUSED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot resume demand request with status '{demand.status}'. Only PAUSED requests can be resumed.",
            )

        now = datetime.now(timezone.utc)
        rb = demand.required_by
        if rb.tzinfo is None:
            rb = rb.replace(tzinfo=timezone.utc)
        if rb <= now:
            demand.status = "EXPIRED"
            DemandRepository.save(db, demand)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot resume demand request: required-by deadline has already passed.",
            )

        if demand.fulfilled_quantity_kg >= demand.requested_quantity_kg:
            demand.status = "FULFILLED"
            DemandRepository.save(db, demand)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot resume demand request: requirement is already completely fulfilled.",
            )

        demand.status = (
            "PARTIALLY_FULFILLED" if demand.fulfilled_quantity_kg > 0 else "OPEN"
        )
        return DemandRepository.save(db, demand)

    @classmethod
    def cancel_demand(
        cls, db: Session, user: User, demand_id: uuid.UUID
    ) -> DemandRequest:
        demand = cls.get_demand(db, user, demand_id)
        if demand.status == "CANCELLED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Demand request is already cancelled.",
            )
        if demand.status in ["FULFILLED", "EXPIRED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel demand request with status '{demand.status}'.",
            )
        demand.status = "CANCELLED"
        return DemandRepository.save(db, demand)
