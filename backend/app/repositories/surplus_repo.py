import uuid
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.food import SurplusListing
from app.schemas.surplus import SurplusListingCreate, SurplusListingUpdate


class SurplusRepository:
    @staticmethod
    def get_by_id(db: Session, listing_id: uuid.UUID) -> Optional[SurplusListing]:
        return db.scalar(select(SurplusListing).where(SurplusListing.id == listing_id))

    @staticmethod
    def list_by_supplier(
        db: Session,
        supplier_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        food_category: Optional[str] = None,
    ) -> Tuple[List[SurplusListing], int]:
        stmt = select(SurplusListing).where(SurplusListing.supplier_id == supplier_id)
        count_stmt = select(func.count(SurplusListing.id)).where(SurplusListing.supplier_id == supplier_id)

        if status:
            stmt = stmt.where(SurplusListing.status == status.upper())
            count_stmt = count_stmt.where(SurplusListing.status == status.upper())

        if food_category:
            stmt = stmt.where(SurplusListing.food_category == food_category.upper())
            count_stmt = count_stmt.where(SurplusListing.food_category == food_category.upper())

        total = db.scalar(count_stmt) or 0
        offset = (page - 1) * page_size
        items = list(
            db.scalars(
                stmt.order_by(SurplusListing.created_at.desc()).offset(offset).limit(page_size)
            ).all()
        )
        return items, total

    @staticmethod
    def create(
        db: Session,
        supplier_id: uuid.UUID,
        data: SurplusListingCreate,
        urgency_classification: str = "PENDING",
    ) -> SurplusListing:
        listing = SurplusListing(
            supplier_id=supplier_id,
            food_category=data.food_category,
            item_name=data.item_name,
            description=data.description,
            initial_quantity_kg=data.initial_quantity_kg,
            remaining_quantity_kg=data.initial_quantity_kg,
            storage_condition=data.storage_condition,
            food_condition=data.food_condition,
            harvest_or_prep_date=data.harvest_or_prep_date,
            preparation_date=data.preparation_date,
            estimated_deadline=data.estimated_deadline,
            pickup_address=data.pickup_address,
            handling_instructions=data.handling_instructions,
            urgency_classification=urgency_classification,
            status="ACTIVE",
        )
        db.add(listing)
        db.commit()
        db.refresh(listing)
        return listing

    @staticmethod
    def update(db: Session, listing: SurplusListing, data: SurplusListingUpdate) -> SurplusListing:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(listing, field, value)
        db.commit()
        db.refresh(listing)
        return listing

    @staticmethod
    def save(db: Session, listing: SurplusListing) -> SurplusListing:
        db.commit()
        db.refresh(listing)
        return listing
