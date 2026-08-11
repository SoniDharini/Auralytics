from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.outreach import OutreachMessage
from app.models.user import User
from app.schemas.outreach import OutreachResponse, OutreachStatusUpdate

router = APIRouter(prefix="/outreach", tags=["Outreach"])


@router.get("", response_model=List[OutreachResponse], summary="List outreach messages")
async def list_outreach(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(OutreachMessage)
    if status:
        stmt = stmt.where(OutreachMessage.status == status)

    result = await db.execute(stmt)
    messages = result.scalars().all()
    return [OutreachResponse.model_validate(m) for m in messages]


@router.patch("/{outreach_id}", response_model=OutreachResponse, summary="Update outreach status")
async def update_outreach_status(
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

    await db.commit()
    await db.refresh(message)
    return OutreachResponse.model_validate(message)
