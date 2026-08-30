"""Add response_status, acceptance fields to outreach_messages and campaign_id to contracts

Revision ID: 20260830_add_acceptance_contract_fields
Revises: 20260829_add_outreach_negotiation
Create Date: 2026-08-30 11:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260830_add_acceptance_contract_fields'
down_revision = '20260829_add_outreach_negotiation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    
    # Outreach messages columns
    outreach_cols = [c['name'] for c in insp.get_columns('outreach_messages')]
    for col_name, col_type in [
        ('response_status', sa.String(length=50)),
        ('response_text', sa.Text()),
        ('final_amount', sa.Float()),
        ('currency', sa.String(length=10)),
        ('deliverables', sa.JSON()),
        ('timeline_start', sa.String(length=50)),
        ('timeline_end', sa.String(length=50)),
        ('additional_terms', sa.Text()),
        ('rejection_reason', sa.String(length=100)),
        ('rejection_notes', sa.Text()),
        ('contract_id', sa.String(length=64)),
    ]:
        if col_name not in outreach_cols:
            op.add_column('outreach_messages', sa.Column(col_name, col_type, nullable=True))

    # Contracts columns
    contract_cols = [c['name'] for c in insp.get_columns('contracts')]
    for col_name, col_type in [
        ('campaign_id', sa.String(length=64)),
        ('influencer_id', sa.String(length=64)),
        ('outreach_id', sa.String(length=64)),
        ('currency', sa.String(length=10)),
        ('additional_terms', sa.String(length=1000)),
        ('contract_body', sa.String(length=10000)),
    ]:
        if col_name not in contract_cols:
            op.add_column('contracts', sa.Column(col_name, col_type, nullable=True))


def downgrade() -> None:
    pass
