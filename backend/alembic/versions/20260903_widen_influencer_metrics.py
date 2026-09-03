"""Widen influencer metric columns to BIGINT

Revision ID: 20260903_widen_inf_metrics
Revises: 20260902_widen_contract
Create Date: 2026-09-03 00:10:00.000000

YouTube subscriber and view counters can exceed PostgreSQL INTEGER.
"""
from alembic import op


# Must stay <= 32 chars: alembic_version.version_num is VARCHAR(32).
revision = "20260903_widen_inf_metrics"
down_revision = "20260902_widen_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE influencers ALTER COLUMN followers TYPE BIGINT")
    op.execute("ALTER TABLE influencers ALTER COLUMN content_count TYPE BIGINT")
    op.execute("ALTER TABLE influencers ALTER COLUMN avg_views TYPE BIGINT")
    op.execute("ALTER TABLE influencers ALTER COLUMN avg_likes TYPE BIGINT")
    op.execute("ALTER TABLE influencers ALTER COLUMN avg_comments TYPE BIGINT")


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE influencers ALTER COLUMN followers TYPE INTEGER")
    op.execute("ALTER TABLE influencers ALTER COLUMN content_count TYPE INTEGER")
    op.execute("ALTER TABLE influencers ALTER COLUMN avg_views TYPE INTEGER")
    op.execute("ALTER TABLE influencers ALTER COLUMN avg_likes TYPE INTEGER")
    op.execute("ALTER TABLE influencers ALTER COLUMN avg_comments TYPE INTEGER")
