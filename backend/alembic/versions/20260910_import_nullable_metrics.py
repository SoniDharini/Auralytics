"""Allow unknown imported campaign metrics to stay null, and store reported ROI.

Revision ID: 20260910_import_metrics
Revises: 20260909_add_hist_import
Create Date: 2026-09-10 13:40:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "20260910_import_metrics"
down_revision = "20260909_add_hist_import"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("campaigns", "budget", existing_type=sa.Float(), nullable=True)
    op.alter_column("campaigns", "spend", existing_type=sa.Float(), nullable=True)
    op.alter_column("campaigns", "revenue", existing_type=sa.Float(), nullable=True)
    op.alter_column("campaigns", "roas", existing_type=sa.Float(), nullable=True)
    op.alter_column("campaigns", "conversions", existing_type=sa.Integer(), nullable=True)
    op.alter_column("campaigns", "reach", existing_type=sa.Integer(), nullable=True)
    op.add_column("campaigns", sa.Column("roi", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaigns", "roi")
    op.alter_column("campaigns", "reach", existing_type=sa.Integer(), nullable=False)
    op.alter_column("campaigns", "conversions", existing_type=sa.Integer(), nullable=False)
    op.alter_column("campaigns", "roas", existing_type=sa.Float(), nullable=False)
    op.alter_column("campaigns", "revenue", existing_type=sa.Float(), nullable=False)
    op.alter_column("campaigns", "spend", existing_type=sa.Float(), nullable=False)
    op.alter_column("campaigns", "budget", existing_type=sa.Float(), nullable=False)
