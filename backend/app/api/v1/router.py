from fastapi import APIRouter
from app.api.v1.endpoints import (
    activities,
    agents,
    ai,
    analytics,
    approvals,
    auth,
    campaign_agents,
    campaign_discovery,
    campaigns,
    contracts,
    dashboard,
    influencers,
    integrations,
    outreach,
    users,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(campaigns.router)
api_router.include_router(campaign_discovery.router)
api_router.include_router(campaign_agents.router)
api_router.include_router(campaign_agents.runs_router)
api_router.include_router(activities.router)
api_router.include_router(dashboard.router)
api_router.include_router(influencers.router)
api_router.include_router(integrations.router)
api_router.include_router(contracts.router)
api_router.include_router(outreach.router)
api_router.include_router(approvals.router)
api_router.include_router(agents.router)
api_router.include_router(ai.router)
api_router.include_router(analytics.router)
