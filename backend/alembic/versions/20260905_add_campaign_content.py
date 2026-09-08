"""Add campaign_contents, content_performance_snapshots, performance_analyses and optimization_plans

Revision ID: 20260905_add_camp_content
Revises: 20260903_widen_inf_metrics
Create Date: 2026-09-05 16:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.db.custom_types import GUID, JSON_COMPAT

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
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("campaign_id", sa.String(length=64), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("influencer_id", sa.String(length=64), sa.ForeignKey("influencers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(length=50), server_default="youtube", nullable=False),
        sa.Column("content_type", sa.String(length=50), server_default="YOUTUBE_VIDEO", nullable=False),
        sa.Column("external_content_id", sa.String(length=255), nullable=False),
        sa.Column("content_url", sa.String(length=1000), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default="true", nullable=False),
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
        sa.Column("attributed_orders", sa.Integer(), nullable=True),
        sa.Column("average_order_value", sa.Float(), nullable=True),
        sa.Column("attributed_revenue", sa.Float(), nullable=True),
        sa.Column("gross_margin_percent", sa.Float(), nullable=True),
        sa.Column("attributed_profit", sa.Float(), nullable=True),
        sa.Column("attribution_source", sa.String(length=100), nullable=True),
        sa.Column("attribution_updated_at", sa.DateTime(timezone=True), nullable=True),
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

    # Create campaign_performance_analyses table
    op.create_table(
        "campaign_performance_analyses",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("campaign_id", sa.String(length=64), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("influencer_id", sa.String(length=64), sa.ForeignKey("influencers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("campaign_content_id", sa.String(length=64), sa.ForeignKey("campaign_contents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("latest_snapshot_id", sa.String(length=64), sa.ForeignKey("content_performance_snapshots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_run_id", sa.String(length=64), sa.ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("content_stage", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("what_is_working", JSON_COMPAT(), nullable=False),
        sa.Column("needs_attention", JSON_COMPAT(), nullable=False),
        sa.Column("financial_interpretation", sa.Text(), nullable=False),
        sa.Column("next_step", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.9", nullable=False),
        sa.Column("raw_kpis", JSON_COMPAT(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_campaign_performance_analyses_id", "campaign_performance_analyses", ["id"])
    op.create_index("ix_campaign_performance_analyses_user_id", "campaign_performance_analyses", ["user_id"])
    op.create_index("ix_campaign_performance_analyses_campaign_id", "campaign_performance_analyses", ["campaign_id"])
    op.create_index("ix_campaign_performance_analyses_content_id", "campaign_performance_analyses", ["campaign_content_id"])

    # Create campaign_optimization_plans table
    op.create_table(
        "campaign_optimization_plans",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("campaign_id", sa.String(length=64), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("campaign_content_id", sa.String(length=64), sa.ForeignKey("campaign_contents.id", ondelete="CASCADE"), nullable=True),
        sa.Column("performance_analysis_id", sa.String(length=64), sa.ForeignKey("campaign_performance_analyses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_run_id", sa.String(length=64), sa.ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recommendations_json", JSON_COMPAT(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_campaign_optimization_plans_id", "campaign_optimization_plans", ["id"])
    op.create_index("ix_campaign_optimization_plans_user_id", "campaign_optimization_plans", ["user_id"])
    op.create_index("ix_campaign_optimization_plans_campaign_id", "campaign_optimization_plans", ["campaign_id"])


def downgrade() -> None:
    op.drop_table("campaign_optimization_plans")
    op.drop_table("campaign_performance_analyses")
    op.drop_table("content_performance_snapshots")
    op.drop_table("campaign_contents")

