from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class InfluencerResponse(BaseModel):
    """Creator payload for the UI.

    Values are read from the snake_case ORM attributes via `validation_alias` and
    serialized under the camelCase field names the frontend types expect.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    external_id: Optional[str] = None
    name: str
    username: str
    description: Optional[str] = None
    avatar: Optional[str] = None
    profile_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    platform: str
    verified: bool = False
    niches: List[str] = Field(default_factory=list)
    followers: int = 0
    total_views: int = 0
    content_count: int = 0
    engagementRate: float = Field(0.0, validation_alias="engagement_rate")
    avgViews: int = Field(0, validation_alias="avg_views")
    avgLikes: int = Field(0, validation_alias="avg_likes")
    avgComments: int = Field(0, validation_alias="avg_comments")
    estimatedCost: Optional[float] = Field(None, validation_alias="estimated_cost")
    location: Optional[str] = None
    country: Optional[str] = None

    # Scores (nullable for factual platform records)
    aiMatchScore: Optional[float] = Field(None, validation_alias="ai_match_score")
    predictedRoas: Optional[float] = Field(None, validation_alias="predicted_roas")
    audienceFit: Optional[float] = Field(None, validation_alias="audience_fit")
    authenticity: Optional[float] = None
    brandSafety: Optional[float] = Field(None, validation_alias="brand_safety")
    nicheMatch: Optional[float] = Field(None, validation_alias="niche_match")
    budgetFit: Optional[float] = Field(None, validation_alias="budget_fit")

    # Demographics (nullable when not officially provided)
    audienceGender: Optional[Dict[str, float]] = Field(None, validation_alias="audience_gender")
    audienceAge: Optional[List[Dict[str, Any]]] = Field(None, validation_alias="audience_age")
    topCountries: Optional[List[Dict[str, Any]]] = Field(None, validation_alias="top_countries")
    topCities: Optional[List[str]] = Field(None, validation_alias="top_cities")
    interests: Optional[List[str]] = Field(default_factory=list)
    whyRecommended: Optional[str] = Field(None, validation_alias="why_recommended")

    shortlisted: bool = False
    status: str = "not_contacted"
    data_source: str = "youtube"
    source_fetched_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Contact details are never fabricated; populated only by a verified source.
    businessEmail: Optional[str] = Field(None, validation_alias="business_email")
    emailSource: Optional[str] = Field(None, validation_alias="email_source")
    emailVerified: bool = Field(False, validation_alias="email_verified")

    # Provenance of the derived averages above.
    lastUploadAt: Optional[datetime] = Field(None, validation_alias="last_upload_at")
    metricsSampleSize: int = Field(0, validation_alias="metrics_sample_size")
    metricsSource: Optional[str] = Field(None, validation_alias="metrics_source")


class MatchFactorSchema(BaseModel):
    key: str
    label: str
    weight: int
    score: Optional[float] = None
    available: bool = False
    detail: str


class CampaignCreatorResponse(BaseModel):
    """A creator as seen from inside one campaign, with that campaign's match signals."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    link_id: str
    campaign_id: str
    status: str
    match_score: Optional[float] = None
    match_reasons: Optional[List[MatchFactorSchema]] = None
    discovery_query: Optional[str] = None
    discovered_at: datetime
    creator: InfluencerResponse


class CampaignCreatorListResponse(BaseModel):
    campaign_id: str
    source: str = "youtube"
    count: int
    total: int
    page: int
    limit: int
    creators: List[CampaignCreatorResponse] = Field(default_factory=list)


class DiscoveryStatsSchema(BaseModel):
    queries: List[str] = Field(default_factory=list)
    raw_candidates: int = 0
    unique_channels: int = 0
    enriched_channels: int = 0
    passed_filters: int = 0
    filtered_out: int = 0
    created: int = 0
    updated: int = 0
    reused_from_cache: int = 0


class DiscoveryResponse(BaseModel):
    campaign_id: str
    source: str = "youtube"
    status: str
    count: int
    stats: DiscoveryStatsSchema
    creators: List[CampaignCreatorResponse] = Field(default_factory=list)


class CampaignCreatorStatusUpdate(BaseModel):
    status: str = Field(..., description="DISCOVERED | SHORTLISTED | REJECTED | CONTACTED")


class InfluencerFetchRequest(BaseModel):
    platforms: Optional[List[str]] = Field(default=None, description="Platforms to query, e.g. ['youtube', 'instagram']")
    limit: Optional[int] = Field(default=25, ge=1, le=100)
    force_refresh: Optional[bool] = Field(default=False, description="Bypass cache and force re-fetching from source APIs")


class ProviderResultSchema(BaseModel):
    status: str
    fetched: int = 0
    created: int = 0
    updated: int = 0
    message: Optional[str] = None


class InfluencerFetchResponse(BaseModel):
    campaign_id: str
    status: str
    total_discovered: int
    providers: Dict[str, ProviderResultSchema]
    influencers: Optional[List[InfluencerResponse]] = None


class IntegrationStatusResponse(BaseModel):
    youtube: Dict[str, Any]
    instagram: Dict[str, Any]
