from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.influencer import Influencer
from app.models.user import User
from app.schemas.influencer import InfluencerResponse

router = APIRouter(prefix="/influencers", tags=["Influencers"])


@router.get("", response_model=List[InfluencerResponse], summary="List and filter influencers")
async def list_influencers(
    platform: Optional[str] = Query(None),
    niche: Optional[str] = Query(None),
    shortlisted: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Influencer)
    if platform and platform != "all":
        stmt = stmt.where(Influencer.platform == platform)
    if shortlisted is not None:
        stmt = stmt.where(Influencer.shortlisted == shortlisted)

    result = await db.execute(stmt)
    influencers = result.scalars().all()

    # Search filter in Python for rich nested/niche search
    filtered = []
    for inf in influencers:
        if niche and niche.lower() not in [n.lower() for n in inf.niches]:
            continue
        if search:
            s = search.lower()
            if (
                s not in inf.name.lower()
                and s not in inf.username.lower()
                and s not in inf.location.lower()
            ):
                continue
        filtered.append(InfluencerResponse.model_validate(inf))

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
