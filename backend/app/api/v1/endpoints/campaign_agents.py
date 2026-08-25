"""Campaign-scoped Supervisor / Strategy agent endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.supervisor import SupervisorAgent
from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.agent_execution import AgentRun
from app.models.campaign import Campaign
from app.models.campaign_strategy import CampaignStrategy
from app.models.user import User
from app.schemas.agent_execution import (
    AgentRunResponse,
    CampaignStrategyResponse,
    SupervisorStartResponse,
)

router = APIRouter(prefix="/campaigns/{campaign_id}/agents", tags=["Campaign Agents"])


def _serialize_run(run: Optional[AgentRun]) -> Optional[AgentRunResponse]:
    if run is None:
        return None
    return AgentRunResponse.model_validate(run)


@router.post("/start", response_model=SupervisorStartResponse, summary="Supervisor: advance workflow")
async def start_supervisor(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    supervisor = SupervisorAgent(db)
    result = await supervisor.start(campaign_id=campaign_id, user=current_user, trigger="manual")
    return SupervisorStartResponse(
        campaignId=result["campaign_id"],
        workflowState=result["workflow_state"],
        next=result.get("next"),
        message=result["message"],
        agentRun=_serialize_run(result.get("agent_run")),
    )


@router.post("/strategy", response_model=SupervisorStartResponse, summary="Run Strategy Agent")
async def run_strategy_agent(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    supervisor = SupervisorAgent(db)
    campaign = await supervisor.load_owned_campaign(campaign_id, current_user)
    result = await supervisor.run_strategy(campaign=campaign, user=current_user, trigger="manual")
    return SupervisorStartResponse(
        campaignId=result["campaign_id"],
        workflowState=result["workflow_state"],
        next=result.get("next"),
        message=result["message"],
        agentRun=_serialize_run(result.get("agent_run")),
    )


@router.post("/discovery", response_model=SupervisorStartResponse, summary="Run Discovery Agent")
async def run_discovery_agent(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    supervisor = SupervisorAgent(db)
    campaign = await supervisor.load_owned_campaign(campaign_id, current_user)
    result = await supervisor.run_discovery(campaign=campaign, user=current_user, trigger="manual")
    return SupervisorStartResponse(
        campaignId=result["campaign_id"],
        workflowState=result["workflow_state"],
        next=result.get("next"),
        message=result["message"],
        agentRun=_serialize_run(result.get("agent_run")),
    )


@router.post("/outreach", response_model=SupervisorStartResponse, summary="Run Outreach Agent")
async def run_outreach_agent(
    campaign_id: str,
    influencer_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    supervisor = SupervisorAgent(db)
    campaign = await supervisor.load_owned_campaign(campaign_id, current_user)
    result = await supervisor.run_outreach(
        campaign=campaign, user=current_user, influencer_id=influencer_id, trigger="manual"
    )
    return SupervisorStartResponse(
        campaignId=result["campaign_id"],
        workflowState=result["workflow_state"],
        next=result.get("next"),
        message=result["message"],
        agentRun=_serialize_run(result.get("agent_run")),
    )


@router.get("/runs", response_model=List[AgentRunResponse], summary="List agent runs for campaign")
async def list_campaign_agent_runs(
    campaign_id: str,
    agent_name: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    owned = await db.execute(
        select(Campaign.id).where(Campaign.id == campaign_id, Campaign.owner_id == current_user.id)
    )
    if owned.scalar_one_or_none() is None:
        raise NotFoundException(detail="Campaign not found")

    stmt = select(AgentRun).where(
        AgentRun.campaign_id == campaign_id,
        AgentRun.user_id == current_user.id,
    )
    if agent_name:
        stmt = stmt.where(AgentRun.agent_name == agent_name)
    stmt = stmt.order_by(AgentRun.created_at.desc())
    result = await db.execute(stmt)
    runs = result.scalars().all()
    return [AgentRunResponse.model_validate(r) for r in runs]


@router.get("/strategy", response_model=Optional[CampaignStrategyResponse], summary="Latest campaign strategy")
async def get_latest_strategy(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    owned = await db.execute(
        select(Campaign.id).where(Campaign.id == campaign_id, Campaign.owner_id == current_user.id)
    )
    if owned.scalar_one_or_none() is None:
        raise NotFoundException(detail="Campaign not found")

    stmt = (
        select(CampaignStrategy)
        .where(CampaignStrategy.campaign_id == campaign_id)
        .order_by(CampaignStrategy.version.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    strategy = result.scalar_one_or_none()
    if not strategy:
        return None
    return CampaignStrategyResponse.model_validate(strategy)


# Also expose a global agent-run fetch under /agents for Agent Center
runs_router = APIRouter(prefix="/agent-runs", tags=["Agent Runs"])


@runs_router.get("/{run_id}", response_model=AgentRunResponse, summary="Get one agent run")
async def get_agent_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AgentRun).where(AgentRun.id == run_id, AgentRun.user_id == current_user.id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise NotFoundException(detail="Agent run not found")
    return AgentRunResponse.model_validate(run)


@runs_router.get("", response_model=List[AgentRunResponse], summary="List my agent runs")
async def list_my_agent_runs(
    limit: int = Query(50, ge=1, le=200),
    agent_name: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(AgentRun).where(AgentRun.user_id == current_user.id)
    if agent_name:
        stmt = stmt.where(AgentRun.agent_name == agent_name)
    stmt = stmt.order_by(AgentRun.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    runs = result.scalars().all()
    return [AgentRunResponse.model_validate(r) for r in runs]
