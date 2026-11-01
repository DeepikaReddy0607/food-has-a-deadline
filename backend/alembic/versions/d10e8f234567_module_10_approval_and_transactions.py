"""Update allocation proposal rejection reason and status constraints for Module 10

Revision ID: d10e8f234567
Revises: c987a123f456
Create Date: 2026-11-01 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd10e8f234567'
down_revision: Union[str, None] = 'c987a123f456'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add rejection_reason column to allocation_proposals
    op.add_column('allocation_proposals', sa.Column('rejection_reason', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('allocation_proposals', 'rejection_reason')
