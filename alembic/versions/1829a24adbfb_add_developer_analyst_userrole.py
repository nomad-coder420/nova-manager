"""add developer & analyst userrole

Revision ID: 1829a24adbfb
Revises: 2b489cdf6ff0
Create Date: 2025-08-15 08:53:19.166974

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1829a24adbfb'
down_revision: Union[str, Sequence[str], None] = '2b489cdf6ff0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'DEVELOPER'")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'ANALYST'")

def downgrade() -> None:
    raise RuntimeError("Downgrade not supported for userrole enum value additions")