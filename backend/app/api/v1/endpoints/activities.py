from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.campaign_activity import CampaignActivity
from app.models.user import User
from app.schemas.campaign import CampaignActivityResponse

router = APIRouter(prefix="/activities", tags=["Activities"])


@router.get("", response_model=List[CampaignActivityResponse], summary="List recent activities for current user")
async def list_user_activities(
    limit: int = Query(20, ge=1, le=100),
    campaign_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(CampaignActivity)
        .where(CampaignActivity.user_id == current_user.id)
    )
    if campaign_id:
        stmt = stmt.where(CampaignActivity.campaign_id == campaign_id)
    stmt = stmt.order_by(CampaignActivity.created_at.desc()).limit(limit)

    result = await db.execute(stmt)
    activities = result.scalars().all()
    return [CampaignActivityResponse.model_validate(a) for a in activities]
