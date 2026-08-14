"""add campaign_activities table

Revision ID: 20260814_add_campaign_activities
Revises: 19bd12886dea
Create Date: 2026-08-14 14:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import app.db.custom_types


# revision identifiers, used by Alembic.
revision: str = '20260814_add_campaign_activities'
down_revision: Union[str, None] = '19bd12886dea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'campaign_activities',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('user_id', app.db.custom_types.GUID(), nullable=False),
        sa.Column('campaign_id', sa.String(length=64), nullable=True),
        sa.Column('activity_type', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata_json', app.db.custom_types.JSON_COMPAT(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_campaign_activities_id'), 'campaign_activities', ['id'], unique=False)
    op.create_index(op.f('ix_campaign_activities_user_id'), 'campaign_activities', ['user_id'], unique=False)
    op.create_index(op.f('ix_campaign_activities_campaign_id'), 'campaign_activities', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_campaign_activities_activity_type'), 'campaign_activities', ['activity_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_campaign_activities_activity_type'), table_name='campaign_activities')
    op.drop_index(op.f('ix_campaign_activities_campaign_id'), table_name='campaign_activities')
    op.drop_index(op.f('ix_campaign_activities_user_id'), table_name='campaign_activities')
    op.drop_index(op.f('ix_campaign_activities_id'), table_name='campaign_activities')
    op.drop_table('campaign_activities')
