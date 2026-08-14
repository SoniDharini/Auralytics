from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.campaign import Campaign
from app.models.approval import Approval
from app.models.user import User
from app.schemas.campaign import DashboardSummaryResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse, summary="Get dashboard summary for current user")
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Campaign).where(Campaign.owner_id == current_user.id)
    result = await db.execute(stmt)
    campaigns = result.scalars().all()

    total_campaigns = len(campaigns)
    active_campaigns = sum(1 for c in campaigns if c.status == "active")
    pending_campaigns = sum(1 for c in campaigns if c.status in ("planning", "draft", "pending_approval", "needs_attention"))
    completed_campaigns = sum(1 for c in campaigns if c.status == "completed")

    total_spend = sum(c.spend for c in campaigns)
    total_revenue = sum(c.revenue for c in campaigns)
    average_roas = (total_revenue / total_spend) if total_spend > 0 else 0.0

    # User pending approvals count (if user has approval records)
    pending_approvals = 0

    return DashboardSummaryResponse(
        total_campaigns=total_campaigns,
        active_campaigns=active_campaigns,
        pending_campaigns=pending_campaigns,
        completed_campaigns=completed_campaigns,
        total_spend=round(total_spend, 2),
        total_revenue=round(total_revenue, 2),
        average_roas=round(average_roas, 2),
        pending_approvals=pending_approvals,
    )
