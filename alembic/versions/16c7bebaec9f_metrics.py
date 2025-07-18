"""metrics

Revision ID: 16c7bebaec9f
Revises: 5262968b533c
Create Date: 2025-07-19 07:36:30.042323

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16c7bebaec9f'
down_revision: Union[str, Sequence[str], None] = '5262968b533c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('metrics',
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=False),
    sa.Column('type', sa.String(), nullable=False),
    sa.Column('config', sa.JSON(), server_default=sa.text("json('{}')"), nullable=False),
    sa.Column('query', sa.String(), nullable=False),
    sa.Column('organisation_id', sa.String(), nullable=False),
    sa.Column('app_id', sa.String(), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('pid', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_metrics_name_org_app', 'metrics', ['name', 'organisation_id', 'app_id'], unique=False)
    op.create_index('idx_metrics_org_app', 'metrics', ['organisation_id', 'app_id'], unique=False)
    op.create_index(op.f('ix_metrics_id'), 'metrics', ['id'], unique=True)
    op.create_index(op.f('ix_metrics_pid'), 'metrics', ['pid'], unique=True)
    op.create_table('experience_metrics',
    sa.Column('experience_id', sa.UUID(), nullable=False),
    sa.Column('metric_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('pid', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['experience_id'], ['experiences.pid'], ),
    sa.ForeignKeyConstraint(['metric_id'], ['metrics.pid'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('experience_id', 'metric_id', name='uq_experience_metrics_exp_metric')
    )
    op.create_index(op.f('ix_experience_metrics_experience_id'), 'experience_metrics', ['experience_id'], unique=False)
    op.create_index(op.f('ix_experience_metrics_id'), 'experience_metrics', ['id'], unique=True)
    op.create_index(op.f('ix_experience_metrics_metric_id'), 'experience_metrics', ['metric_id'], unique=False)
    op.create_index(op.f('ix_experience_metrics_pid'), 'experience_metrics', ['pid'], unique=True)
    op.create_table('experience_segment_metrics',
    sa.Column('experience_segment_id', sa.UUID(), nullable=False),
    sa.Column('metric_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('pid', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['experience_segment_id'], ['experience_segments.pid'], ),
    sa.ForeignKeyConstraint(['metric_id'], ['metrics.pid'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('experience_segment_id', 'metric_id', name='uq_experience_segment_metrics_exp_seg_metric')
    )
    op.create_index(op.f('ix_experience_segment_metrics_experience_segment_id'), 'experience_segment_metrics', ['experience_segment_id'], unique=False)
    op.create_index(op.f('ix_experience_segment_metrics_id'), 'experience_segment_metrics', ['id'], unique=True)
    op.create_index(op.f('ix_experience_segment_metrics_metric_id'), 'experience_segment_metrics', ['metric_id'], unique=False)
    op.create_index(op.f('ix_experience_segment_metrics_pid'), 'experience_segment_metrics', ['pid'], unique=True)
    op.create_table('personalisation_metrics',
    sa.Column('personalisation_id', sa.UUID(), nullable=False),
    sa.Column('metric_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('pid', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['metric_id'], ['metrics.pid'], ),
    sa.ForeignKeyConstraint(['personalisation_id'], ['personalisations.pid'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('personalisation_id', 'metric_id', name='uq_personalisation_metrics_pers_metric')
    )
    op.create_index(op.f('ix_personalisation_metrics_id'), 'personalisation_metrics', ['id'], unique=True)
    op.create_index(op.f('ix_personalisation_metrics_metric_id'), 'personalisation_metrics', ['metric_id'], unique=False)
    op.create_index(op.f('ix_personalisation_metrics_personalisation_id'), 'personalisation_metrics', ['personalisation_id'], unique=False)
    op.create_index(op.f('ix_personalisation_metrics_pid'), 'personalisation_metrics', ['pid'], unique=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_personalisation_metrics_pid'), table_name='personalisation_metrics')
    op.drop_index(op.f('ix_personalisation_metrics_personalisation_id'), table_name='personalisation_metrics')
    op.drop_index(op.f('ix_personalisation_metrics_metric_id'), table_name='personalisation_metrics')
    op.drop_index(op.f('ix_personalisation_metrics_id'), table_name='personalisation_metrics')
    op.drop_table('personalisation_metrics')
    op.drop_index(op.f('ix_experience_segment_metrics_pid'), table_name='experience_segment_metrics')
    op.drop_index(op.f('ix_experience_segment_metrics_metric_id'), table_name='experience_segment_metrics')
    op.drop_index(op.f('ix_experience_segment_metrics_id'), table_name='experience_segment_metrics')
    op.drop_index(op.f('ix_experience_segment_metrics_experience_segment_id'), table_name='experience_segment_metrics')
    op.drop_table('experience_segment_metrics')
    op.drop_index(op.f('ix_experience_metrics_pid'), table_name='experience_metrics')
    op.drop_index(op.f('ix_experience_metrics_metric_id'), table_name='experience_metrics')
    op.drop_index(op.f('ix_experience_metrics_id'), table_name='experience_metrics')
    op.drop_index(op.f('ix_experience_metrics_experience_id'), table_name='experience_metrics')
    op.drop_table('experience_metrics')
    op.drop_index(op.f('ix_metrics_pid'), table_name='metrics')
    op.drop_index(op.f('ix_metrics_id'), table_name='metrics')
    op.drop_index('idx_metrics_org_app', table_name='metrics')
    op.drop_index('idx_metrics_name_org_app', table_name='metrics')
    op.drop_table('metrics')
    # ### end Alembic commands ###
