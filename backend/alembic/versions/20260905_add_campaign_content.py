"""Add campaign_contents and content_performance_snapshots tables

Revision ID: 20260905_add_camp_content
Revises: 20260903_widen_inf_metrics
Create Date: 2026-09-05 16:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.db.custom_types import JSON_COMPAT

revision = "20260905_add_camp_content"
down_revision = "20260903_widen_inf_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Create campaign_contents table
    op.create_table(
        "campaign_contents",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("campaign_id", sa.String(length=64), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("influencer_id", sa.String(length=64), sa.ForeignKey("influencers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(length=50), server_default="youtube", nullable=False),
        sa.Column("content_type", sa.String(length=50), server_default="YOUTUBE_VIDEO", nullable=False),
        sa.Column("external_content_id", sa.String(length=255), nullable=False),
        sa.Column("content_url", sa.String(length=1000), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=1000), nullable=True),
        sa.Column("channel_id", sa.String(length=255), nullable=True),
        sa.Column("channel_title", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("tracking_status", sa.String(length=50), server_default="TRACKING", nullable=False),
        sa.Column("agreed_cost", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=10), server_default="INR", nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_error", sa.Text(), nullable=True),
        sa.Column("baseline_median_views", sa.Float(), nullable=True),
        sa.Column("baseline_avg_views", sa.Float(), nullable=True),
        sa.Column("baseline_avg_likes", sa.Float(), nullable=True),
        sa.Column("baseline_avg_comments", sa.Float(), nullable=True),
        sa.Column("baseline_engagement_rate", sa.Float(), nullable=True),
        sa.Column("baseline_sample_size", sa.Integer(), nullable=True),
        sa.Column("baseline_video_ids", JSON_COMPAT(), nullable=True),
        sa.Column("current_views", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("current_likes", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("current_comments", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("engagement_rate", sa.Float(), nullable=True),
        sa.Column("performance_lift_percent", sa.Float(), nullable=True),
        sa.Column("cost_per_view", sa.Float(), nullable=True),
        sa.Column("cost_per_engagement", sa.Float(), nullable=True),
        sa.Column("performance_status", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_campaign_contents_id", "campaign_contents", ["id"])
    op.create_index("ix_campaign_contents_campaign_id", "campaign_contents", ["campaign_id"])
    op.create_index("ix_campaign_contents_influencer_id", "campaign_contents", ["influencer_id"])
    op.create_index("ix_campaign_contents_platform", "campaign_contents", ["platform"])
    op.create_index("ix_campaign_contents_external_content_id", "campaign_contents", ["external_content_id"])
    op.create_index("ix_campaign_contents_tracking_status", "campaign_contents", ["tracking_status"])

    # Create content_performance_snapshots table
    op.create_table(
        "content_performance_snapshots",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("campaign_content_id", sa.String(length=64), sa.ForeignKey("campaign_contents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("views", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("likes", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("comments", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("view_growth_absolute", sa.BigInteger(), nullable=True),
        sa.Column("view_growth_percentage", sa.Float(), nullable=True),
        sa.Column("engagement_growth", sa.BigInteger(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_content_performance_snapshots_id", "content_performance_snapshots", ["id"])
    op.create_index("ix_content_performance_snapshots_content_id", "content_performance_snapshots", ["campaign_content_id"])


def downgrade() -> None:
    op.drop_table("content_performance_snapshots")
    op.drop_table("campaign_contents")
