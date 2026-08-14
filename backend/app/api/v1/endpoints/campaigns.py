import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.campaign import Campaign
from app.models.campaign_activity import CampaignActivity
from app.models.influencer import Influencer
from app.models.user import User
from app.schemas.campaign import (
    CampaignActivityResponse,
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
)
from app.schemas.influencer import (
    InfluencerFetchRequest,
    InfluencerFetchResponse,
    InfluencerResponse,
    ProviderResultSchema,
)
from app.services.influencer_ingestion_service import InfluencerIngestionService

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.get("", response_model=List[CampaignResponse], summary="List all campaigns for current user")
async def list_campaigns(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Campaign).where(Campaign.owner_id == current_user.id)
    if status and status != "all":
        stmt = stmt.where(Campaign.status == status)

    result = await db.execute(stmt)
    campaigns = result.scalars().all()
    return [CampaignResponse.model_validate(c) for c in campaigns]


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED, summary="Create a new campaign")
async def create_campaign(
    data: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    camp_id = f"camp-{uuid.uuid4().hex[:8]}"

    campaign = Campaign(
        id=camp_id,
        owner_id=current_user.id,
        name=data.name,
        brand=data.brand,
        status=data.status,
        health=data.health,
        budget=data.budget,
        spend=0.0,
        revenue=0.0,
        roas=0.0,
        influencers=0,
        progress=0,
        start_date=data.start_date,
        end_date=data.end_date,
        conversions=0,
        reach=0,
        objective=data.objective,
        description=data.description,
        campaign_types=data.campaign_types,
        target_locations=data.target_locations,
        target_age_min=data.target_age_min,
        target_age_max=data.target_age_max,
        target_gender=data.target_gender,
        interests=data.interests,
        languages=data.languages,
        platforms=data.platforms,
        creator_tiers=data.creator_tiers,
        budget_allocation=data.budget_allocation,
        primary_kpi=data.primary_kpi,
        target_roas=data.target_roas,
        target_cpa=data.target_cpa,
    )
    db.add(campaign)

    activity = CampaignActivity(
        id=f"act-{uuid.uuid4().hex[:8]}",
        user_id=current_user.id,
        campaign_id=camp_id,
        activity_type="CAMPAIGN_CREATED",
        title=f"Campaign '{campaign.name}' created",
        description=f"Created campaign for brand '{campaign.brand}' with budget ₹{campaign.budget:,.0f}.",
        metadata_json={"campaign_name": campaign.name, "brand": campaign.brand, "budget": campaign.budget},
    )
    db.add(activity)

    await db.commit()
    await db.refresh(campaign)
    return CampaignResponse.model_validate(campaign)


@router.get("/{campaign_id}", response_model=CampaignResponse, summary="Get a campaign by ID")
async def get_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id,
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise NotFoundException(detail=f"Campaign {campaign_id} not found")

    return CampaignResponse.model_validate(campaign)


@router.patch("/{campaign_id}", response_model=CampaignResponse, summary="Update a campaign")
async def update_campaign(
    campaign_id: str,
    data: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id,
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise NotFoundException(detail=f"Campaign {campaign_id} not found")

    old_budget = campaign.budget
    old_status = campaign.status

    update_dict = data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(campaign, field, value)

    # Determine activity description
    if "status" in update_dict and update_dict["status"] != old_status:
        activity_type = "CAMPAIGN_STATUS_CHANGED"
        title = f"Campaign '{campaign.name}' status changed to {campaign.status.upper()}"
        description = f"Status transitioned from {old_status} to {campaign.status}."
    elif "budget" in update_dict and update_dict["budget"] != old_budget:
        activity_type = "CAMPAIGN_UPDATED"
        title = f"Campaign '{campaign.name}' budget updated"
        description = f"Budget updated from ₹{old_budget:,.0f} to ₹{campaign.budget:,.0f}."
    else:
        activity_type = "CAMPAIGN_UPDATED"
        title = f"Campaign '{campaign.name}' updated"
        fields_str = ", ".join(update_dict.keys())
        description = f"Modified fields: {fields_str}."

    activity = CampaignActivity(
        id=f"act-{uuid.uuid4().hex[:8]}",
        user_id=current_user.id,
        campaign_id=campaign.id,
        activity_type=activity_type,
        title=title,
        description=description,
        metadata_json=update_dict,
    )
    db.add(activity)

    await db.commit()
    await db.refresh(campaign)
    return CampaignResponse.model_validate(campaign)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a campaign")
async def delete_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id,
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise NotFoundException(detail=f"Campaign {campaign_id} not found")

    camp_name = campaign.name

    # Record user activity before deleting campaign
    activity = CampaignActivity(
        id=f"act-{uuid.uuid4().hex[:8]}",
        user_id=current_user.id,
        campaign_id=None,
        activity_type="CAMPAIGN_DELETED",
        title=f"Campaign '{camp_name}' deleted",
        description=f"Campaign '{camp_name}' (ID: {campaign_id}) was permanently removed.",
        metadata_json={"deleted_campaign_id": campaign_id, "deleted_campaign_name": camp_name},
    )
    db.add(activity)

    await db.delete(campaign)
    await db.commit()


@router.get(
    "/{campaign_id}/activities",
    response_model=List[CampaignActivityResponse],
    summary="Get activities for a campaign",
)
async def get_campaign_activities(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify campaign belongs to current user
    camp_stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id,
    )
    camp_res = await db.execute(camp_stmt)
    if not camp_res.scalar_one_or_none():
        raise NotFoundException(detail=f"Campaign {campaign_id} not found")

    stmt = (
        select(CampaignActivity)
        .where(
            CampaignActivity.campaign_id == campaign_id,
            CampaignActivity.user_id == current_user.id,
        )
        .order_by(CampaignActivity.created_at.desc())
    )
    result = await db.execute(stmt)
    activities = result.scalars().all()
    return [CampaignActivityResponse.model_validate(a) for a in activities]


@router.post(
    "/{campaign_id}/fetch-influencers",
    response_model=InfluencerFetchResponse,
    summary="Acquire real creator data from social platforms for this campaign",
)
async def fetch_campaign_influencers(
    campaign_id: str,
    payload: Optional[InfluencerFetchRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify campaign belongs to current user
    camp_stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id,
    )
    camp_res = await db.execute(camp_stmt)
    campaign = camp_res.scalar_one_or_none()
    if not campaign:
        raise NotFoundException(detail=f"Campaign {campaign_id} not found")

    service = InfluencerIngestionService()
    res = await service.ingest_for_campaign(
        db=db,
        campaign=campaign,
        user_id=current_user.id,
        requested_platforms=payload.platforms if payload else None,
        limit_per_platform=payload.limit if payload else 25,
        force_refresh=payload.force_refresh if payload else False,
    )

    # Fetch real influencers currently stored in database matching platform
    inf_stmt = select(Influencer)
    inf_res = await db.execute(inf_stmt)
    db_influencers = inf_res.scalars().all()

    providers_dict = {
        k: ProviderResultSchema(
            status=v.get("status", "unknown"),
            fetched=v.get("fetched", 0),
            created=v.get("created", 0),
            updated=v.get("updated", 0),
            message=v.get("message"),
        )
        for k, v in res.get("providers", {}).items()
    }

    return InfluencerFetchResponse(
        campaign_id=campaign.id,
        status=res.get("status", "completed"),
        total_discovered=res.get("total_discovered", 0),
        providers=providers_dict,
        influencers=[InfluencerResponse.model_validate(i) for i in db_influencers],
    )
