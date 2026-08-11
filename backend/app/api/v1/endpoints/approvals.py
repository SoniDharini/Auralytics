from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.approval import Approval
from app.models.user import User
from app.schemas.approval import ApprovalDecisionRequest, ApprovalResponse

router = APIRouter(prefix="/approvals", tags=["Approvals"])


@router.get("", response_model=List[ApprovalResponse], summary="List approvals")
async def list_approvals(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Approval)
    if status:
        stmt = stmt.where(Approval.status == status)
    stmt = stmt.order_by(Approval.created_at.desc())

    result = await db.execute(stmt)
    approvals = result.scalars().all()
    return [ApprovalResponse.model_validate(a) for a in approvals]


@router.post("/{approval_id}", response_model=ApprovalResponse, summary="Decide approval item")
async def decide_approval(
    approval_id: str,
    data: ApprovalDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Approval).where(Approval.id == approval_id)
    result = await db.execute(stmt)
    approval = result.scalar_one_or_none()

    if not approval:
        raise NotFoundException(detail=f"Approval item {approval_id} not found")

    approval.status = data.decision
    approval.decision_reason = data.reason
    approval.reviewed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(approval)
    return ApprovalResponse.model_validate(approval)
