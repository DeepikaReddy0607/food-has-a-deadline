"""Update transaction and proposal status constraints for Module 10 and 11

Revision ID: f12a01234567
Revises: e11f01234567
Create Date: 2026-11-01 12:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'f12a01234567'
down_revision: Union[str, Sequence[str], None] = 'e11f01234567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update RedistributionTransaction status check constraint
    op.drop_constraint('ck_tx_status', 'redistribution_transactions', type_='check')
    op.create_check_constraint(
        'ck_tx_status',
        'redistribution_transactions',
        "status IN ('APPROVED', 'SCHEDULED', 'PICKUP_SCHEDULED', 'DISPATCHED', 'PICKED_UP', 'IN_TRANSIT', 'DELIVERED', 'COMPLETED', 'FAILED', 'CANCELLED')",
    )

    # 2. Update AllocationProposal status check constraint
    op.drop_constraint('ck_proposals_status', 'allocation_proposals', type_='check')
    op.create_check_constraint(
        'ck_proposals_status',
        'allocation_proposals',
        "status IN ('PENDING_REVIEW', 'APPROVED', 'ACCEPTED', 'EXECUTING', 'COMPLETED', 'REJECTED', 'CANCELLED', 'FAILED', 'SUPERSEDED')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_proposals_status', 'allocation_proposals', type_='check')
    op.create_check_constraint(
        'ck_proposals_status',
        'allocation_proposals',
        "status IN ('PENDING_REVIEW', 'ACCEPTED', 'REJECTED', 'SUPERSEDED')",
    )

    op.drop_constraint('ck_tx_status', 'redistribution_transactions', type_='check')
    op.create_check_constraint(
        'ck_tx_status',
        'redistribution_transactions',
        "status IN ('SCHEDULED', 'DISPATCHED', 'IN_TRANSIT', 'DELIVERED', 'FAILED', 'CANCELLED')",
    )
