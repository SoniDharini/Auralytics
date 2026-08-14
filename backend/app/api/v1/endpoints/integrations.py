from fastapi import APIRouter, Depends
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.influencer import IntegrationStatusResponse
from app.services.influencer_ingestion_service import InfluencerIngestionService

router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.get("/status", response_model=IntegrationStatusResponse, summary="Get safe status of external social providers")
async def get_integration_status(
    current_user: User = Depends(get_current_user),
):
    service = InfluencerIngestionService()
    status_dict = service.get_providers_status()
    return IntegrationStatusResponse(
        youtube=status_dict.get("youtube", {"configured": False}),
        instagram=status_dict.get("instagram", {"configured": False}),
    )
