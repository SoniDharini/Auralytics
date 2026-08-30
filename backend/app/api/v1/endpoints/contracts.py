from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.contract import Contract
from app.models.user import User
from app.schemas.contract import ContractResponse

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@router.get("", response_model=List[ContractResponse], summary="List all contracts")
async def list_contracts(
    campaign_id: Optional[str] = Query(None),
    influencer_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Contract)
    if campaign_id:
        stmt = stmt.where(Contract.campaign_id == campaign_id)
    if influencer_id:
        stmt = stmt.where(Contract.influencer_id == influencer_id)
    if status:
        stmt = stmt.where(Contract.status == status)
    stmt = stmt.order_by(Contract.created_at.desc())

    result = await db.execute(stmt)
    contracts = result.scalars().all()
    return [ContractResponse.model_validate(c) for c in contracts]


@router.get("/{contract_id}", response_model=ContractResponse, summary="Get contract by ID")
async def get_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Contract).where(Contract.id == contract_id)
    result = await db.execute(stmt)
    contract = result.scalar_one_or_none()

    if not contract:
        raise NotFoundException(detail=f"Contract {contract_id} not found")

    return ContractResponse.model_validate(contract)
