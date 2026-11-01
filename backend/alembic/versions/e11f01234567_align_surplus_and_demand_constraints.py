"""Align surplus and demand check constraints with SQLAlchemy models

Revision ID: e11f01234567
Revises: d10e8f234567
Create Date: 2026-11-01 12:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'e11f01234567'
down_revision: Union[str, Sequence[str], None] = 'd10e8f234567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update SurplusListing constraints
    op.drop_constraint('ck_surplus_food_condition', 'surplus_listings', type_='check')
    op.create_check_constraint(
        'ck_surplus_food_condition',
        'surplus_listings',
        "food_condition IN ('EXCELLENT', 'GOOD', 'FAIR', 'RIPE', 'IMMINENT_DECAY', 'IMPERFECT')",
    )

    op.drop_constraint('ck_surplus_status', 'surplus_listings', type_='check')
    op.create_check_constraint(
        'ck_surplus_status',
        'surplus_listings',
        "status IN ('ACTIVE', 'PAUSED', 'DEPLETED', 'EXPIRED', 'CANCELLED', 'AVAILABLE', 'ALLOCATING', 'EXHAUSTED')",
    )

    op.drop_constraint('ck_surplus_urgency', 'surplus_listings', type_='check')
    op.create_check_constraint(
        'ck_surplus_urgency',
        'surplus_listings',
        "urgency_classification IN ('CRITICAL', 'HIGH', 'MODERATE', 'LOW', 'PENDING')",
    )

    # 2. Update DemandRequest constraints
    op.drop_constraint('ck_demand_status', 'demand_requests', type_='check')
    op.create_check_constraint(
        'ck_demand_status',
        'demand_requests',
        "status IN ('ACTIVE', 'OPEN', 'PARTIALLY_FULFILLED', 'FULFILLED', 'EXPIRED', 'CANCELLED')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_demand_status', 'demand_requests', type_='check')
    op.create_check_constraint(
        'ck_demand_status',
        'demand_requests',
        "status IN ('ACTIVE', 'PARTIALLY_FULFILLED', 'FULFILLED', 'EXPIRED', 'CANCELLED')",
    )

    op.drop_constraint('ck_surplus_urgency', 'surplus_listings', type_='check')
    op.create_check_constraint(
        'ck_surplus_urgency',
        'surplus_listings',
        "urgency_classification IN ('CRITICAL', 'HIGH', 'MODERATE', 'LOW')",
    )

    op.drop_constraint('ck_surplus_status', 'surplus_listings', type_='check')
    op.create_check_constraint(
        'ck_surplus_status',
        'surplus_listings',
        "status IN ('AVAILABLE', 'ALLOCATING', 'EXHAUSTED', 'EXPIRED', 'CANCELLED')",
    )

    op.drop_constraint('ck_surplus_food_condition', 'surplus_listings', type_='check')
    op.create_check_constraint(
        'ck_surplus_food_condition',
        'surplus_listings',
        "food_condition IN ('EXCELLENT', 'RIPE', 'IMMINENT_DECAY', 'IMPERFECT')",
    )
