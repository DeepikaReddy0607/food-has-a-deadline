import uuid
from decimal import Decimal
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.food import DemandRequest
from app.schemas.demand import DemandRequestCreate, DemandRequestUpdate


class DemandRepository:
    @staticmethod
    def get_by_id(db: Session, demand_id: uuid.UUID) -> Optional[DemandRequest]:
        return db.scalar(select(DemandRequest).where(DemandRequest.id == demand_id))

    @staticmethod
    def list_by_receiver(
        db: Session,
        receiver_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        food_category: Optional[str] = None,
    ) -> Tuple[List[DemandRequest], int]:
        stmt = select(DemandRequest).where(DemandRequest.receiver_id == receiver_id)
        count_stmt = select(func.count(DemandRequest.id)).where(DemandRequest.receiver_id == receiver_id)

        if status:
            stmt = stmt.where(DemandRequest.status == status.upper())
            count_stmt = count_stmt.where(DemandRequest.status == status.upper())

        if food_category:
            stmt = stmt.where(DemandRequest.food_category == food_category.upper())
            count_stmt = count_stmt.where(DemandRequest.food_category == food_category.upper())

        total = db.scalar(count_stmt) or 0
        offset = (page - 1) * page_size
        items = list(
            db.scalars(
                stmt.order_by(DemandRequest.created_at.desc()).offset(offset).limit(page_size)
            ).all()
        )
        return items, total

    @staticmethod
    def create(db: Session, receiver_id: uuid.UUID, data: DemandRequestCreate) -> DemandRequest:
        demand = DemandRequest(
            receiver_id=receiver_id,
            food_category=data.food_category,
            item_name=data.item_name,
            description=data.description,
            requested_quantity_kg=data.requested_quantity_kg,
            fulfilled_quantity_kg=Decimal("0.00"),
            acceptable_food_condition=data.acceptable_food_condition,
            dietary_requirements=data.dietary_requirements or [],
            storage_capability=data.storage_capability,
            delivery_address=data.delivery_address,
            handling_instructions=data.handling_instructions,
            required_by=data.required_by,
            priority_weight=data.priority_weight,
            status="OPEN",
        )
        db.add(demand)
        db.commit()
        db.refresh(demand)
        return demand

    @staticmethod
    def update(db: Session, demand: DemandRequest, data: DemandRequestUpdate) -> DemandRequest:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(demand, field, value)
        db.commit()
        db.refresh(demand)
        return demand

    @staticmethod
    def save(db: Session, demand: DemandRequest) -> DemandRequest:
        db.commit()
        db.refresh(demand)
        return demand
