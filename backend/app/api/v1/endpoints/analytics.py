from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.campaigns import reconcile_campaign_metrics
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.campaign import Campaign
from app.models.campaign_influencer import CampaignInfluencer, CampaignInfluencerStatus
from app.models.contract import Contract
from app.models.user import User
from app.schemas.analytics import (
    DashboardAnalyticsResponse,
    MetricCardSchema,
    RevenueSpendPoint,
    TrendData,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("", response_model=DashboardAnalyticsResponse, summary="Get dashboard overview analytics for current user")
async def get_dashboard_analytics(
    campaign_id: Optional[str] = Query(None, alias="campaignId"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Dynamic aggregate queries strictly for current user
    camp_stmt = select(Campaign).where(Campaign.owner_id == current_user.id)
    if campaign_id:
        camp_stmt = camp_stmt.where(Campaign.id == campaign_id)
    camp_res = await db.execute(camp_stmt)
    raw_camps = camp_res.scalars().all()
    camps = [await reconcile_campaign_metrics(c, db) for c in raw_camps]

    total_spend = sum(c.spend for c in camps)
    total_rev = sum(c.revenue for c in camps)
    active_camps = len([c for c in camps if c.status == "active"])
    avg_roas = (total_rev / total_spend) if total_spend > 0 else 0.0
    pending_approvals = 0

    camp_ids = [c.id for c in camps]
    discovered_cnt = 0
    shortlisted_cnt = 0
    contracted_cnt = 0
    active_cnt = 0

    if camp_ids:
        discovered_res = await db.execute(
            select(func.count())
            .select_from(CampaignInfluencer)
            .where(
                CampaignInfluencer.campaign_id.in_(camp_ids),
                CampaignInfluencer.status == CampaignInfluencerStatus.DISCOVERED,
            )
        )
        discovered_cnt = discovered_res.scalar() or 0

        shortlisted_res = await db.execute(
            select(func.count())
            .select_from(CampaignInfluencer)
            .where(
                CampaignInfluencer.campaign_id.in_(camp_ids),
                CampaignInfluencer.status.in_([
                    CampaignInfluencerStatus.SHORTLISTED,
                    CampaignInfluencerStatus.CONTACTED,
                    CampaignInfluencerStatus.NEGOTIATING,
                    CampaignInfluencerStatus.ACCEPTED,
                ]),
            )
        )
        shortlisted_cnt = shortlisted_res.scalar() or 0

        contracted_res = await db.execute(
            select(func.count())
            .select_from(Contract)
            .where(Contract.campaign_id.in_(camp_ids))
        )
        contracted_cnt = contracted_res.scalar() or 0

        signed_res = await db.execute(
            select(func.count())
            .select_from(Contract)
            .where(
                Contract.campaign_id.in_(camp_ids),
                Contract.status.in_(["signed", "APPROVED"]),
            )
        )
        active_cnt = signed_res.scalar() or 0
        if active_cnt == 0 and contracted_cnt > 0:
            active_cnt = contracted_cnt
        elif active_cnt == 0:
            accepted_res = await db.execute(
                select(func.count())
                .select_from(CampaignInfluencer)
                .where(
                    CampaignInfluencer.campaign_id.in_(camp_ids),
                    CampaignInfluencer.status == CampaignInfluencerStatus.ACCEPTED,
                )
            )
            active_cnt = accepted_res.scalar() or 0

    total_discovered_pool = discovered_cnt + shortlisted_cnt
    if total_discovered_pool > 0:
        total_influencers = shortlisted_cnt
        funnel = [
            {"label": "Discovered", "value": total_discovered_pool},
            {"label": "Shortlisted", "value": shortlisted_cnt},
            {"label": "Contracted", "value": contracted_cnt},
            {"label": "Active", "value": active_cnt},
        ]
    else:
        fallback_inf = sum(c.influencers for c in camps)
        total_influencers = fallback_inf
        if camps:
            funnel = [
                {"label": "Discovered", "value": fallback_inf},
                {"label": "Shortlisted", "value": fallback_inf},
                {"label": "Contracted", "value": fallback_inf},
                {"label": "Active", "value": fallback_inf},
            ]
        else:
            funnel = []

    metrics = [
        MetricCardSchema(
            id="active",
            label="Active Campaigns",
            value=str(active_camps),
            context=f"{len(camps)} total campaigns",
            trend=TrendData(value=f"+{active_camps}", positive=True),
            sparkline=[0, 0, 0, 0, float(active_camps)] if len(camps) > 0 else None,
        ),
        MetricCardSchema(
            id="spend",
            label="Total Spend",
            value=f"₹{total_spend / 100000:.1f}L" if total_spend >= 100000 else f"₹{total_spend:,.0f}",
            context="Allocated campaign budget",
            trend=TrendData(value="0% of budget" if total_spend == 0 else f"{int(min(100, (total_spend / (sum(c.budget for c in camps) or 1)) * 100))}% of budget", positive=True),
            sparkline=None,
        ),
        MetricCardSchema(
            id="revenue",
            label="Revenue Generated",
            value=f"₹{total_rev / 100000:.1f}L" if total_rev >= 100000 else f"₹{total_rev:,.0f}",
            context="Attributed revenue",
            trend=TrendData(value="+0%" if total_rev == 0 else "+100%", positive=True),
            sparkline=None,
        ),
        MetricCardSchema(
            id="roas",
            label="Average ROAS",
            value=f"{avg_roas:.2f}x",
            context="Target: 2.50x",
            trend=TrendData(value=f"{avg_roas:.2f}x", positive=avg_roas >= 2.0),
            sparkline=None,
        ),
        MetricCardSchema(
            id="influencers",
            label="Influencers Active",
            value=str(total_influencers),
            context=f"Across {active_camps} active campaigns",
            trend=TrendData(value=f"{total_influencers} active", positive=True),
            sparkline=None,
        ),
        MetricCardSchema(
            id="approvals",
            label="Pending Approvals",
            value=str(pending_approvals),
            context="Action required",
            trend=TrendData(value="Up to date" if pending_approvals == 0 else "Needs review", positive=pending_approvals == 0),
            sparkline=None,
        ),
    ]

    if camps:
        revenue_spend_data = [
            RevenueSpendPoint(
                month="Current",
                spend=round(total_spend, 2),
                revenue=round(total_rev, 2),
                roas=round(avg_roas, 2),
            )
        ]
    else:
        revenue_spend_data = []

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
