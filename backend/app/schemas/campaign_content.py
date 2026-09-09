from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TrackContentRequest(BaseModel):
    influencer_id: str = Field(..., description="Campaign influencer ID")
    content_url: str = Field(..., description="Exact YouTube video or Short URL")
    content_type: Optional[str] = Field(None, description="YOUTUBE_VIDEO | YOUTUBE_SHORT")


class AttributionUpdateRequest(BaseModel):
    """Business attribution supplied by brand/user for real financial outcome tracking."""
    # Option A: Direct Attributed Revenue
    attributed_revenue: Optional[float] = Field(None, ge=0, description="Direct revenue attributed to this content (INR)")
    
    # Option B: Orders & Average Order Value (backend computes revenue = orders * aov)
    attributed_orders: Optional[int] = Field(None, ge=0, description="Attributed orders / sales count")
    average_order_value: Optional[float] = Field(None, ge=0, description="Average order value (INR)")

    # Optional Profit & Margin Data (Required for true ROI; otherwise ROI is NOT_AVAILABLE)
    gross_margin_percent: Optional[float] = Field(None, ge=0, le=100, description="Gross profit margin % (0-100)")
    attributed_profit: Optional[float] = Field(None, description="Direct attributed gross profit (INR)")

    # Informational Attribution Source
    attribution_source: Optional[str] = Field(
        None,
        description="Tracking Link | Coupon Code | Ecommerce Analytics | CRM Sales Data | Manual Verified Entry | Other",
    )


class SnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_content_id: str
    views: int
    likes: int
    comments: int
    view_growth_absolute: Optional[int] = None
    view_growth_percentage: Optional[float] = None
    engagement_growth: Optional[int] = None
    captured_at: datetime


class CampaignContentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    influencer_id: str
    influencer_name: Optional[str] = None
    influencer_username: Optional[str] = None
    influencer_avatar: Optional[str] = None

    platform: str
    content_type: str
    external_content_id: str
    content_url: str
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None
    channel_id: Optional[str] = None
    channel_title: Optional[str] = None
    published_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None

    tracking_status: str
    agreed_cost: Optional[float] = None
    currency: str = "INR"
    last_sync_at: Optional[datetime] = None
    sync_error: Optional[str] = None

    baseline_median_views: Optional[float] = None
    baseline_avg_views: Optional[float] = None
    baseline_avg_likes: Optional[float] = None
    baseline_avg_comments: Optional[float] = None
    baseline_engagement_rate: Optional[float] = None
    baseline_sample_size: Optional[int] = None

    current_views: int
    current_likes: int
    current_comments: int
    engagement_rate: Optional[float] = None
    performance_lift_percent: Optional[float] = None
    cost_per_view: Optional[float] = None
    cpm: Optional[float] = None
    cost_per_engagement: Optional[float] = None
    engagement_lift_percent: Optional[float] = None
    performance_status: Optional[str] = None

    # Deterministic Business Attribution & Financial Outcomes
    attributed_orders: Optional[int] = None
    average_order_value: Optional[float] = None
    attributed_revenue: Optional[float] = None
    gross_margin_percent: Optional[float] = None
    attributed_profit: Optional[float] = None
    attribution_source: Optional[str] = None
    attribution_updated_at: Optional[datetime] = None

    # Financial KPIs
    roas: Optional[float] = None
    roi: Optional[float] = None

    # Time-Aware Performance Metrics
    content_age_hours: Optional[float] = None
    content_age_days: Optional[float] = None
    content_stage: Optional[str] = None
    momentum: Optional[str] = None

    is_demo: bool = False
    snapshots: List[SnapshotResponse] = []
    created_at: datetime
    updated_at: datetime


class PerformanceAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    influencer_id: str
    campaign_content_id: str
    latest_snapshot_id: Optional[str] = None
    agent_run_id: Optional[str] = None
    status: str
    content_stage: str
    summary: str
    what_is_working: List[str] = []
    needs_attention: List[str] = []
    financial_interpretation: str
    next_step: str
    confidence: float
    raw_kpis: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class OptimizationRecommendationSchema(BaseModel):
    id: Optional[str] = None
    priority: str
    category: str
    action: str
    reason: str
    evidence: List[str] = []
    requires_human_approval: bool = True
    approval_id: Optional[str] = None
    status: str = "pending"


class OptimizationPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    campaign_content_id: Optional[str] = None
    performance_analysis_id: Optional[str] = None
    agent_run_id: Optional[str] = None
    status: str = "PENDING_APPROVAL"
    recommendations: List[OptimizationRecommendationSchema] = []
    created_at: datetime
    updated_at: datetime


class DecideOptimizationRequest(BaseModel):
    approval_id: str
    decision: str  # "approved", "modified", "rejected"
    reason: Optional[str] = None

