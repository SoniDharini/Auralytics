"""Read-only campaign context for the assistant. Never invents rows or runs agents."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.campaign_content import CampaignContent, ContentPerformanceSnapshot
from app.models.campaign_influencer import CampaignInfluencer
from app.models.contract import Contract
from app.models.influencer import Influencer
from app.models.outreach import OutreachMessage
from app.models.user import User
from app.services.campaign_workflow_service import CampaignWorkflowService


class CampaignContextService:
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user

    async def list_campaigns(self) -> List[Campaign]:
        result = await self.db.execute(
            select(Campaign).where(Campaign.owner_id == self.user.id).order_by(Campaign.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_owned_campaign(self, campaign_id: str) -> Optional[Campaign]:
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id, Campaign.owner_id == self.user.id)
        )
        return result.scalar_one_or_none()

    async def workspace_summary(self) -> Dict[str, Any]:
        campaigns = await self.list_campaigns()
        completed = [c for c in campaigns if c.status == "completed" or c.workflow_state == "COMPLETED"]
        active = [c for c in campaigns if c.status not in {"completed", "draft"} and c.workflow_state != "COMPLETED"]
        pending = [c for c in active if c.status in {"active", "planning", "needs_attention", "paused"}]
        return {
            "total": len(campaigns),
            "completed": [{"id": c.id, "name": c.name, "brand": c.brand, "status": c.status} for c in completed],
            "active": [{"id": c.id, "name": c.name, "brand": c.brand, "status": c.status, "workflow_state": c.workflow_state} for c in active],
            "pending_work": [{"id": c.id, "name": c.name, "status": c.status, "workflow_state": c.workflow_state} for c in pending],
        }

    async def campaign_status(self, campaign: Campaign) -> Dict[str, Any]:
        state = await CampaignWorkflowService(self.db).get_state(campaign)
        return {
            "id": campaign.id,
            "name": campaign.name,
            "brand": campaign.brand,
            "status": campaign.status,
            "workflow_state": campaign.workflow_state,
            "current_step": state.current_step,
            "next_step": state.next_step,
            "progress_percentage": state.progress_percentage,
            "next_action": state.next_action.model_dump() if state.next_action else None,
            "discovered_count": state.discovered_count,
            "shortlisted_count": state.shortlisted_count,
            "outreach_count": state.outreach_count,
        }

    async def creator_history(self, query: str) -> Dict[str, Any]:
        needle = f"%{query.strip()}%"
        result = await self.db.execute(
            select(Influencer)
            .join(CampaignInfluencer, CampaignInfluencer.influencer_id == Influencer.id)
            .join(Campaign, Campaign.id == CampaignInfluencer.campaign_id)
            .where(
                Campaign.owner_id == self.user.id,
                or_(
                    Influencer.name.ilike(needle),
                    Influencer.username.ilike(needle),
                ),
            )
            .distinct()
        )
        influencers = list(result.scalars().all())
        if not influencers:
            return {"found": False, "query": query, "matches": []}

        matches = []
        for inf in influencers:
            links = await self.db.execute(
                select(CampaignInfluencer, Campaign)
                .join(Campaign, Campaign.id == CampaignInfluencer.campaign_id)
                .where(
                    CampaignInfluencer.influencer_id == inf.id,
                    Campaign.owner_id == self.user.id,
                )
            )
            campaigns = []
            for link, camp in links.all():
                campaigns.append(
                    {
                        "campaign_id": camp.id,
                        "campaign_name": camp.name,
                        "status": camp.status,
                        "creator_status": link.status,
                    }
                )
            contracts = await self.db.execute(
                select(Contract).where(
                    Contract.influencer_id == inf.id,
                    Contract.campaign_id.in_([c["campaign_id"] for c in campaigns] or ["__none__"]),
                )
            )
            contract_rows = [
                {
                    "campaign": c.campaign,
                    "value": c.value,
                    "currency": c.currency,
                    "status": c.status,
                    "reference_only": True,
                }
                for c in contracts.scalars().all()
            ]
            matches.append(
                {
                    "name": inf.name,
                    "username": inf.username,
                    "campaign_count": len(campaigns),
                    "campaigns": campaigns,
                    "contracts": contract_rows,
                }
            )
        return {"found": True, "query": query, "matches": matches}

    async def campaign_detail(self, campaign: Campaign) -> Dict[str, Any]:
        status = await self.campaign_status(campaign)
        outreach = await self.db.execute(
            select(OutreachMessage).where(OutreachMessage.campaign_id == campaign.id)
        )
        contracts = await self.db.execute(select(Contract).where(Contract.campaign_id == campaign.id))
        contents = await self.db.execute(select(CampaignContent).where(CampaignContent.campaign_id == campaign.id))
        content_rows = list(contents.scalars().all())
        snapshots = []
        if content_rows:
            snap = await self.db.execute(
                select(ContentPerformanceSnapshot)
                .where(ContentPerformanceSnapshot.campaign_content_id.in_([c.id for c in content_rows]))
                .order_by(ContentPerformanceSnapshot.captured_at.asc())
            )
            snapshots = [
                {
                    "content_id": s.campaign_content_id,
                    "views": s.views,
                    "likes": s.likes,
                    "comments": s.comments,
                    "captured_at": s.captured_at.isoformat() if s.captured_at else None,
                    "kind": "HISTORICAL_SNAPSHOT",
                }
                for s in snap.scalars().all()
            ]
        return {
            **status,
            "spend": campaign.spend,
            "revenue": campaign.revenue,
            "roas": campaign.roas,
            "outreach": [
                {
                    "influencer_name": m.influencer_name,
                    "status": m.status,
                    "final_amount": m.final_amount,
                    "currency": m.currency,
                }
                for m in outreach.scalars().all()
            ],
            "contracts": [
                {
                    "creator": c.creator,
                    "value": c.value,
                    "currency": c.currency,
                    "status": c.status,
                    "reference_only": bool((c.analysis_json or {}).get("reference_only")),
                }
                for c in contracts.scalars().all()
            ],
            "content": [
                {
                    "id": c.id,
                    "url": c.content_url,
                    "current_views": c.current_views,
                    "tracking_status": c.tracking_status,
                    "attribution_source": c.attribution_source,
                }
                for c in content_rows
            ],
            "performance_snapshots": snapshots,
        }
