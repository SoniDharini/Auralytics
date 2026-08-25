"""Extend outreach_messages with campaign_id, agent_run_id, short_dm, personalization_points, call_to_action, confidence, updated_at

Revision ID: 20260825_extend_outreach
Revises: 20260824_agent_run_grok_meta
Create Date: 2026-08-25 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260825_extend_outreach'
down_revision = '20260824_agent_run_grok_meta'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('outreach_messages', sa.Column('campaign_id', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_outreach_messages_campaign_id'), 'outreach_messages', ['campaign_id'], unique=False)
    op.add_column('outreach_messages', sa.Column('agent_run_id', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_outreach_messages_agent_run_id'), 'outreach_messages', ['agent_run_id'], unique=False)
    op.add_column('outreach_messages', sa.Column('short_dm', sa.Text(), nullable=True))
    op.add_column('outreach_messages', sa.Column('call_to_action', sa.Text(), nullable=True))
    op.add_column('outreach_messages', sa.Column('personalization_points', sa.JSON(), nullable=True))
    op.add_column('outreach_messages', sa.Column('confidence', sa.Float(), nullable=True))
    op.add_column('outreach_messages', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('outreach_messages', 'updated_at')
    op.drop_column('outreach_messages', 'confidence')
    op.drop_column('outreach_messages', 'personalization_points')
    op.drop_column('outreach_messages', 'call_to_action')
    op.drop_column('outreach_messages', 'short_dm')
    op.drop_index(op.f('ix_outreach_messages_agent_run_id'), table_name='outreach_messages')
    op.drop_column('outreach_messages', 'agent_run_id')
    op.drop_index(op.f('ix_outreach_messages_campaign_id'), table_name='outreach_messages')
    op.drop_column('outreach_messages', 'campaign_id')
