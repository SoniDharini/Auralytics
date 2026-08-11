import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.campaign import Campaign
from app.models.user import User
from app.schemas.campaign import CampaignCreate, CampaignResponse, CampaignUpdate

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.get("", response_model=List[CampaignResponse], summary="List all campaigns")
async def list_campaigns(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Campaign)
    if status:
        stmt = stmt.where(Campaign.status == status)
    stmt = stmt.order_by(Campaign.created_at.desc())

    result = await db.execute(stmt)
    campaigns = result.scalars().all()
    return [CampaignResponse.model_validate(c) for c in campaigns]


@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new campaign",
)
async def create_campaign(
    data: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    campaign = Campaign(
        id=f"camp-{uuid.uuid4().hex[:8]}",
        owner_id=current_user.id,
        name=data.name,
        brand=data.brand,
        budget=data.budget,
        objective=data.objective,
        start_date=data.start_date,
        end_date=data.end_date,
        status=data.status,
        health=data.health,
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
    await db.commit()
    await db.refresh(campaign)

    return CampaignResponse.model_validate(campaign)


@router.get("/{campaign_id}", response_model=CampaignResponse, summary="Get campaign details by ID")
async def get_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Campaign).where(Campaign.id == campaign_id)
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise NotFoundException(detail=f"Campaign {campaign_id} not found")

    return CampaignResponse.model_validate(campaign)


@router.patch("/{campaign_id}", response_model=CampaignResponse, summary="Update campaign")
async def update_campaign(
    campaign_id: str,
    data: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Campaign).where(Campaign.id == campaign_id)
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise NotFoundException(detail=f"Campaign {campaign_id} not found")

    update_dict = data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(campaign, field, value)

    await db.commit()
    await db.refresh(campaign)
    return CampaignResponse.model_validate(campaign)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a campaign")
async def delete_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Campaign).where(Campaign.id == campaign_id)
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise NotFoundException(detail=f"Campaign {campaign_id} not found")

    await db.delete(campaign)
    await db.commit()
