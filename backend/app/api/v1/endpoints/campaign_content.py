from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ForbiddenException, NotFoundException
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.campaign import Campaign
from app.models.campaign_content import CampaignContent, ContentPerformanceSnapshot
from app.models.campaign_influencer import CampaignInfluencer
from app.models.influencer import Influencer
from app.models.user import User
from app.schemas.campaign_content import (
    AttributionUpdateRequest,
    CampaignContentResponse,
    SnapshotResponse,
    TrackContentRequest,
)
from app.services.content_tracking_service import ContentTrackingService

router = APIRouter(prefix="/campaigns/{campaign_id}/content", tags=["Campaign Content Tracking"])


async def _get_owned_campaign(campaign_id: str, user: User, db: AsyncSession) -> Campaign:
    stmt = select(Campaign).where(Campaign.id == campaign_id, Campaign.owner_id == user.id)
    res = await db.execute(stmt)
    campaign = res.scalar_one_or_none()
    if not campaign:
        raise NotFoundException(detail=f"Campaign '{campaign_id}' not found or not accessible.")
    return campaign


def _norm_dt(dt: Optional[datetime]) -> datetime:
    if dt is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _build_content_response(content: CampaignContent, influencer: Optional[Influencer] = None) -> CampaignContentResponse:
    snapshots = [
        SnapshotResponse.model_validate(s)
        for s in sorted(content.snapshots or [], key=lambda x: _norm_dt(x.captured_at), reverse=True)
    ]

    return CampaignContentResponse(
        id=content.id,
        campaign_id=content.campaign_id,
        influencer_id=content.influencer_id,
        influencer_name=influencer.name if influencer else (content.influencer.name if content.influencer else None),
        influencer_username=influencer.username if influencer else (content.influencer.username if content.influencer else None),
        influencer_avatar=influencer.avatar if influencer else (content.influencer.avatar if content.influencer else None),
        platform=content.platform,
        content_type=content.content_type,
        external_content_id=content.external_content_id,
        content_url=content.content_url,
        title=content.title,
        thumbnail_url=content.thumbnail_url,
        channel_id=content.channel_id,
        channel_title=content.channel_title,
        published_at=content.published_at,
        duration_seconds=content.duration_seconds,
        tracking_status=content.tracking_status,
        agreed_cost=content.agreed_cost,
        currency=content.currency,
        last_sync_at=content.last_sync_at,
        sync_error=content.sync_error,
        baseline_median_views=content.baseline_median_views,
        baseline_avg_views=content.baseline_avg_views,
        baseline_avg_likes=content.baseline_avg_likes,
        baseline_avg_comments=content.baseline_avg_comments,
        baseline_engagement_rate=content.baseline_engagement_rate,
        baseline_sample_size=content.baseline_sample_size,
        current_views=content.current_views,
        current_likes=content.current_likes,
        current_comments=content.current_comments,
        engagement_rate=content.engagement_rate,
        performance_lift_percent=content.performance_lift_percent,
        cost_per_view=content.cost_per_view,
        cpm=content.cpm,
        cost_per_engagement=content.cost_per_engagement,
        engagement_lift_percent=content.engagement_lift_percent,
        performance_status=content.performance_status,
        attributed_orders=content.attributed_orders,
        average_order_value=content.average_order_value,
        attributed_revenue=content.attributed_revenue,
        gross_margin_percent=content.gross_margin_percent,
        attributed_profit=content.attributed_profit,
        attribution_source=content.attribution_source,
        attribution_updated_at=content.attribution_updated_at,
        roas=content.roas,
        roi=content.roi,
        content_age_hours=content.content_age_hours,
        content_age_days=content.content_age_days,
        content_stage=content.content_stage,
        momentum=content.momentum,
        snapshots=snapshots,
        created_at=content.created_at,
        updated_at=content.updated_at,
    )


@router.post("/track", response_model=CampaignContentResponse, summary="Register & track YouTube video or Short URL")
async def track_campaign_content(
    campaign_id: str,
    payload: TrackContentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    campaign = await _get_owned_campaign(campaign_id, current_user, db)

    # Verify influencer exists and is associated with this campaign or exists on platform
    inf_stmt = select(Influencer).where(Influencer.id == payload.influencer_id)
    inf_res = await db.execute(inf_stmt)
    influencer = inf_res.scalar_one_or_none()
    if not influencer:
        raise NotFoundException(detail=f"Influencer '{payload.influencer_id}' not found.")

    tracking_service = ContentTrackingService(db)
    content = await tracking_service.track_content(
        campaign=campaign,
        influencer=influencer,
        content_url=payload.content_url,
        content_type_override=payload.content_type,
    )

    return _build_content_response(content, influencer)


@router.get("", response_model=List[CampaignContentResponse], summary="List tracked campaign content")
async def list_campaign_content(
    campaign_id: str,
    influencer_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_campaign(campaign_id, current_user, db)

    stmt = (
        select(CampaignContent)
        .options(selectinload(CampaignContent.snapshots), selectinload(CampaignContent.influencer))
        .where(CampaignContent.campaign_id == campaign_id)
    )
    if influencer_id:
        stmt = stmt.where(CampaignContent.influencer_id == influencer_id)
    stmt = stmt.order_by(CampaignContent.created_at.desc())

    res = await db.execute(stmt)
    items = res.scalars().all()

    return [_build_content_response(item) for item in items]


@router.post("/{content_id}/refresh", response_model=CampaignContentResponse, summary="Refresh live metrics from YouTube API")
async def refresh_content_metrics(
    campaign_id: str,
    content_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_campaign(campaign_id, current_user, db)

    # Verify content belongs to this campaign
    c_stmt = (
        select(CampaignContent)
        .options(selectinload(CampaignContent.snapshots), selectinload(CampaignContent.influencer))
        .where(CampaignContent.id == content_id, CampaignContent.campaign_id == campaign_id)
    )
    c_res = await db.execute(c_stmt)
    content = c_res.scalar_one_or_none()
    if not content:
        raise NotFoundException(detail=f"Tracked content '{content_id}' not found for this campaign.")

    tracking_service = ContentTrackingService(db)
    updated = await tracking_service.refresh_content_metrics(content_id)

    # Reload with relationships
    c_res2 = await db.execute(c_stmt)
    reloaded = c_res2.scalar_one()
    return _build_content_response(reloaded)


@router.get("/{content_id}/snapshots", response_model=List[SnapshotResponse], summary="List historical performance snapshots")
async def list_content_snapshots(
    campaign_id: str,
    content_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_campaign(campaign_id, current_user, db)

    snap_stmt = (
        select(ContentPerformanceSnapshot)
        .join(CampaignContent, ContentPerformanceSnapshot.campaign_content_id == CampaignContent.id)
        .where(
            CampaignContent.campaign_id == campaign_id,
            ContentPerformanceSnapshot.campaign_content_id == content_id,
        )
        .order_by(ContentPerformanceSnapshot.captured_at.asc())
    )
    res = await db.execute(snap_stmt)
    snapshots = res.scalars().all()
    return [SnapshotResponse.model_validate(s) for s in snapshots]


@router.post(
    "/{content_id}/attribution",
    response_model=CampaignContentResponse,
    summary="Save verified campaign business attribution",
)
async def update_content_attribution(
    campaign_id: str,
    content_id: str,
    payload: AttributionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_campaign(campaign_id, current_user, db)

    # Verify content belongs to this campaign
    c_stmt = select(CampaignContent).where(
        CampaignContent.id == content_id, CampaignContent.campaign_id == campaign_id
    )
    c_res = await db.execute(c_stmt)
    content = c_res.scalar_one_or_none()
    if not content:
        raise NotFoundException(detail=f"Tracked content '{content_id}' not found for this campaign.")

    tracking_service = ContentTrackingService(db)
    updated = await tracking_service.update_content_attribution(
        content_id=content_id,
        attributed_revenue=payload.attributed_revenue,
        attributed_orders=payload.attributed_orders,
        average_order_value=payload.average_order_value,
        gross_margin_percent=payload.gross_margin_percent,
        attributed_profit=payload.attributed_profit,
        attribution_source=payload.attribution_source,
    )

    # Reload with influencer and snapshots
    load_stmt = (
        select(CampaignContent)
        .options(selectinload(CampaignContent.snapshots), selectinload(CampaignContent.influencer))
        .where(CampaignContent.id == content_id)
    )
    res = await db.execute(load_stmt)
    reloaded = res.scalar_one()

    return _build_content_response(reloaded)
