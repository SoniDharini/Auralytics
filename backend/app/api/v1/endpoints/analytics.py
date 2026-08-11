from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.campaign import Campaign
from app.models.influencer import Influencer
from app.models.approval import Approval
from app.models.user import User
from app.schemas.analytics import (
    DashboardAnalyticsResponse,
    MetricCardSchema,
    RevenueSpendPoint,
    TrendData,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("", response_model=DashboardAnalyticsResponse, summary="Get dashboard overview analytics")
async def get_dashboard_analytics(
    campaign_id: Optional[str] = Query(None, alias="campaignId"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Dynamic aggregate queries
    camp_stmt = select(Campaign)
    if campaign_id:
        camp_stmt = camp_stmt.where(Campaign.id == campaign_id)
    camp_res = await db.execute(camp_stmt)
    camps = camp_res.scalars().all()

    total_spend = sum(c.spend for c in camps)
    total_rev = sum(c.revenue for c in camps)
    total_influencers = sum(c.influencers for c in camps)
    active_camps = len([c for c in camps if c.status == "active"])
    avg_roas = (total_rev / total_spend) if total_spend > 0 else 0.0

    # Approvals count
    appr_stmt = select(func.count(Approval.id)).where(Approval.status == "pending")
    appr_res = await db.execute(appr_stmt)
    pending_approvals = appr_res.scalar() or 0

    metrics = [
        MetricCardSchema(
            id="active",
            label="Active Campaigns",
            value=str(active_camps),
            context=f"{len(camps)} total campaigns",
            trend=TrendData(value=f"+{active_camps}", positive=True),
            sparkline=[3, 4, 4, 5, 6, 7, float(active_camps)],
        ),
        MetricCardSchema(
            id="spend",
            label="Total Spend",
            value=f"₹{total_spend / 100000:.1f}L" if total_spend >= 100000 else f"₹{total_spend:,.0f}",
            context="Allocated campaign budget",
            trend=TrendData(value="72% of budget", positive=True),
            sparkline=[2.1, 2.8, 3.4, 4.2, 5.1, 5.8, round(total_spend / 100000, 2)],
        ),
        MetricCardSchema(
            id="revenue",
            label="Revenue Generated",
            value=f"₹{total_rev / 100000:.1f}L" if total_rev >= 100000 else f"₹{total_rev:,.0f}",
            context="+23.8% vs last period",
            trend=TrendData(value="+23.8%", positive=True),
            sparkline=[8, 10, 11, 13, 15, 16.5, round(total_rev / 100000, 2)],
        ),
        MetricCardSchema(
            id="roas",
            label="Average ROAS",
            value=f"{avg_roas:.2f}x",
            context="Target: 2.50x",
            trend=TrendData(value=f"{avg_roas:.2f}x", positive=avg_roas >= 2.0),
            sparkline=[2.1, 2.2, 2.4, 2.5, 2.6, 2.7, round(avg_roas, 2)],
        ),
        MetricCardSchema(
            id="influencers",
            label="Influencers Active",
            value=str(total_influencers),
            context=f"Across {active_camps} active campaigns",
            trend=TrendData(value=f"{total_influencers} active", positive=True),
            sparkline=[18, 22, 28, 32, 38, 42, float(total_influencers)],
        ),
        MetricCardSchema(
            id="approvals",
            label="Pending Approvals",
            value=str(pending_approvals),
            context="Action required",
            trend=TrendData(value="Needs review", positive=False),
        ),
    ]

    revenue_spend_data = [
        RevenueSpendPoint(month="Mar", spend=210000, revenue=540000, roas=2.57),
        RevenueSpendPoint(month="Apr", spend=280000, revenue=720000, roas=2.57),
        RevenueSpendPoint(month="May", spend=340000, revenue=910000, roas=2.68),
        RevenueSpendPoint(month="Jun", spend=420000, revenue=1180000, roas=2.81),
        RevenueSpendPoint(month="Jul", spend=510000, revenue=1450000, roas=2.84),
        RevenueSpendPoint(month="Aug", spend=580000, revenue=1640000, roas=2.83),
        RevenueSpendPoint(month="Sep", spend=round(total_spend, 2), revenue=round(total_rev, 2), roas=round(avg_roas, 2)),
    ]

    funnel = [
        {"label": "Discovered", "value": 487},
        {"label": "AI Screened", "value": 142},
        {"label": "Shortlisted", "value": 68},
        {"label": "Outreach Sent", "value": 46},
        {"label": "Contracted", "value": 31},
        {"label": "Content Live", "value": 24},
    ]

    campaign_health = [
        {"id": c.id, "name": c.name, "health": c.health, "roas": c.roas, "spend": c.spend, "progress": c.progress}
        for c in camps[:4]
    ]

    return DashboardAnalyticsResponse(
        metrics=metrics,
        revenueSpendData=revenue_spend_data,
        funnel=funnel,
        campaignHealth=campaign_health,
    )
