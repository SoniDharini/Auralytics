"""Auralytics Assistant APIs. Does not invoke Strategy/Discovery/Outreach/Contract/Performance agents."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.campaign_import import (
    ChatRequest,
    ChatResponse,
    ClassifyCampaignRequest,
    ConfirmImportRequest,
    HistoricalCampaignImportPreview,
    ResolveConflictRequest,
)
from app.services.assistant_chat_service import AssistantChatService
from app.services.campaign_history_import_service import CampaignHistoryImportService

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/imports", response_model=HistoricalCampaignImportPreview)
async def upload_campaign_history(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await CampaignHistoryImportService(db, current_user).create_from_files(files)


@router.get("/imports/{import_id}", response_model=HistoricalCampaignImportPreview)
async def get_import_preview(
    import_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await CampaignHistoryImportService(db, current_user).get_preview(import_id)


@router.post("/imports/{import_id}/conflicts", response_model=HistoricalCampaignImportPreview)
async def resolve_import_conflict(
    import_id: str,
    payload: ResolveConflictRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await CampaignHistoryImportService(db, current_user).resolve_conflict(import_id, payload)


@router.post("/imports/{import_id}/classify", response_model=HistoricalCampaignImportPreview)
async def classify_imported_campaign(
    import_id: str,
    payload: ClassifyCampaignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await CampaignHistoryImportService(db, current_user).classify_campaign(import_id, payload)


@router.post("/imports/{import_id}/confirm")
async def confirm_campaign_import(
    import_id: str,
    payload: Optional[ConfirmImportRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await CampaignHistoryImportService(db, current_user).confirm(import_id, payload)


@router.post("/chat", response_model=ChatResponse)
async def assistant_chat(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await AssistantChatService(db, current_user).chat(
        payload.message,
        campaign_id=payload.campaign_id,
        import_id=payload.import_id,
    )


@router.get("/chat")
async def assistant_transcript(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    messages = await AssistantChatService(db, current_user).get_transcript()
    return {"messages": messages}
