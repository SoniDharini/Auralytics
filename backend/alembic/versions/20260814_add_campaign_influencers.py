"""add campaign_influencers join table, campaign discovery criteria and creator metric provenance

Revision ID: 20260814_add_campaign_influencers
Revises: 20260814_update_influencers
Create Date: 2026-08-14 16:45:00.000000

Additive only: no existing table is dropped or recreated, so users, campaigns and
authentication records are preserved.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import app.db.custom_types


# revision identifiers, used by Alembic.
revision: str = '20260814_add_camp_infl'
down_revision: Union[str, None] = '20260814_update_influencers'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Campaign-level creator discovery criteria
    with op.batch_alter_table('campaigns', schema=None) as batch_op:
        batch_op.add_column(sa.Column('keywords', app.db.custom_types.JSON_COMPAT(), nullable=True))
        batch_op.add_column(sa.Column('min_followers', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('max_followers', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('last_discovery_at', sa.DateTime(timezone=True), nullable=True))

    # 2. Creator metric provenance and contact verification flag
    with op.batch_alter_table('influencers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_upload_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('metrics_sample_size', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('metrics_source', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('email_verified', sa.Boolean(), server_default=sa.false(), nullable=False))

    # 3. Campaign <-> influencer relationship
    op.create_table(
        'campaign_influencers',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('campaign_id', sa.String(length=64), nullable=False),
        sa.Column('influencer_id', sa.String(length=64), nullable=False),
        sa.Column('match_score', sa.Float(), nullable=True),
        sa.Column('match_reasons', app.db.custom_types.JSON_COMPAT(), nullable=True),
        sa.Column('discovery_query', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='DISCOVERED', nullable=False),
        sa.Column('discovered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['influencer_id'], ['influencers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('campaign_id', 'influencer_id', name='uq_campaign_influencer'),
    )
    op.create_index(op.f('ix_campaign_influencers_id'), 'campaign_influencers', ['id'], unique=False)
    op.create_index(op.f('ix_campaign_influencers_campaign_id'), 'campaign_influencers', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_campaign_influencers_influencer_id'), 'campaign_influencers', ['influencer_id'], unique=False)
    op.create_index(op.f('ix_campaign_influencers_status'), 'campaign_influencers', ['status'], unique=False)
    op.create_index(
        'ix_campaign_influencers_campaign_status',
        'campaign_influencers',
        ['campaign_id', 'status'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_campaign_influencers_campaign_status', table_name='campaign_influencers')
    op.drop_index(op.f('ix_campaign_influencers_status'), table_name='campaign_influencers')
    op.drop_index(op.f('ix_campaign_influencers_influencer_id'), table_name='campaign_influencers')
    op.drop_index(op.f('ix_campaign_influencers_campaign_id'), table_name='campaign_influencers')
    op.drop_index(op.f('ix_campaign_influencers_id'), table_name='campaign_influencers')
    op.drop_table('campaign_influencers')

    with op.batch_alter_table('influencers', schema=None) as batch_op:
        batch_op.drop_column('email_verified')
        batch_op.drop_column('metrics_source')
        batch_op.drop_column('metrics_sample_size')
        batch_op.drop_column('last_upload_at')

    with op.batch_alter_table('campaigns', schema=None) as batch_op:
        batch_op.drop_column('last_discovery_at')
        batch_op.drop_column('max_followers')
        batch_op.drop_column('min_followers')
        batch_op.drop_column('keywords')
