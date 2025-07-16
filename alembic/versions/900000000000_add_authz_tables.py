"""
Add organisations, apps and membership tables
"""
# revision identifiers, used by Alembic.
revision = '900000000000'
down_revision = 'f23b53e54d73'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # Organisations
    op.create_table(
        'organisations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('pid', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )
    # Apps
    op.create_table(
        'apps',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('pid', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('organisation_id', sa.String(), sa.ForeignKey('organisations.pid'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )
    # User-Organisation Membership
    op.create_table(
        'user_organisation_membership',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('pid', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('auth_user.id'), nullable=False),
        sa.Column('organisation_id', sa.String(), sa.ForeignKey('organisations.pid'), nullable=False),
        sa.Column('role', sa.Enum('owner','admin','member', name='organisationrole'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )
    # User-App Membership
    op.create_table(
        'user_app_membership',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('pid', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('auth_user.id'), nullable=False),
        sa.Column('app_id', sa.String(), sa.ForeignKey('apps.pid'), nullable=False),
        sa.Column('role', sa.Enum('admin','developer','analyst','viewer', name='approle'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('user_app_membership')
    op.drop_table('user_organisation_membership')
    op.drop_table('apps')
    op.drop_table('organisations')
