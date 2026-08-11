from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class InfluencerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    name: str
    username: str
    avatar: str
    platform: str
    verified: bool
    niches: List[str]
    followers: int
    engagementRate: float = Field(..., alias="engagement_rate")
    avgViews: int = Field(..., alias="avg_views")
    avgLikes: int = Field(..., alias="avg_likes")
    avgComments: int = Field(..., alias="avg_comments")
    estimatedCost: float = Field(..., alias="estimated_cost")
    location: str
    aiMatchScore: float = Field(..., alias="ai_match_score")
    predictedRoas: float = Field(..., alias="predicted_roas")
    audienceFit: float = Field(..., alias="audience_fit")
    authenticity: float
    brandSafety: float = Field(..., alias="brand_safety")
    nicheMatch: float = Field(..., alias="niche_match")
    budgetFit: float = Field(..., alias="budget_fit")
    audienceGender: Dict[str, float] = Field(..., alias="audience_gender")
    audienceAge: List[Dict[str, Any]] = Field(..., alias="audience_age")
    topCountries: List[Dict[str, Any]] = Field(..., alias="top_countries")
    topCities: List[str] = Field(..., alias="top_cities")
    interests: List[str]
    whyRecommended: str = Field(..., alias="why_recommended")
    shortlisted: bool = False
    status: str = "not_contacted"
