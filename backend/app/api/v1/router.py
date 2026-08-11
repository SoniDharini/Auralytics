from fastapi import APIRouter
from app.api.v1.endpoints import (
    agents,
    analytics,
    approvals,
    auth,
    campaigns,
    contracts,
    influencers,
    outreach,
    users,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(campaigns.router)
api_router.include_router(influencers.router)
api_router.include_router(contracts.router)
api_router.include_router(outreach.router)
api_router.include_router(approvals.router)
api_router.include_router(agents.router)
api_router.include_router(analytics.router)
