from typing import List, Optional
from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.supervisor import SupervisorAgent
from app.core.exceptions import InvalidRequestException, NotFoundException
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.campaign import Campaign
from app.models.contract import Contract
from app.models.user import User
from app.schemas.agent_execution import AgentRunResponse, SupervisorStartResponse
from app.schemas.contract import (
    ContractAnalyzeRequest,
    ContractApprovalRequest,
    ContractBodyUpdateRequest,
    ContractChangeRequest,
    ContractReadinessResponse,
    ContractRejectRequest,
    ContractResponse,
)
from app.services.contract_readiness_service import ContractReadinessService

router = APIRouter(prefix="/contracts", tags=["Contracts"])


async def _load_owned_contract(contract_id: str, user: User, db: AsyncSession) -> tuple[Contract, Optional[Campaign]]:
    """Helper to verify campaign ownership for a contract."""
    stmt = select(Contract).where(Contract.id == contract_id)
    res = await db.execute(stmt)
    contract = res.scalar_one_or_none()
    if not contract:
        raise NotFoundException(detail=f"Contract {contract_id} not found")

    campaign = None
    if contract.campaign_id:
        camp_stmt = select(Campaign).where(
            Campaign.id == contract.campaign_id,
            Campaign.owner_id == user.id,
        )
        camp_res = await db.execute(camp_stmt)
        campaign = camp_res.scalar_one_or_none()
        if not campaign:
            raise NotFoundException(detail="Campaign not found or access denied")
    else:
        camp_stmt = select(Campaign).where(Campaign.owner_id == user.id).limit(1)
        camp_res = await db.execute(camp_stmt)
        campaign = camp_res.scalar_one_or_none()

    return contract, campaign


@router.get("", response_model=List[ContractResponse], summary="List all contracts for current user")
async def list_contracts(
    campaign_id: Optional[str] = Query(None),
    influencer_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Fetch user's campaign IDs to enforce strict tenant isolation
    user_campaigns_stmt = select(Campaign.id).where(Campaign.owner_id == current_user.id)
    user_campaigns_res = await db.execute(user_campaigns_stmt)
    user_campaign_ids = [c for c in user_campaigns_res.scalars().all()]

    if not user_campaign_ids:
        return []

    stmt = select(Contract).where(Contract.campaign_id.in_(user_campaign_ids))
    if campaign_id:
        if campaign_id not in user_campaign_ids:
            return []
        stmt = stmt.where(Contract.campaign_id == campaign_id)
    if influencer_id:
        stmt = stmt.where(Contract.influencer_id == influencer_id)
    if status and status != "all":
        stmt = stmt.where(Contract.status == status)
    stmt = stmt.order_by(Contract.created_at.desc())

    result = await db.execute(stmt)
    contracts = result.scalars().all()
    return [ContractResponse.model_validate(c) for c in contracts]


@router.get("/readiness", response_model=ContractReadinessResponse, summary="Check contract readiness for a creator")
async def check_contract_readiness(
    campaign_id: str = Query(..., description="Campaign ID"),
    influencer_id: str = Query(..., description="Influencer ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    readiness_service = ContractReadinessService(db)
    result = await readiness_service.check_readiness(
        campaign_id=campaign_id,
        influencer_id=influencer_id,
        user=current_user,
    )
    return ContractReadinessResponse.model_validate(result.to_dict())


@router.get("/campaign-readiness/{campaign_id}", response_model=List[ContractReadinessResponse], summary="List contract readiness for all creators in a campaign")
async def list_campaign_contract_readiness(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    readiness_service = ContractReadinessService(db)
    results = await readiness_service.list_campaign_creators_readiness(
        campaign_id=campaign_id,
        user=current_user,
    )
    return [ContractReadinessResponse.model_validate(r) for r in results]


@router.get("/{contract_id}", response_model=ContractResponse, summary="Get contract by ID")
async def get_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract, _ = await _load_owned_contract(contract_id, current_user, db)
    return ContractResponse.model_validate(contract)


@router.post("/analyze/{campaign_id}", response_model=SupervisorStartResponse, summary="Run Contract Agent analysis for accepted creator")
async def analyze_contract(
    campaign_id: str,
    payload: ContractAnalyzeRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    supervisor = SupervisorAgent(db)
    campaign = await supervisor.load_owned_campaign(campaign_id, current_user)

    confirmed_dict = payload.confirmed_terms.model_dump() if payload.confirmed_terms else payload.custom_terms

    result = await supervisor.run_contract(
        campaign=campaign,
        user=current_user,
        influencer_id=payload.influencer_id,
        agreed_terms=payload.custom_terms,
        confirmed_terms=confirmed_dict,
        contract_text=payload.contract_text,
        trigger="manual",
    )

    agent_run = result.get("agent_run")
    contract_obj = result.get("contract")
    contract_id = contract_obj.id if contract_obj else None

    return SupervisorStartResponse(
        campaignId=result["campaign_id"],
        workflowState=result["workflow_state"],
        next=result.get("next"),
        message=result["message"],
        agentRun=AgentRunResponse.model_validate(agent_run) if agent_run else None,
        contractId=contract_id,
    )


@router.post("/{contract_id}/approve", response_model=ContractResponse, summary="Human approval of creator contract")
async def approve_contract_endpoint(
    contract_id: str,
    payload: Optional[ContractApprovalRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract, campaign = await _load_owned_contract(contract_id, current_user, db)
    if not campaign:
        raise NotFoundException(detail="Campaign not found")

    supervisor = SupervisorAgent(db)
    notes = payload.notes if payload else None
    approved = await supervisor.approve_contract(
        campaign=campaign,
        user=current_user,
        contract=contract,
        notes=notes,
    )
    return ContractResponse.model_validate(approved)


@router.post("/{contract_id}/request-changes", response_model=ContractResponse, summary="Human request for changes on contract")
async def request_contract_changes_endpoint(
    contract_id: str,
    payload: ContractChangeRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract, campaign = await _load_owned_contract(contract_id, current_user, db)
    if not campaign:
        raise NotFoundException(detail="Campaign not found")

    supervisor = SupervisorAgent(db)
    updated = await supervisor.request_contract_changes(
        campaign=campaign,
        user=current_user,
        contract=contract,
        requested_changes=payload.requested_changes,
        reason=payload.reason,
    )
    return ContractResponse.model_validate(updated)


@router.post("/{contract_id}/reject", response_model=ContractResponse, summary="Human rejection of creator contract")
async def reject_contract_endpoint(
    contract_id: str,
    payload: ContractRejectRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract, campaign = await _load_owned_contract(contract_id, current_user, db)
    if not campaign:
        raise NotFoundException(detail="Campaign not found")

    supervisor = SupervisorAgent(db)
    rejected = await supervisor.reject_contract(
        campaign=campaign,
        user=current_user,
        contract=contract,
        reason=payload.reason,
        notes=payload.notes,
    )
    return ContractResponse.model_validate(rejected)


@router.patch("/{contract_id}/body", response_model=ContractResponse, summary="Update contract agreement text")
async def update_contract_body(
    contract_id: str,
    payload: ContractBodyUpdateRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract, campaign = await _load_owned_contract(contract_id, current_user, db)
    contract.contract_body = payload.contract_body
    await db.flush()

    if payload.reanalyze and campaign and contract.influencer_id:
        supervisor = SupervisorAgent(db)
        await supervisor.run_contract(
            campaign=campaign,
            user=current_user,
            influencer_id=contract.influencer_id,
            contract_text=payload.contract_body,
            trigger="manual",
        )

    await db.commit()
    await db.refresh(contract)
    return ContractResponse.model_validate(contract)

