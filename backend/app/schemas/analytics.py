from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TrendData(BaseModel):
    value: str
    positive: bool


class MetricCardSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    value: str
    context: str
    trend: Optional[TrendData] = None
    sparkline: Optional[List[float]] = None


class RevenueSpendPoint(BaseModel):
    month: str
    spend: float
    revenue: float
    roas: float


class DashboardAnalyticsResponse(BaseModel):
    metrics: List[MetricCardSchema]
    revenueSpendData: List[RevenueSpendPoint]
    funnel: List[Dict[str, Any]]
    campaignHealth: List[Dict[str, Any]]
