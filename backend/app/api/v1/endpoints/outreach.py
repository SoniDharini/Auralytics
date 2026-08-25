from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.supervisor import SupervisorAgent
from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.outreach import OutreachMessage
from app.models.user import User
from app.schemas.agent_execution import AgentRunResponse, SupervisorStartResponse
from app.schemas.outreach import OutreachGenerateRequest, OutreachResponse, OutreachStatusUpdate

router = APIRouter(prefix="/outreach", tags=["Outreach"])


@router.get("", response_model=List[OutreachResponse], summary="List outreach messages")
async def list_outreach(
    campaign_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(OutreachMessage)
    if campaign_id:
        stmt = stmt.where(OutreachMessage.campaign_id == campaign_id)
    if status and status != "all":
        stmt = stmt.where(OutreachMessage.status == status)
    stmt = stmt.order_by(OutreachMessage.created_at.desc())

    result = await db.execute(stmt)
    messages = result.scalars().all()
    return [OutreachResponse.model_validate(m) for m in messages]


@router.post("/generate/{campaign_id}", response_model=SupervisorStartResponse, summary="Generate outreach message for campaign/creator")
async def generate_outreach(
    campaign_id: str,
    payload: Optional[OutreachGenerateRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    supervisor = SupervisorAgent(db)
    campaign = await supervisor.load_owned_campaign(campaign_id, current_user)
    inf_id = payload.influencer_id if payload else None
    result = await supervisor.run_outreach(
        campaign=campaign, user=current_user, influencer_id=inf_id, trigger="manual"
    )
    agent_run = result.get("agent_run")
    return SupervisorStartResponse(
        campaignId=result["campaign_id"],
        workflowState=result["workflow_state"],
        next=result.get("next"),
        message=result["message"],
        agentRun=AgentRunResponse.model_validate(agent_run) if agent_run else None,
    )


@router.patch("/{outreach_id}", response_model=OutreachResponse, summary="Update outreach message or status")
async def update_outreach(
    outreach_id: str,
    data: OutreachStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(OutreachMessage).where(OutreachMessage.id == outreach_id)
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()

    if not message:
        raise NotFoundException(detail=f"Outreach message {outreach_id} not found")

    message.status = data.status
    if data.reply is not None:
        message.reply = data.reply
    if data.subject is not None:
        message.subject = data.subject
    if data.body is not None:
        message.body = data.body
    if data.short_dm is not None:
        message.short_dm = data.short_dm

    await db.commit()
    await db.refresh(message)
    return OutreachResponse.model_validate(message)
