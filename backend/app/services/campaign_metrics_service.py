"""Reconcile campaign card metrics without erasing imported historical values."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.campaign_content import CampaignContent, TrackingStatus
from app.models.campaign_influencer import CampaignInfluencer
from app.models.contract import Contract


HISTORICAL_SOURCE = "HISTORICAL_REPORTED_RESULTS"


async def reconcile_campaign_metrics(campaign: Campaign, db: AsyncSession) -> Campaign:
    """Lift spend/reach/creator counts from live records without zeroing imports.

    Live tracked content and signed contracts can raise totals. They must not
    replace a stored imported value with zero, and they must not overwrite a
    reported historical ROAS.
    """
    live_stmt = select(
        func.coalesce(func.sum(CampaignContent.agreed_cost), 0.0),
        func.coalesce(func.sum(CampaignContent.current_views), 0),
        func.count(func.distinct(CampaignContent.influencer_id)),
    ).where(
        CampaignContent.campaign_id == campaign.id,
        CampaignContent.tracking_status.in_([TrackingStatus.ACTIVE, TrackingStatus.TRACKING]),
    )
    live_row = (await db.execute(live_stmt)).first()
    tracked_spend = float(live_row[0] or 0.0) if live_row else 0.0
    tracked_reach = int(live_row[1] or 0) if live_row else 0
    tracked_creators = int(live_row[2] or 0) if live_row else 0

    hist_stmt = select(
        func.coalesce(func.sum(CampaignContent.agreed_cost), 0.0),
        func.coalesce(func.sum(CampaignContent.current_views), 0),
    ).where(
        CampaignContent.campaign_id == campaign.id,
        CampaignContent.attribution_source == HISTORICAL_SOURCE,
    )
    hist_row = (await db.execute(hist_stmt)).first()
    imported_spend = float(hist_row[0] or 0.0) if hist_row else 0.0
    imported_reach = int(hist_row[1] or 0) if hist_row else 0

    contract_stmt = select(
        func.coalesce(func.sum(Contract.value), 0.0),
        func.count(func.distinct(Contract.influencer_id)),
    ).where(
        Contract.campaign_id == campaign.id,
        Contract.status.in_(["APPROVED", "signed"]),
    )
    cntr_row = (await db.execute(contract_stmt)).first()
    contract_spend = float(cntr_row[0] or 0.0) if cntr_row else 0.0
    contracted_creators = int(cntr_row[1] or 0) if cntr_row else 0

    link_count = int(
        (
            await db.execute(
                select(func.count()).select_from(CampaignInfluencer).where(
                    CampaignInfluencer.campaign_id == campaign.id
                )
            )
        ).scalar_one()
        or 0
    )

    spend_floor = campaign.spend if campaign.spend is not None else 0.0
    reach_floor = campaign.reach if campaign.reach is not None else 0

    effective_spend = max(tracked_spend, contract_spend, imported_spend, spend_floor)
    effective_reach = max(tracked_reach, imported_reach, reach_floor)
    effective_creators = max(tracked_creators, contracted_creators, campaign.influencers or 0, link_count)

    live_rev_stmt = select(func.coalesce(func.sum(CampaignContent.attributed_revenue), 0.0)).where(
        CampaignContent.campaign_id == campaign.id,
        CampaignContent.tracking_status.in_([TrackingStatus.ACTIVE, TrackingStatus.TRACKING]),
    )
    live_revenue = float(((await db.execute(live_rev_stmt)).first() or [0.0])[0] or 0.0)

    changed = False
    if campaign.spend is None:
        if effective_spend > 0:
            campaign.spend = effective_spend
            changed = True
    elif effective_spend != campaign.spend:
        campaign.spend = effective_spend
        changed = True

    if campaign.reach is None:
        if effective_reach > 0:
            campaign.reach = effective_reach
            changed = True
    elif effective_reach != campaign.reach:
        campaign.reach = effective_reach
        changed = True

    if effective_creators != campaign.influencers:
        campaign.influencers = effective_creators
        changed = True

    if live_revenue > 0 and (campaign.revenue is None or campaign.revenue == 0):
        campaign.revenue = live_revenue
        changed = True

    if changed:
        await db.commit()
        await db.refresh(campaign)
    return campaign
