from typing import List, Optional
from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.supervisor import SupervisorAgent
from app.core.exceptions import InvalidRequestException, NotFoundException
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.campaign import Campaign
from app.models.campaign_influencer import CampaignInfluencer, CampaignInfluencerStatus
from app.models.outreach import OutreachMessage
from app.models.user import User
from app.schemas.agent_execution import AgentRunResponse, SupervisorStartResponse
from app.schemas.outreach import (
    OutreachAcceptanceRequest,
    OutreachGenerateRequest,
    OutreachNegotiateRequest,
    OutreachNegotiateResponse,
    OutreachRejectionRequest,
    OutreachResponse,
    OutreachStatusDecisionRequest,
    OutreachStatusUpdate,
)

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


@router.post("/{outreach_id}/negotiate", response_model=OutreachNegotiateResponse, summary="Analyze creator reply and generate negotiation follow-up")
async def negotiate_outreach(
    outreach_id: str,
    payload: OutreachNegotiateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(OutreachMessage).where(OutreachMessage.id == outreach_id)
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()
    if not message:
        raise NotFoundException(detail=f"Outreach message {outreach_id} not found")

    supervisor = SupervisorAgent(db)
    campaign = await supervisor.load_owned_campaign(message.campaign_id or "", current_user)

    res = await supervisor.run_negotiation(
        campaign=campaign,
        user=current_user,
        outreach_message_id=outreach_id,
        influencer_reply=payload.influencer_reply,
        user_instruction=payload.user_instruction,
        trigger="manual",
    )

    data = res.get("negotiation_data") or {}
    return OutreachNegotiateResponse(
        conversation_state=data.get("conversation_state") or "NEGOTIATING_PRICE",
        influencer_reply_summary=data.get("influencer_reply_summary") or "",
        extracted_terms=data.get("extracted_terms") or {},
        recommended_action=data.get("recommended_action") or "COUNTER_OFFER",
        subject=data.get("subject"),
        message=data.get("message") or "",
        short_dm=data.get("short_dm"),
        confidence=float(data.get("confidence") or 0.90),
        budget_constraint_warning=data.get("budget_constraint_warning"),
        outreach_message=OutreachResponse.model_validate(res["outreach_message"]) if res.get("outreach_message") else None,
    )


@router.post("/{outreach_id}/acceptance", response_model=OutreachResponse, summary="Save confirmed influencer collaboration acceptance details")
async def save_outreach_acceptance(
    outreach_id: str,
    payload: OutreachAcceptanceRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(OutreachMessage).where(OutreachMessage.id == outreach_id)
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()
    if not message:
        raise NotFoundException(detail=f"Outreach message {outreach_id} not found")

    supervisor = SupervisorAgent(db)
    campaign = await supervisor.load_owned_campaign(message.campaign_id or "", current_user)

    message.response_status = "ACCEPTED"
    message.status = "ACCEPTED"
    message.response_text = payload.response_notes
    message.final_amount = payload.final_amount
    message.currency = payload.currency
    message.deliverables = payload.deliverables
    message.timeline_start = payload.timeline_start
    message.timeline_end = payload.timeline_end
    message.additional_terms = payload.additional_terms

    terms_dict = {
        "agreed_rate": payload.final_amount,
        "final_amount": payload.final_amount,
        "currency": payload.currency,
        "deliverables": payload.deliverables,
        "timeline_start": payload.timeline_start,
        "timeline_end": payload.timeline_end,
        "additional_terms": payload.additional_terms or "",
    }
    current_terms = dict(message.extracted_terms or {})
    current_terms.update(terms_dict)
    message.extracted_terms = current_terms

    history = list(message.conversation_history or [])
    history.append({
        "sender": "BRAND",
        "message": f"Confirmed collaboration acceptance. Final amount: {payload.currency} {payload.final_amount:,.2f}. Deliverables: {', '.join(payload.deliverables)}.",
        "message_type": "DEAL_ACCEPTED",
        "terms": terms_dict,
    })
    message.conversation_history = history

    # Update CampaignInfluencer status
    if message.campaign_id and message.influencer_id:
        link_stmt = select(CampaignInfluencer).where(
            CampaignInfluencer.campaign_id == message.campaign_id,
            CampaignInfluencer.influencer_id == message.influencer_id,
        )
        link_res = await db.execute(link_stmt)
        link = link_res.scalar_one_or_none()
        if link:
            link.status = CampaignInfluencerStatus.ACCEPTED

    # Record Activities
    from app.models.campaign_activity import CampaignActivity
    act1 = CampaignActivity(
        user_id=current_user.id,
        campaign_id=campaign.id,
        activity_type="collaboration_accepted",
        title=f"Collaboration accepted by {message.influencer_name}",
        description=f"Creator agreed to collaborate. Status updated to ACCEPTED.",
    )
    act2 = CampaignActivity(
        user_id=current_user.id,
        campaign_id=campaign.id,
        activity_type="amount_recorded",
        title=f"Final collaboration amount recorded: {payload.currency} {payload.final_amount:,.2f}",
        description=f"Confirmed {len(payload.deliverables)} deliverable(s) for flight {payload.timeline_start} to {payload.timeline_end}.",
    )
    db.add_all([act1, act2])

    await db.commit()
    await db.refresh(message)
    return OutreachResponse.model_validate(message)


@router.post("/{outreach_id}/rejection", response_model=OutreachResponse, summary="Record influencer rejection reason and notes")
async def save_outreach_rejection(
    outreach_id: str,
    payload: OutreachRejectionRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(OutreachMessage).where(OutreachMessage.id == outreach_id)
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()
    if not message:
        raise NotFoundException(detail=f"Outreach message {outreach_id} not found")

    supervisor = SupervisorAgent(db)
    campaign = await supervisor.load_owned_campaign(message.campaign_id or "", current_user)

    message.response_status = "REJECTED"
    message.status = "REJECTED"
    message.rejection_reason = payload.rejection_reason
    message.rejection_notes = payload.rejection_notes

    history = list(message.conversation_history or [])
    history.append({
        "sender": "BRAND",
        "message": f"Recorded rejection. Reason: {payload.rejection_reason}. Notes: {payload.rejection_notes or 'None'}",
        "message_type": "DEAL_REJECTED",
    })
    message.conversation_history = history

    # Update CampaignInfluencer status
    if message.campaign_id and message.influencer_id:
        link_stmt = select(CampaignInfluencer).where(
            CampaignInfluencer.campaign_id == message.campaign_id,
            CampaignInfluencer.influencer_id == message.influencer_id,
        )
        link_res = await db.execute(link_stmt)
        link = link_res.scalar_one_or_none()
        if link:
            link.status = CampaignInfluencerStatus.REJECTED

    # Record Activity
    from app.models.campaign_activity import CampaignActivity
    act = CampaignActivity(
        user_id=current_user.id,
        campaign_id=campaign.id,
        activity_type="collaboration_rejected",
        title=f"Collaboration rejected: {message.influencer_name}",
        description=f"Reason: {payload.rejection_reason}" + (f" | Notes: {payload.rejection_notes}" if payload.rejection_notes else ""),
    )
    db.add(act)

    await db.commit()
    await db.refresh(message)
    return OutreachResponse.model_validate(message)


@router.post("/{outreach_id}/generate-contract", response_model=SupervisorStartResponse, summary="Human-controlled trigger to run Contract Agent for accepted creator")
async def generate_contract_for_outreach(
    outreach_id: str,
    payload: Optional[ContractAnalyzeRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(OutreachMessage).where(OutreachMessage.id == outreach_id)
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()
    if not message:
        raise NotFoundException(detail=f"Outreach message {outreach_id} not found")

    if message.response_status != "ACCEPTED" and message.status != "ACCEPTED":
        raise InvalidRequestException(
            detail="Cannot generate contract: Influencer response must be explicitly ACCEPTED first."
        )

    if not message.final_amount or float(message.final_amount) <= 0:
        raise InvalidRequestException(
            detail="Please complete and save the collaboration details before generating the contract."
        )

    supervisor = SupervisorAgent(db)
    campaign = await supervisor.load_owned_campaign(message.campaign_id or "", current_user)

    agreed_terms = {
        "agreed_rate": float(message.final_amount),
        "final_amount": float(message.final_amount),
        "currency": message.currency or "INR",
        "deliverables": message.deliverables or ["1 Dedicated collaboration video"],
        "timeline_start": message.timeline_start or campaign.start_date or "Launch Date",
        "timeline_end": message.timeline_end or campaign.end_date or "Launch + 30",
        "additional_terms": message.additional_terms or "",
    }

    confirmed_terms_dict = None
    if payload and payload.confirmed_terms:
        confirmed_terms_dict = payload.confirmed_terms.model_dump()
    elif payload and payload.custom_terms:
        confirmed_terms_dict = payload.custom_terms

    result = await supervisor.run_contract(
        campaign=campaign,
        user=current_user,
        influencer_id=message.influencer_id,
        agreed_terms=agreed_terms,
        confirmed_terms=confirmed_terms_dict,
        contract_text=payload.contract_text if payload else None,
        trigger="manual",
    )

    agent_run = result.get("agent_run")
    contract_obj = result.get("contract")
    contract_id = contract_obj.id if contract_obj else message.contract_id

    return SupervisorStartResponse(
        campaignId=result["campaign_id"],
        workflowState=result["workflow_state"],
        next=result.get("next"),
        message=result["message"],
        agentRun=AgentRunResponse.model_validate(agent_run) if agent_run else None,
        contractId=contract_id,
    )


@router.post("/{outreach_id}/decision", response_model=OutreachResponse, summary="Confirm influencer decision (ACCEPTED / DECLINED / NEGOTIATING)")
async def decide_outreach_status(
    outreach_id: str,
    payload: OutreachStatusDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(OutreachMessage).where(OutreachMessage.id == outreach_id)
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()
    if not message:
        raise NotFoundException(detail=f"Outreach message {outreach_id} not found")

    new_status = payload.status.upper()
    if new_status not in ("ACCEPTED", "DECLINED", "REJECTED", "NEGOTIATING", "CONTACTED", "SENT", "READY"):
        raise InvalidRequestException(detail="Status must be one of: ACCEPTED, DECLINED, REJECTED, NEGOTIATING, CONTACTED, SENT, READY")

    message.status = new_status
    message.response_status = new_status if new_status in ("ACCEPTED", "DECLINED", "REJECTED") else message.response_status
    if payload.agreed_terms:
        current_terms = dict(message.extracted_terms or {})
        current_terms.update(payload.agreed_terms)
        message.extracted_terms = current_terms

    # Update conversation history entry
    history = list(message.conversation_history or [])
    history.append({
        "sender": "BRAND",
        "message": f"User marked deal as {new_status}." + (f" Note: {payload.note}" if payload.note else ""),
        "message_type": f"DEAL_{new_status}",
        "terms": message.extracted_terms or {},
    })
    message.conversation_history = history

    # Update CampaignInfluencer status
    if message.campaign_id and message.influencer_id:
        link_stmt = select(CampaignInfluencer).where(
            CampaignInfluencer.campaign_id == message.campaign_id,
            CampaignInfluencer.influencer_id == message.influencer_id,
        )
        link_res = await db.execute(link_stmt)
        link = link_res.scalar_one_or_none()
        if link:
            if new_status == "ACCEPTED":
                link.status = CampaignInfluencerStatus.ACCEPTED
            elif new_status in ("DECLINED", "REJECTED"):
                link.status = CampaignInfluencerStatus.DECLINED
            elif new_status == "NEGOTIATING":
                link.status = CampaignInfluencerStatus.NEGOTIATING

    await db.commit()
    await db.refresh(message)
    return OutreachResponse.model_validate(message)


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
    if data.negotiation_state is not None:
        message.negotiation_state = data.negotiation_state
    if data.extracted_terms is not None:
        message.extracted_terms = data.extracted_terms

    await db.commit()
    await db.refresh(message)
    return OutreachResponse.model_validate(message)

