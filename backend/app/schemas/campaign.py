import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    brand: str = Field(default="GlowNaturals", max_length=255)
    budget: float = Field(..., ge=0)
    objective: str = Field(default="Product Launch", max_length=100)
    start_date: str = Field(..., max_length=50)
    end_date: str = Field(..., max_length=50)
    status: str = Field(default="planning", max_length=50)
    health: str = Field(default="healthy", max_length=50)

    description: Optional[str] = None
    campaign_types: Optional[List[str]] = None
    target_locations: Optional[str] = None
    target_age_min: Optional[int] = None
    target_age_max: Optional[int] = None
    target_gender: Optional[str] = None
    interests: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    platforms: Optional[List[str]] = None
    creator_tiers: Optional[List[str]] = None
    budget_allocation: Optional[List[Dict[str, Any]]] = None
    primary_kpi: Optional[str] = None
    target_roas: Optional[float] = None
    target_cpa: Optional[float] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    status: Optional[str] = None
    health: Optional[str] = None
    budget: Optional[float] = None
    spend: Optional[float] = None
    revenue: Optional[float] = None
    roas: Optional[float] = None
    influencers: Optional[int] = None
    progress: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    conversions: Optional[int] = None
    reach: Optional[int] = None
    objective: Optional[str] = None
    description: Optional[str] = None
    campaign_types: Optional[List[str]] = None
    target_locations: Optional[str] = None
    target_age_min: Optional[int] = None
    target_age_max: Optional[int] = None
    target_gender: Optional[str] = None
    interests: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    platforms: Optional[List[str]] = None
    creator_tiers: Optional[List[str]] = None
    budget_allocation: Optional[List[Dict[str, Any]]] = None
    primary_kpi: Optional[str] = None
    target_roas: Optional[float] = None
    target_cpa: Optional[float] = None


class CampaignActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    user_id: uuid.UUID
    campaign_id: Optional[str] = None
    activity_type: str
    title: str
    description: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    name: str
    brand: str
    status: str
    health: str
    budget: float
    spend: float
    revenue: float
    roas: float
    influencers: int
    progress: int
    startDate: str = Field(..., alias="start_date")
    endDate: str = Field(..., alias="end_date")
    conversions: int
    reach: int
    objective: str
    description: Optional[str] = None
    campaign_types: Optional[List[str]] = None
    target_locations: Optional[str] = None
    target_age_min: Optional[int] = None
    target_age_max: Optional[int] = None
    target_gender: Optional[str] = None
    interests: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    platforms: Optional[List[str]] = None
    creator_tiers: Optional[List[str]] = None
    budget_allocation: Optional[List[Dict[str, Any]]] = None
    primary_kpi: Optional[str] = None
    target_roas: Optional[float] = None
    target_cpa: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class DashboardSummaryResponse(BaseModel):
    total_campaigns: int
    active_campaigns: int
    pending_campaigns: int
    completed_campaigns: int
    total_spend: float
    total_revenue: float
    average_roas: float
    pending_approvals: int
