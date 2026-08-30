"""Add negotiation_state, extracted_terms, and conversation_history to outreach_messages

Revision ID: 20260829_add_outreach_negotiation
Revises: 20260825_extend_outreach
Create Date: 2026-08-29 19:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260829_add_outreach_negotiation'
down_revision = '20260825_extend_outreach'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use batch mode or inspect for SQLite compatibility
    conn = op.get_bind()
    insp = sa.inspect(conn)
    columns = [c['name'] for c in insp.get_columns('outreach_messages')]

    if 'negotiation_state' not in columns:
        op.add_column('outreach_messages', sa.Column('negotiation_state', sa.String(length=50), nullable=True))
    if 'extracted_terms' not in columns:
        op.add_column('outreach_messages', sa.Column('extracted_terms', sa.JSON(), nullable=True))
    if 'conversation_history' not in columns:
        op.add_column('outreach_messages', sa.Column('conversation_history', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('outreach_messages', 'conversation_history')
    op.drop_column('outreach_messages', 'extracted_terms')
    op.drop_column('outreach_messages', 'negotiation_state')
