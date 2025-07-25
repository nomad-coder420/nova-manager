"""events_schema

Revision ID: cc00f8f5f444
Revises: ad43f07058e3
Create Date: 2025-07-23 18:50:26.475922

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc00f8f5f444'
down_revision: Union[str, Sequence[str], None] = 'ad43f07058e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('events_schema',
    sa.Column('event_name', sa.String(), nullable=False),
    sa.Column('event_schema', sa.JSON(), server_default=sa.text("json('{}')"), nullable=False),
    sa.Column('organisation_id', sa.String(), nullable=False),
    sa.Column('app_id', sa.String(), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('pid', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('event_name', 'organisation_id', 'app_id', name='uq_events_schema_event_name_org_app')
    )
    op.create_index('idx_events_schema_event_name_org_app', 'events_schema', ['event_name', 'organisation_id', 'app_id'], unique=False)
    op.create_index(op.f('ix_events_schema_id'), 'events_schema', ['id'], unique=True)
    op.create_index(op.f('ix_events_schema_pid'), 'events_schema', ['pid'], unique=True)
    op.add_column('user_experience', sa.Column('experience_variant_id', sa.UUID(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user_experience', 'experience_variant_id')
    op.drop_index(op.f('ix_events_schema_pid'), table_name='events_schema')
    op.drop_index(op.f('ix_events_schema_id'), table_name='events_schema')
    op.drop_index('idx_events_schema_event_name_org_app', table_name='events_schema')
    op.drop_table('events_schema')
    # ### end Alembic commands ###
