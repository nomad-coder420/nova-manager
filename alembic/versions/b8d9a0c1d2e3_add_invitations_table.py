"""
Add invitations table

Revision ID: b8d9a0c1d2e3
Revises: a7c04eab34a2
Create Date: 2025-07-18 14:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b8d9a0c1d2e3'
down_revision = 'a7c04eab34a2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'invitations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('pid', sa.UUID(), nullable=False),
        sa.Column('target_type', sa.Enum('org', 'app', name='invitationtargettype', native_enum=False), nullable=False),
        sa.Column('target_id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'accepted', 'declined', name='invitationstatus', native_enum=False), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('pid'),
        sa.UniqueConstraint('token'),
    )
    op.create_index(op.f('ix_invitations_pid'), 'invitations', ['pid'], unique=True)
    op.create_index(op.f('ix_invitations_token'), 'invitations', ['token'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_invitations_token'), table_name='invitations')
    op.drop_index(op.f('ix_invitations_pid'), table_name='invitations')
    op.drop_table('invitations')
    # Drop ENUM types if needed
    op.execute("DROP TYPE invitationtargettype;")
    op.execute("DROP TYPE invitationstatus;")
