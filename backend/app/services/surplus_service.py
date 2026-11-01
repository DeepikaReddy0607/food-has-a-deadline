import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.food import SurplusListing
from app.repositories.profile_repo import SupplierProfileRepository
from app.repositories.surplus_repo import SurplusRepository
from app.schemas.surplus import SurplusListingCreate, SurplusListingUpdate
from app.intelligence.perishability_engine import PerishabilityEngine
from app.intelligence.models import PerishabilityEvaluation, BatchEvaluationResponse


class SurplusService:
    @staticmethod
    def _get_verified_supplier_profile(db: Session, user: User):
        if user.role != "SUPPLIER" and user.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only registered suppliers can manage surplus inventory.",
            )
        profile = SupplierProfileRepository.get_by_user_id(db, user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supplier profile must be completed before listing surplus inventory.",
            )
        return profile

    @classmethod
    def create_listing(
        cls, db: Session, user: User, data: SurplusListingCreate
    ) -> SurplusListing:
        profile = cls._get_verified_supplier_profile(db, user)

        # Fallback to profile address if pickup_address not provided
        if not data.pickup_address or not data.pickup_address.strip():
            data.pickup_address = (
                f"{profile.address}, {profile.city}, {profile.district}, {profile.state}"
            )

        # Deterministically evaluate initial urgency classification
        evaluation = PerishabilityEngine.evaluate(
            estimated_deadline=data.estimated_deadline,
            harvest_or_prep_date=data.harvest_or_prep_date,
            food_condition=data.food_condition,
            storage_condition=data.storage_condition,
        )

        return SurplusRepository.create(
            db, profile.id, data, urgency_classification=evaluation.urgency
        )

    @classmethod
    def list_listings(
        cls,
        db: Session,
        user: User,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None,
        food_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        profile = cls._get_verified_supplier_profile(db, user)
        items, total = SurplusRepository.list_by_supplier(
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
    def get_listing(
        cls, db: Session, user: User, listing_id: uuid.UUID
    ) -> SurplusListing:
        profile = cls._get_verified_supplier_profile(db, user)
        listing = SurplusRepository.get_by_id(db, listing_id)
        if not listing or listing.supplier_id != profile.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surplus listing not found.",
            )
        return listing

    @classmethod
    def update_listing(
        cls, db: Session, user: User, listing_id: uuid.UUID, data: SurplusListingUpdate
    ) -> SurplusListing:
        listing = cls.get_listing(db, user, listing_id)

        if listing.status in ["CANCELLED", "DEPLETED", "EXPIRED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update listing with status '{listing.status}'.",
            )

        if data.remaining_quantity_kg is not None:
            if data.remaining_quantity_kg > listing.initial_quantity_kg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Remaining quantity cannot exceed initial quantity.",
                )
            if data.remaining_quantity_kg == 0:
                listing.status = "DEPLETED"
            elif listing.status == "DEPLETED" and data.remaining_quantity_kg > 0:
                listing.status = "ACTIVE"

        if data.estimated_deadline is not None:
            now = datetime.now(timezone.utc)
            dl = data.estimated_deadline
            if dl.tzinfo is None:
                dl = dl.replace(tzinfo=timezone.utc)
            if dl <= now:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Estimated usable deadline cannot be in the past.",
                )
            prep = listing.harvest_or_prep_date
            if prep.tzinfo is None:
                prep = prep.replace(tzinfo=timezone.utc)
            if dl <= prep:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Estimated deadline must be after harvest or preparation date.",
                )

        # Recalculate urgency classification if deadline, condition, or storage was modified
        new_deadline = data.estimated_deadline or listing.estimated_deadline
        new_condition = data.food_condition or listing.food_condition
        new_storage = data.storage_condition or listing.storage_condition

        evaluation = PerishabilityEngine.evaluate(
            estimated_deadline=new_deadline,
            harvest_or_prep_date=listing.harvest_or_prep_date,
            food_condition=new_condition,
            storage_condition=new_storage,
        )
        if listing.urgency_classification != evaluation.urgency:
            listing.urgency_classification = evaluation.urgency

        return SurplusRepository.update(db, listing, data)

    @classmethod
    def pause_listing(
        cls, db: Session, user: User, listing_id: uuid.UUID
    ) -> SurplusListing:
        listing = cls.get_listing(db, user, listing_id)
        if listing.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot pause listing with status '{listing.status}'. Only ACTIVE listings can be paused.",
            )
        listing.status = "PAUSED"
        return SurplusRepository.save(db, listing)

    @classmethod
    def resume_listing(
        cls, db: Session, user: User, listing_id: uuid.UUID
    ) -> SurplusListing:
        listing = cls.get_listing(db, user, listing_id)
        if listing.status != "PAUSED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot resume listing with status '{listing.status}'. Only PAUSED listings can be resumed.",
            )

        now = datetime.now(timezone.utc)
        dl = listing.estimated_deadline
        if dl.tzinfo is None:
            dl = dl.replace(tzinfo=timezone.utc)
        if dl <= now:
            listing.status = "EXPIRED"
            SurplusRepository.save(db, listing)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot resume listing: estimated usable deadline has already passed.",
            )

        if listing.remaining_quantity_kg <= 0:
            listing.status = "DEPLETED"
            SurplusRepository.save(db, listing)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot resume listing: remaining quantity is zero.",
            )

        # Recalculate urgency on resume
        eval_res = PerishabilityEngine.evaluate_listing(listing)
        listing.urgency_classification = eval_res.urgency
        listing.status = "ACTIVE"
        return SurplusRepository.save(db, listing)

    @classmethod
    def cancel_listing(
        cls, db: Session, user: User, listing_id: uuid.UUID
    ) -> SurplusListing:
        listing = cls.get_listing(db, user, listing_id)
        if listing.status == "CANCELLED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Listing is already cancelled.",
            )
        if listing.status in ["DEPLETED", "EXPIRED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel listing with status '{listing.status}'.",
            )
        listing.status = "CANCELLED"
        return SurplusRepository.save(db, listing)

    @classmethod
    def get_listing_perishability(
        cls,
        db: Session,
        user: User,
        listing_id: uuid.UUID,
        evaluation_time: Optional[datetime] = None,
    ) -> PerishabilityEvaluation:
        listing = SurplusRepository.get_by_id(db, listing_id)
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surplus listing not found.",
            )

        # Supplier can only access their own listings
        if user.role == "SUPPLIER":
            profile = SupplierProfileRepository.get_by_user_id(db, user.id)
            if not profile or listing.supplier_id != profile.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Surplus listing not found.",
                )
        elif user.role not in ["ADMIN", "COORDINATOR"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized to access perishability intelligence.",
            )

        # If stored urgency differs from current evaluation, update in DB
        eval_res = PerishabilityEngine.evaluate_listing(listing, evaluation_time=evaluation_time)
        if listing.urgency_classification != eval_res.urgency:
            listing.urgency_classification = eval_res.urgency
            db.commit()

        return eval_res

    @classmethod
    def batch_evaluate_active(
        cls,
        db: Session,
        user: User,
        evaluation_time: Optional[datetime] = None,
    ) -> BatchEvaluationResponse:
        if user.role == "SUPPLIER":
            profile = cls._get_verified_supplier_profile(db, user)
            active_items, _ = SurplusRepository.list_by_supplier(
                db, profile.id, page=1, page_size=500, status="ACTIVE"
            )
            paused_items, _ = SurplusRepository.list_by_supplier(
                db, profile.id, page=1, page_size=500, status="PAUSED"
            )
            all_items = active_items + paused_items
        elif user.role in ["ADMIN", "COORDINATOR"]:
            stmt = select(SurplusListing).where(SurplusListing.status.in_(["ACTIVE", "PAUSED"]))
            all_items = list(db.scalars(stmt).all())
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized to perform batch perishability evaluations.",
            )

        batch_res = PerishabilityEngine.batch_evaluate(all_items, evaluation_time=evaluation_time)

        # Synchronize database records if urgency changed
        updated = False
        for item, ev in zip(all_items, batch_res.items):
            if item.urgency_classification != ev.urgency:
                item.urgency_classification = ev.urgency
                updated = True
        if updated:
            db.commit()

        return batch_res
