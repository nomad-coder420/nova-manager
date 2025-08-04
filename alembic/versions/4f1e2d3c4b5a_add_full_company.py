"""add full_name and company_name to auth_user table

Revision ID: 4f1e2d3c4b5a
Revises: 3dbe5b69aff0
Create Date: 2025-07-22 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4f1e2d3c4b5a'
down_revision = '3dbe5b69aff0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user full name and company name
    op.add_column('auth_user', sa.Column('full_name', sa.String(length=100), nullable=False, server_default=''))
    op.add_column('auth_user', sa.Column('company_name', sa.String(length=100), nullable=False, server_default=''))
    # Remove server defaults for future inserts
    op.alter_column('auth_user', 'full_name', server_default=None)
    op.alter_column('auth_user', 'company_name', server_default=None)


def downgrade() -> None:
    # Drop the added columns
    op.drop_column('auth_user', 'company_name')
    op.drop_column('auth_user', 'full_name')
