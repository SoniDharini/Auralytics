"""Widen contract payment_due and related text columns

Revision ID: 20260902_widen_contract
Revises: 20260830_add_acceptance_contract_fields
Create Date: 2026-09-02 13:30:00.000000

"""
from alembic import op


# Must stay <= 32 chars: alembic_version.version_num is VARCHAR(32).
revision = "20260902_widen_contract"
down_revision = "20260830_add_acceptance_contract_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE contracts ALTER COLUMN payment_due TYPE VARCHAR(1000)")
    op.execute("ALTER TABLE contracts ALTER COLUMN usage_rights TYPE VARCHAR(1000)")
    op.execute("ALTER TABLE contracts ALTER COLUMN exclusivity TYPE VARCHAR(1000)")
    op.execute("ALTER TABLE contracts ALTER COLUMN additional_terms TYPE VARCHAR(2000)")
    op.execute("ALTER TABLE contracts ALTER COLUMN contract_body TYPE TEXT")


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE contracts ALTER COLUMN payment_due TYPE VARCHAR(50)")
    op.execute("ALTER TABLE contracts ALTER COLUMN usage_rights TYPE VARCHAR(255)")
    op.execute("ALTER TABLE contracts ALTER COLUMN exclusivity TYPE VARCHAR(255)")
    op.execute("ALTER TABLE contracts ALTER COLUMN additional_terms TYPE VARCHAR(1000)")
    op.execute("ALTER TABLE contracts ALTER COLUMN contract_body TYPE VARCHAR(10000)")
