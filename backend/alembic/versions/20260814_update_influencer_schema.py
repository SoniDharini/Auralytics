"""update influencer schema and add influencer_source_snapshots

Revision ID: 20260814_update_influencer_schema
Revises: 20260814_add_campaign_activities
Create Date: 2026-08-14 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import app.db.custom_types


# revision identifiers, used by Alembic.
revision: str = '20260814_update_influencers'
down_revision: Union[str, None] = '20260814_add_campaign_activities'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to influencers table
    with op.batch_alter_table('influencers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('external_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('profile_url', sa.String(length=1000), nullable=True))
        batch_op.add_column(sa.Column('thumbnail_url', sa.String(length=1000), nullable=True))
        batch_op.add_column(sa.Column('country', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('total_views', sa.BigInteger(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('content_count', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('business_email', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('email_source', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('data_source', sa.String(length=100), server_default='youtube', nullable=False))
        batch_op.add_column(sa.Column('source_fetched_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False))

        # Make columns nullable that were previously non-nullable in mock schema
        batch_op.alter_column('avatar', existing_type=sa.String(length=500), type_=sa.String(length=1000), nullable=True)
        batch_op.alter_column('location', existing_type=sa.String(length=255), nullable=True)
        batch_op.alter_column('estimated_cost', existing_type=sa.Float(), nullable=True)
        batch_op.alter_column('ai_match_score', existing_type=sa.Float(), nullable=True)
        batch_op.alter_column('predicted_roas', existing_type=sa.Float(), nullable=True)
        batch_op.alter_column('audience_fit', existing_type=sa.Float(), nullable=True)
        batch_op.alter_column('authenticity', existing_type=sa.Float(), nullable=True)
        batch_op.alter_column('brand_safety', existing_type=sa.Float(), nullable=True)
        batch_op.alter_column('niche_match', existing_type=sa.Float(), nullable=True)
        batch_op.alter_column('budget_fit', existing_type=sa.Float(), nullable=True)
        batch_op.alter_column('audience_gender', existing_type=app.db.custom_types.JSON_COMPAT(), nullable=True)
        batch_op.alter_column('audience_age', existing_type=app.db.custom_types.JSON_COMPAT(), nullable=True)
        batch_op.alter_column('top_countries', existing_type=app.db.custom_types.JSON_COMPAT(), nullable=True)
        batch_op.alter_column('top_cities', existing_type=app.db.custom_types.JSON_COMPAT(), nullable=True)
        batch_op.alter_column('interests', existing_type=app.db.custom_types.JSON_COMPAT(), nullable=True)
        batch_op.alter_column('why_recommended', existing_type=sa.Text(), nullable=True)

        batch_op.create_index(batch_op.f('ix_influencers_external_id'), ['external_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_influencers_platform'), ['platform'], unique=False)
        batch_op.create_unique_constraint('uq_influencer_platform_external_id', ['platform', 'external_id'])

    # Create influencer_source_snapshots table
    op.create_table(
        'influencer_source_snapshots',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('influencer_id', sa.String(length=64), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('raw_payload', app.db.custom_types.JSON_COMPAT(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['influencer_id'], ['influencers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_influencer_source_snapshots_id'), 'influencer_source_snapshots', ['id'], unique=False)
    op.create_index(op.f('ix_influencer_source_snapshots_influencer_id'), 'influencer_source_snapshots', ['influencer_id'], unique=False)


def downgrade() -> None:
    op.drop_table('influencer_source_snapshots')
    with op.batch_alter_table('influencers', schema=None) as batch_op:
        batch_op.drop_constraint('uq_influencer_platform_external_id', type_='unique')
        batch_op.drop_index(batch_op.f('ix_influencers_platform'))
        batch_op.drop_index(batch_op.f('ix_influencers_external_id'))
        batch_op.drop_column('source_fetched_at')
        batch_op.drop_column('data_source')
        batch_op.drop_column('email_source')
        batch_op.drop_column('business_email')
        batch_op.drop_column('content_count')
        batch_op.drop_column('total_views')
        batch_op.drop_column('country')
        batch_op.drop_column('thumbnail_url')
        batch_op.drop_column('profile_url')
        batch_op.drop_column('description')
        batch_op.drop_column('external_id')
