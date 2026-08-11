from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.agent_run import Agent, TimelineEvent
from app.models.user import User
from app.schemas.agent import AgentResponse, TimelineEventResponse

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("", response_model=List[AgentResponse], summary="List all autonomous agents")
async def list_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Agent)
    result = await db.execute(stmt)
    agents = result.scalars().all()
    return [AgentResponse.model_validate(a) for a in agents]


@router.get("/timeline", response_model=List[TimelineEventResponse], summary="Get agent activity timeline")
async def get_agent_timeline(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(TimelineEvent).order_by(TimelineEvent.created_at.desc())
    result = await db.execute(stmt)
    events = result.scalars().all()
    return [TimelineEventResponse.model_validate(e) for e in events]
