"""Add organization verification status and document columns

Revision ID: g13b01234567
Revises: f12a01234567
Create Date: 2026-11-01 22:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'g13b01234567'
down_revision: Union[str, Sequence[str], None] = 'f12a01234567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add verification_status to users
    op.add_column(
        'users',
        sa.Column('verification_status', sa.String(32), server_default='PENDING_VERIFICATION', nullable=False)
    )
    op.create_check_constraint(
        'ck_users_verification_status',
        'users',
        "verification_status IN ('PENDING_VERIFICATION', 'DOCUMENTS_SUBMITTED', 'VERIFIED', 'REJECTED')"
    )

    # 2. Add verification columns to supplier_profiles
    op.add_column('supplier_profiles', sa.Column('verification_status', sa.String(32), server_default='PENDING_VERIFICATION', nullable=False))
    op.add_column('supplier_profiles', sa.Column('license_number', sa.String(100), nullable=True))
    op.add_column('supplier_profiles', sa.Column('representative_name', sa.String(255), nullable=True))
    op.add_column('supplier_profiles', sa.Column('verification_document_path', sa.String(500), nullable=True))
    op.add_column('supplier_profiles', sa.Column('verification_document_name', sa.String(255), nullable=True))
    op.add_column('supplier_profiles', sa.Column('verification_submitted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('supplier_profiles', sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('supplier_profiles', sa.Column('verified_by_user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    op.add_column('supplier_profiles', sa.Column('rejection_reason', sa.Text(), nullable=True))
    op.create_check_constraint(
        'ck_supplier_verification_status',
        'supplier_profiles',
        "verification_status IN ('PENDING_VERIFICATION', 'DOCUMENTS_SUBMITTED', 'VERIFIED', 'REJECTED')"
    )

    # 3. Add verification columns to receiver_profiles
    op.add_column('receiver_profiles', sa.Column('verification_status', sa.String(32), server_default='PENDING_VERIFICATION', nullable=False))
    op.add_column('receiver_profiles', sa.Column('license_number', sa.String(100), nullable=True))
    op.add_column('receiver_profiles', sa.Column('representative_name', sa.String(255), nullable=True))
    op.add_column('receiver_profiles', sa.Column('verification_document_path', sa.String(500), nullable=True))
    op.add_column('receiver_profiles', sa.Column('verification_document_name', sa.String(255), nullable=True))
    op.add_column('receiver_profiles', sa.Column('verification_submitted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('receiver_profiles', sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('receiver_profiles', sa.Column('verified_by_user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    op.add_column('receiver_profiles', sa.Column('rejection_reason', sa.Text(), nullable=True))
    op.create_check_constraint(
        'ck_receiver_verification_status',
        'receiver_profiles',
        "verification_status IN ('PENDING_VERIFICATION', 'DOCUMENTS_SUBMITTED', 'VERIFIED', 'REJECTED')"
    )

    # 4. Migrate existing organizations to VERIFIED status so existing operational data remains valid
    op.execute("UPDATE users SET verification_status = 'VERIFIED', is_verified = TRUE")
    op.execute("UPDATE supplier_profiles SET verification_status = 'VERIFIED'")
    op.execute("UPDATE receiver_profiles SET verification_status = 'VERIFIED'")


def downgrade() -> None:
    op.drop_constraint('ck_receiver_verification_status', 'receiver_profiles', type_='check')
    op.drop_column('receiver_profiles', 'rejection_reason')
    op.drop_column('receiver_profiles', 'verified_by_user_id')
    op.drop_column('receiver_profiles', 'verified_at')
    op.drop_column('receiver_profiles', 'verification_submitted_at')
    op.drop_column('receiver_profiles', 'verification_document_name')
    op.drop_column('receiver_profiles', 'verification_document_path')
    op.drop_column('receiver_profiles', 'representative_name')
    op.drop_column('receiver_profiles', 'license_number')
    op.drop_column('receiver_profiles', 'verification_status')

    op.drop_constraint('ck_supplier_verification_status', 'supplier_profiles', type_='check')
    op.drop_column('supplier_profiles', 'rejection_reason')
    op.drop_column('supplier_profiles', 'verified_by_user_id')
    op.drop_column('supplier_profiles', 'verified_at')
    op.drop_column('supplier_profiles', 'verification_submitted_at')
    op.drop_column('supplier_profiles', 'verification_document_name')
    op.drop_column('supplier_profiles', 'verification_document_path')
    op.drop_column('supplier_profiles', 'representative_name')
    op.drop_column('supplier_profiles', 'license_number')
    op.drop_column('supplier_profiles', 'verification_status')

    op.drop_constraint('ck_users_verification_status', 'users', type_='check')
    op.drop_column('users', 'verification_status')
