"""init

Revision ID: 44a43d2daa5b
Revises: 
Create Date: 2025-07-17 20:52:05.872979

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44a43d2daa5b'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('campaigns',
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), server_default='', nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('rule_config', sa.JSON(), server_default=sa.text("json('{}')"), nullable=False),
    sa.Column('launched_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('organisation_id', sa.String(), nullable=False),
    sa.Column('app_id', sa.String(), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('pid', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', 'organisation_id', 'app_id', name='uq_campaigns_name_org_app')
    )
    op.create_index('idx_campaigns_org_app', 'campaigns', ['organisation_id', 'app_id'], unique=False)
    op.create_index(op.f('ix_campaigns_id'), 'campaigns', ['id'], unique=True)
    op.create_index(op.f('ix_campaigns_pid'), 'campaigns', ['pid'], unique=True)
    op.create_table('experiences',
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), server_default='', nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('organisation_id', sa.String(), nullable=False),
    sa.Column('app_id', sa.String(), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('pid', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', 'organisation_id', 'app_id', name='uq_experiences_name_org_app')
    )
    op.create_index('idx_experiences_name_org_app', 'experiences', ['name', 'organisation_id', 'app_id'], unique=False)
    op.create_index('idx_experiences_org_app', 'experiences', ['organisation_id', 'app_id'], unique=False)
    op.create_index('idx_experiences_status_org_app', 'experiences', ['status', 'organisation_id', 'app_id'], unique=False)
    op.create_index(op.f('ix_experiences_id'), 'experiences', ['id'], unique=True)
    op.create_index(op.f('ix_experiences_pid'), 'experiences', ['pid'], unique=True)
    op.create_table('segments',
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), server_default='', nullable=False),
    sa.Column('rule_config', sa.JSON(), server_default=sa.text("json('{}')"), nullable=False),
    sa.Column('organisation_id', sa.String(), nullable=False),
    sa.Column('app_id', sa.String(), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('pid', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', 'organisation_id', 'app_id', name='uq_segments_name_org_app')
    )
    op.create_index('idx_segments_org_app', 'segments', ['organisation_id', 'app_id'], unique=False)
    op.create_index(op.f('ix_segments_id'), 'segments', ['id'], unique=True)
    op.create_index(op.f('ix_segments_pid'), 'segments', ['pid'], unique=True)
    op.create_table('users',
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('user_profile', sa.JSON(), server_default=sa.text("json('{}')"), nullable=False),
    sa.Column('organisation_id', sa.String(), nullable=False),
    sa.Column('app_id', sa.String(), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('pid', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'organisation_id', 'app_id', name='uq_users_user_id_org_app')
    )
    op.create_index('idx_users_org_app', 'users', ['organisation_id', 'app_id'], unique=False)
    op.create_index('idx_users_user_id_org_app', 'users', ['user_id', 'organisation_id', 'app_id'], unique=False)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=True)
    op.create_index(op.f('ix_users_pid'), 'users', ['pid'], unique=True)
    op.create_table('experience_segments',
    sa.Column('experience_id', sa.UUID(), nullable=False),
    sa.Column('segment_id', sa.UUID(), nullable=False),
    sa.Column('target_percentage', sa.Integer(), nullable=False),
    sa.Column('priority', sa.Integer(), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('pid', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('target_percentage >= 0 AND target_percentage <= 100', name='ck_experience_segments_valid_percentage'),
    sa.ForeignKeyConstraint(['experience_id'], ['experiences.pid'], ),
    sa.ForeignKeyConstraint(['segment_id'], ['segments.pid'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('experience_id', 'segment_id', name='uq_experience_segments_exp_seg')
    )
    op.create_index('idx_experience_segments_experience_id', 'experience_segments', ['experience_id'], unique=False)
    op.create_index('idx_experience_segments_priority', 'experience_segments', ['priority'], unique=False)
    op.create_index('idx_experience_segments_segment_id', 'experience_segments', ['segment_id'], unique=False)
    op.create_index(op.f('ix_experience_segments_id'), 'experience_segments', ['id'], unique=True)
    op.create_index(op.f('ix_experience_segments_pid'), 'experience_segments', ['pid'], unique=True)
    op.create_table('feature_flags',
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), server_default='', nullable=False),
    sa.Column('keys_config', sa.JSON(), server_default=sa.text("json('{}')"), nullable=False),
    sa.Column('type', sa.String(), server_default='', nullable=False),
    sa.Column('experience_id', sa.UUID(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('organisation_id', sa.String(), nullable=False),
    sa.Column('app_id', sa.String(), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('pid', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['experience_id'], ['experiences.pid'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', 'organisation_id', 'app_id', name='uq_feature_flags_name_org_app')
    )
    op.create_index('idx_feature_flags_active_org_app', 'feature_flags', ['is_active', 'organisation_id', 'app_id'], unique=False)
    op.create_index('idx_feature_flags_org_app', 'feature_flags', ['organisation_id', 'app_id'], unique=False)
    op.create_index(op.f('ix_feature_flags_id'), 'feature_flags', ['id'], unique=True)
    op.create_index(op.f('ix_feature_flags_pid'), 'feature_flags', ['pid'], unique=True)
    op.create_table('personalisations',
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), server_default='', nullable=False),
    sa.Column('experience_id', sa.UUID(), nullable=False),
    sa.Column('is_default', sa.Boolean(), nullable=False),
    sa.Column('last_updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('pid', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['experience_id'], ['experiences.pid'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', 'experience_id', name='uq_personalisations_name_exp')
    )
    op.create_index('idx_personalisations_experience_id', 'personalisations', ['experience_id'], unique=False)
    op.create_index(op.f('ix_personalisations_id'), 'personalisations', ['id'], unique=True)
    op.create_index(op.f('ix_personalisations_pid'), 'personalisations', ['pid'], unique=True)
    op.create_table('experience_segment_personalisations',
    sa.Column('experience_segment_id', sa.UUID(), nullable=False),
    sa.Column('personalisation_id', sa.UUID(), nullable=False),
    sa.Column('target_percentage', sa.Integer(), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('pid', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['experience_segment_id'], ['experience_segments.pid'], ),
    sa.ForeignKeyConstraint(['personalisation_id'], ['personalisations.pid'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_experience_segment_personalisations_experience_segment_id'), 'experience_segment_personalisations', ['experience_segment_id'], unique=False)
    op.create_index(op.f('ix_experience_segment_personalisations_id'), 'experience_segment_personalisations', ['id'], unique=True)
    op.create_index(op.f('ix_experience_segment_personalisations_personalisation_id'), 'experience_segment_personalisations', ['personalisation_id'], unique=False)
    op.create_index(op.f('ix_experience_segment_personalisations_pid'), 'experience_segment_personalisations', ['pid'], unique=True)
    op.create_table('feature_variants',
    sa.Column('feature_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('config', sa.JSON(), server_default=sa.text("json('{}')"), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('pid', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['feature_id'], ['feature_flags.pid'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', 'feature_id', name='uq_feature_variants_name_feature')
    )
    op.create_index('idx_feature_variants_feature_id', 'feature_variants', ['feature_id'], unique=False)
    op.create_index(op.f('ix_feature_variants_id'), 'feature_variants', ['id'], unique=True)
    op.create_index(op.f('ix_feature_variants_pid'), 'feature_variants', ['pid'], unique=True)
    op.create_table('feature_variants_templates',
    sa.Column('feature_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('config', sa.JSON(), server_default=sa.text("json('{}')"), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('pid', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['feature_id'], ['feature_flags.pid'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', 'feature_id', name='uq_feature_variants_templates_name_feature')
    )
    op.create_index('idx_feature_variants_templates_feature_id', 'feature_variants_templates', ['feature_id'], unique=False)
    op.create_index(op.f('ix_feature_variants_templates_id'), 'feature_variants_templates', ['id'], unique=True)
    op.create_index(op.f('ix_feature_variants_templates_pid'), 'feature_variants_templates', ['pid'], unique=True)
    op.create_table('user_experience_personalisation',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('experience_id', sa.UUID(), nullable=False),
    sa.Column('personalisation_id', sa.UUID(), nullable=True),
    sa.Column('segment_id', sa.UUID(), nullable=True),
    sa.Column('experience_segment_personalisation_id', sa.UUID(), nullable=True),
    sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('evaluation_reason', sa.String(), nullable=False),
    sa.Column('organisation_id', sa.String(), nullable=False),
    sa.Column('app_id', sa.String(), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('pid', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['experience_id'], ['experiences.pid'], ),
    sa.ForeignKeyConstraint(['personalisation_id'], ['personalisations.pid'], ),
    sa.ForeignKeyConstraint(['segment_id'], ['segments.pid'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.pid'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'experience_id', 'organisation_id', 'app_id', name='uq_user_experience_user_exp_org_app')
    )
    op.create_index('idx_user_experience_assigned_org_app', 'user_experience_personalisation', ['assigned_at', 'organisation_id', 'app_id'], unique=False)
    op.create_index('idx_user_experience_experience_org_app', 'user_experience_personalisation', ['experience_id', 'organisation_id', 'app_id'], unique=False)
    op.create_index('idx_user_experience_main_query', 'user_experience_personalisation', ['user_id', 'organisation_id', 'app_id', 'experience_id'], unique=False)
    op.create_index('idx_user_experience_user_assigned', 'user_experience_personalisation', ['user_id', 'assigned_at'], unique=False)
    op.create_index(op.f('ix_user_experience_personalisation_id'), 'user_experience_personalisation', ['id'], unique=True)
    op.create_index(op.f('ix_user_experience_personalisation_pid'), 'user_experience_personalisation', ['pid'], unique=True)
    op.create_table('personalisation_feature_variants',
    sa.Column('personalisation_id', sa.UUID(), nullable=False),
    sa.Column('feature_variant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('pid', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['feature_variant_id'], ['feature_variants.pid'], ),
    sa.ForeignKeyConstraint(['personalisation_id'], ['personalisations.pid'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_personalisation_feature_variants_id'), 'personalisation_feature_variants', ['id'], unique=True)
    op.create_index(op.f('ix_personalisation_feature_variants_pid'), 'personalisation_feature_variants', ['pid'], unique=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_personalisation_feature_variants_pid'), table_name='personalisation_feature_variants')
    op.drop_index(op.f('ix_personalisation_feature_variants_id'), table_name='personalisation_feature_variants')
    op.drop_table('personalisation_feature_variants')
    op.drop_index(op.f('ix_user_experience_personalisation_pid'), table_name='user_experience_personalisation')
    op.drop_index(op.f('ix_user_experience_personalisation_id'), table_name='user_experience_personalisation')
    op.drop_index('idx_user_experience_user_assigned', table_name='user_experience_personalisation')
    op.drop_index('idx_user_experience_main_query', table_name='user_experience_personalisation')
    op.drop_index('idx_user_experience_experience_org_app', table_name='user_experience_personalisation')
    op.drop_index('idx_user_experience_assigned_org_app', table_name='user_experience_personalisation')
    op.drop_table('user_experience_personalisation')
    op.drop_index(op.f('ix_feature_variants_templates_pid'), table_name='feature_variants_templates')
    op.drop_index(op.f('ix_feature_variants_templates_id'), table_name='feature_variants_templates')
    op.drop_index('idx_feature_variants_templates_feature_id', table_name='feature_variants_templates')
    op.drop_table('feature_variants_templates')
    op.drop_index(op.f('ix_feature_variants_pid'), table_name='feature_variants')
    op.drop_index(op.f('ix_feature_variants_id'), table_name='feature_variants')
    op.drop_index('idx_feature_variants_feature_id', table_name='feature_variants')
    op.drop_table('feature_variants')
    op.drop_index(op.f('ix_experience_segment_personalisations_pid'), table_name='experience_segment_personalisations')
    op.drop_index(op.f('ix_experience_segment_personalisations_personalisation_id'), table_name='experience_segment_personalisations')
    op.drop_index(op.f('ix_experience_segment_personalisations_id'), table_name='experience_segment_personalisations')
    op.drop_index(op.f('ix_experience_segment_personalisations_experience_segment_id'), table_name='experience_segment_personalisations')
    op.drop_table('experience_segment_personalisations')
    op.drop_index(op.f('ix_personalisations_pid'), table_name='personalisations')
    op.drop_index(op.f('ix_personalisations_id'), table_name='personalisations')
    op.drop_index('idx_personalisations_experience_id', table_name='personalisations')
    op.drop_table('personalisations')
    op.drop_index(op.f('ix_feature_flags_pid'), table_name='feature_flags')
    op.drop_index(op.f('ix_feature_flags_id'), table_name='feature_flags')
    op.drop_index('idx_feature_flags_org_app', table_name='feature_flags')
    op.drop_index('idx_feature_flags_active_org_app', table_name='feature_flags')
    op.drop_table('feature_flags')
    op.drop_index(op.f('ix_experience_segments_pid'), table_name='experience_segments')
    op.drop_index(op.f('ix_experience_segments_id'), table_name='experience_segments')
    op.drop_index('idx_experience_segments_segment_id', table_name='experience_segments')
    op.drop_index('idx_experience_segments_priority', table_name='experience_segments')
    op.drop_index('idx_experience_segments_experience_id', table_name='experience_segments')
    op.drop_table('experience_segments')
    op.drop_index(op.f('ix_users_pid'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index('idx_users_user_id_org_app', table_name='users')
    op.drop_index('idx_users_org_app', table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_segments_pid'), table_name='segments')
    op.drop_index(op.f('ix_segments_id'), table_name='segments')
    op.drop_index('idx_segments_org_app', table_name='segments')
    op.drop_table('segments')
    op.drop_index(op.f('ix_experiences_pid'), table_name='experiences')
    op.drop_index(op.f('ix_experiences_id'), table_name='experiences')
    op.drop_index('idx_experiences_status_org_app', table_name='experiences')
    op.drop_index('idx_experiences_org_app', table_name='experiences')
    op.drop_index('idx_experiences_name_org_app', table_name='experiences')
    op.drop_table('experiences')
    op.drop_index(op.f('ix_campaigns_pid'), table_name='campaigns')
    op.drop_index(op.f('ix_campaigns_id'), table_name='campaigns')
    op.drop_index('idx_campaigns_org_app', table_name='campaigns')
    op.drop_table('campaigns')
    # ### end Alembic commands ###
