"""Campaign-scoped creator discovery endpoints.

Every route resolves the campaign through the authenticated user, so a user can
only ever reach discovery results belonging to their own campaigns.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import InvalidRequestException, NotFoundException
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.campaign import Campaign
from app.models.campaign_influencer import CampaignInfluencer, CampaignInfluencerStatus
from app.models.influencer import Influencer
from app.models.user import User
from app.ai.agents.supervisor import SupervisorAgent
from app.models.outreach import OutreachMessage
from app.schemas.influencer import (
    CampaignCreatorListResponse,
    CampaignCreatorResponse,
    CampaignCreatorStatusUpdate,
    DiscoveryResponse,
    DiscoveryStatsSchema,
    InfluencerResponse,
)
from app.services.creator_discovery_service import CreatorDiscoveryService, discover_for_campaign_with_retry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["Creator Discovery"])

SORT_FIELDS = {
    "match_score": CampaignInfluencer.match_score,
    "followers": Influencer.followers,
    "engagement": Influencer.engagement_rate,
    "avg_views": Influencer.avg_views,
    "recent": CampaignInfluencer.discovered_at,
}


async def _load_owned_campaign(db: AsyncSession, campaign_id: str, user: User) -> Campaign:
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.owner_id == user.id,
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        # Same response for "does not exist" and "belongs to someone else" so the
        # endpoint cannot be used to probe for other users' campaign IDs.
        raise NotFoundException(detail=f"Campaign {campaign_id} not found")
    return campaign


def _to_creator_response(link: CampaignInfluencer) -> CampaignCreatorResponse:
    return CampaignCreatorResponse(
        link_id=link.id,
        campaign_id=link.campaign_id,
        status=link.status,
        match_score=link.match_score,
        match_reasons=link.match_reasons,
        discovery_query=link.discovery_query,
        discovered_at=link.discovered_at,
        creator=InfluencerResponse.model_validate(link.influencer),
    )


@router.post(
    "/{campaign_id}/discover-creators",
    response_model=DiscoveryResponse,
    summary="Discover real YouTube creators matching this campaign",
)
async def discover_creators(
    campaign_id: str,
    refresh: bool = Query(False, description="Bypass the cached creator statistics and re-fetch from YouTube"),
    limit: int = Query(25, ge=1, le=50, description="Maximum creators to enrich and persist"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    campaign = await _load_owned_campaign(db, campaign_id, current_user)

    service = CreatorDiscoveryService()
    result = await discover_for_campaign_with_retry(
        db=db,
        service=service,
        campaign=campaign,
        user_id=current_user.id,
        limit=limit,
        force_refresh=refresh,
    )

    await db.commit()

    # Re-read with the creator eagerly loaded so the response can be serialized.
    links = await _fetch_links(db, campaign_id, link_ids=[l.id for l in result["links"]])

    return DiscoveryResponse(
        campaign_id=campaign.id,
        status=result["status"],
        count=len(links),
        stats=DiscoveryStatsSchema(**result["stats"]),
        creators=[_to_creator_response(link) for link in links],
    )


async def _fetch_links(db: AsyncSession, campaign_id: str, link_ids: List[str]) -> List[CampaignInfluencer]:
    if not link_ids:
        return []
    result = await db.execute(
        select(CampaignInfluencer)
        .options(selectinload(CampaignInfluencer.influencer))
        .where(
            CampaignInfluencer.campaign_id == campaign_id,
            CampaignInfluencer.id.in_(link_ids),
        )
        .order_by(CampaignInfluencer.match_score.desc().nullslast())
    )
    return list(result.scalars().all())


@router.get(
    "/{campaign_id}/influencers",
    response_model=CampaignCreatorListResponse,
    summary="List creators already discovered for this campaign (reads PostgreSQL only)",
)
async def list_campaign_influencers(
    campaign_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=100),
    sort: str = Query("match_score", description="match_score | followers | engagement | avg_views | recent"),
    status: Optional[str] = Query(None, description="Filter by DISCOVERED | SHORTLISTED | REJECTED | CONTACTED"),
    min_subscribers: Optional[int] = Query(None, ge=0),
    max_subscribers: Optional[int] = Query(None, ge=0),
    min_engagement: Optional[float] = Query(None, ge=0),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _load_owned_campaign(db, campaign_id, current_user)

    base = (
        select(CampaignInfluencer)
        .join(Influencer, CampaignInfluencer.influencer_id == Influencer.id)
        .where(CampaignInfluencer.campaign_id == campaign_id)
    )

    if status and status.upper() != "ALL":
        base = base.where(CampaignInfluencer.status == status.upper())
    if min_subscribers is not None:
        base = base.where(Influencer.followers >= min_subscribers)
    if max_subscribers is not None:
        base = base.where(Influencer.followers <= max_subscribers)
    if min_engagement is not None:
        base = base.where(Influencer.engagement_rate >= min_engagement)
    if search:
        # Parameter-bound ILIKE; no string interpolation into SQL.
        pattern = f"%{search.strip()}%"
        base = base.where(
            Influencer.name.ilike(pattern)
            | Influencer.username.ilike(pattern)
            | Influencer.description.ilike(pattern)
        )

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = int(count_result.scalar_one() or 0)

    sort_column = SORT_FIELDS.get(sort, CampaignInfluencer.match_score)
    stmt = (
        base.options(selectinload(CampaignInfluencer.influencer))
        .order_by(sort_column.desc().nullslast())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await db.execute(stmt)
    links = list(result.scalars().all())

    return CampaignCreatorListResponse(
        campaign_id=campaign_id,
        count=len(links),
        total=total,
        page=page,
        limit=limit,
        creators=[_to_creator_response(link) for link in links],
    )


@router.get(
    "/{campaign_id}/influencers/{influencer_id}",
    response_model=CampaignCreatorResponse,
    summary="Get one discovered creator with its campaign match breakdown",
)
async def get_campaign_influencer(
    campaign_id: str,
    influencer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _load_owned_campaign(db, campaign_id, current_user)

    result = await db.execute(
        select(CampaignInfluencer)
        .options(selectinload(CampaignInfluencer.influencer))
        .where(
            CampaignInfluencer.campaign_id == campaign_id,
            CampaignInfluencer.influencer_id == influencer_id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise NotFoundException(detail="Creator has not been discovered for this campaign")

    return _to_creator_response(link)


@router.patch(
    "/{campaign_id}/influencers/{influencer_id}",
    response_model=CampaignCreatorResponse,
    summary="Update a creator's status within this campaign (persists shortlisting)",
)
async def update_campaign_influencer_status(
    campaign_id: str,
    influencer_id: str,
    payload: CampaignCreatorStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _load_owned_campaign(db, campaign_id, current_user)

    new_status = payload.status.upper()
    if new_status not in CampaignInfluencerStatus.ALL:
        raise InvalidRequestException(
            detail=f"Status must be one of: {', '.join(CampaignInfluencerStatus.ALL)}"
        )

    result = await db.execute(
        select(CampaignInfluencer)
        .options(selectinload(CampaignInfluencer.influencer))
        .where(
            CampaignInfluencer.campaign_id == campaign_id,
            CampaignInfluencer.influencer_id == influencer_id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise NotFoundException(detail="Creator has not been discovered for this campaign")

    link.status = new_status

    # Keep the cross-campaign shortlist flag in sync for the global Shortlist workspace.
    if new_status == CampaignInfluencerStatus.SHORTLISTED:
        link.influencer.shortlisted = True

        # Trigger Supervisor Outreach Agent if draft does not already exist for this creator
        existing_msg = await db.execute(
            select(OutreachMessage).where(
                OutreachMessage.campaign_id == campaign_id,
                OutreachMessage.influencer_id == influencer_id,
            )
        )
        if not existing_msg.scalars().first():
            supervisor = SupervisorAgent(db)
            campaign = await db.get(Campaign, campaign_id)
            if campaign:
                try:
                    await supervisor.run_outreach(
                        campaign=campaign,
                        user=current_user,
                        influencer_id=influencer_id,
                        trigger="shortlist_event",
                    )
                except Exception as exc:
                    logger.warning(
                        "Auto outreach generation on shortlist event failed for creator %s: %s",
                        influencer_id,
                        exc,
                    )
    elif new_status in (CampaignInfluencerStatus.DISCOVERED, CampaignInfluencerStatus.REJECTED):
        still_shortlisted = await db.execute(
            select(func.count())
            .select_from(CampaignInfluencer)
            .where(
                CampaignInfluencer.influencer_id == influencer_id,
                CampaignInfluencer.id != link.id,
                CampaignInfluencer.status == CampaignInfluencerStatus.SHORTLISTED,
            )
        )
        link.influencer.shortlisted = bool(still_shortlisted.scalar_one() or 0)

    await db.commit()

    logger.info(
        "Campaign %s creator %s status set to %s by user %s",
        campaign_id,
        influencer_id,
        new_status,
        current_user.id,
    )

    return _to_creator_response(link)
