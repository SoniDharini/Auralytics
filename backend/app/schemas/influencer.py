from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class InfluencerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    external_id: Optional[str] = Field(None, alias="external_id")
    name: str
    username: str
    description: Optional[str] = None
    avatar: Optional[str] = None
    profile_url: Optional[str] = Field(None, alias="profile_url")
    thumbnail_url: Optional[str] = Field(None, alias="thumbnail_url")
    platform: str
    verified: bool = False
    niches: List[str] = Field(default_factory=list)
    followers: int = 0
    total_views: int = Field(0, alias="total_views")
    content_count: int = Field(0, alias="content_count")
    engagementRate: float = Field(0.0, alias="engagement_rate")
    avgViews: int = Field(0, alias="avg_views")
    avgLikes: int = Field(0, alias="avg_likes")
    avgComments: int = Field(0, alias="avg_comments")
    estimatedCost: Optional[float] = Field(None, alias="estimated_cost")
    location: Optional[str] = None
    country: Optional[str] = None

    # Scores (nullable for factual platform records)
    aiMatchScore: Optional[float] = Field(None, alias="ai_match_score")
    predictedRoas: Optional[float] = Field(None, alias="predicted_roas")
    audienceFit: Optional[float] = Field(None, alias="audience_fit")
    authenticity: Optional[float] = None
    brandSafety: Optional[float] = Field(None, alias="brand_safety")
    nicheMatch: Optional[float] = Field(None, alias="niche_match")
    budgetFit: Optional[float] = Field(None, alias="budget_fit")

    # Demographics (nullable when not officially provided)
    audienceGender: Optional[Dict[str, float]] = Field(None, alias="audience_gender")
    audienceAge: Optional[List[Dict[str, Any]]] = Field(None, alias="audience_age")
    topCountries: Optional[List[Dict[str, Any]]] = Field(None, alias="top_countries")
    topCities: Optional[List[str]] = Field(None, alias="top_cities")
    interests: Optional[List[str]] = Field(default_factory=list)
    whyRecommended: Optional[str] = Field(None, alias="why_recommended")

    shortlisted: bool = False
    status: str = "not_contacted"
    data_source: str = Field("youtube", alias="data_source")
    source_fetched_at: Optional[datetime] = Field(None, alias="source_fetched_at")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


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
