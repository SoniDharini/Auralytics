from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.influencer import Influencer
from app.models.user import User
from app.schemas.influencer import InfluencerResponse
from app.services.influencer_ingestion_service import InfluencerIngestionService

router = APIRouter(prefix="/influencers", tags=["Influencers"])


@router.get("", response_model=List[InfluencerResponse], summary="List and filter discovered influencers")
async def list_influencers(
    platform: Optional[str] = Query(None),
    niche: Optional[str] = Query(None),
    shortlisted: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Influencer).order_by(desc(Influencer.followers))
    if platform and platform != "all":
        stmt = stmt.where(Influencer.platform == platform.lower())
    if shortlisted is not None:
        stmt = stmt.where(Influencer.shortlisted == shortlisted)

    result = await db.execute(stmt)
    influencers = result.scalars().all()

    # In-memory filtering for niche keywords and multi-field text search
    filtered = []
    for inf in influencers:
        if niche and niche.lower() != "all":
            niche_lower = niche.lower()
            niches_list = [n.lower() for n in (inf.niches or [])]
            if niche_lower not in niches_list and not any(niche_lower in n for n in niches_list):
                continue
        if search:
            s = search.lower()
            name_match = s in (inf.name or "").lower()
            user_match = s in (inf.username or "").lower()
            loc_match = s in (inf.location or "").lower()
            desc_match = s in (inf.description or "").lower()
            if not (name_match or user_match or loc_match or desc_match):
                continue
        filtered.append(InfluencerResponse.model_validate(inf))
        if len(filtered) >= limit:
            break

    return filtered


@router.get("/{influencer_id}", response_model=InfluencerResponse, summary="Get influencer by ID")
async def get_influencer(
    influencer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Influencer).where(Influencer.id == influencer_id)
    result = await db.execute(stmt)
    influencer = result.scalar_one_or_none()

    if not influencer:
        raise NotFoundException(detail=f"Influencer {influencer_id} not found")

    return InfluencerResponse.model_validate(influencer)


@router.post("/{influencer_id}/shortlist", response_model=InfluencerResponse, summary="Toggle influencer shortlist")
async def toggle_shortlist(
    influencer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Influencer).where(Influencer.id == influencer_id)
    result = await db.execute(stmt)
    influencer = result.scalar_one_or_none()

    if not influencer:
        raise NotFoundException(detail=f"Influencer {influencer_id} not found")

    influencer.shortlisted = not influencer.shortlisted
    await db.commit()
    await db.refresh(influencer)

    return InfluencerResponse.model_validate(influencer)


@router.post("/{influencer_id}/refresh", response_model=InfluencerResponse, summary="Refresh latest platform statistics for an influencer")
async def refresh_influencer_stats(
    influencer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InfluencerIngestionService()
    updated_inf = await service.refresh_influencer(db, influencer_id)
    if not updated_inf:
        raise NotFoundException(detail=f"Influencer {influencer_id} not found")
    return InfluencerResponse.model_validate(updated_inf)
