"""AI status + Groq connectivity probe (authenticated, no secrets)."""

from fastapi import APIRouter, Depends, Query

from app.ai.llm_service import LLMService
from app.ai.schemas import AIStatusResponse
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/status", response_model=AIStatusResponse, summary="Groq connectivity status")
async def ai_status(
    probe: bool = Query(True, description="When true, sends a tiny ping to Groq"),
    current_user: User = Depends(get_current_user),
):
    """Never returns API keys. Used to validate Groq before agent workflows."""
    _ = current_user
    return await LLMService().status(probe=probe)
