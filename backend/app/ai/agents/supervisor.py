"""Supervisor — deterministic workflow coordinator (Grok does not choose transitions)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.discovery import DiscoveryAgent
from app.ai.agents.outreach import OutreachAgent
from app.ai.agents.strategy import StrategyAgent
from app.ai.execution import AgentExecutionService
from app.ai.workflow_states import ALLOWED_TRANSITIONS, AgentNames, AgentRunStatus, WorkflowState
from app.core.exceptions import NotFoundException, WorkflowStateException
from app.models.agent_execution import AgentRun
from app.models.approval import Approval
from app.models.campaign import Campaign
from app.models.campaign_influencer import CampaignInfluencer
from app.models.campaign_strategy import CampaignStrategy
from app.models.outreach import OutreachMessage
from app.models.user import User

logger = logging.getLogger(__name__)


class SupervisorAgent:
    """Coordinates agents via persisted workflow_state. Not a free-running LLM loop."""

    name = AgentNames.SUPERVISOR
    version = "1.0.0"

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.execution = AgentExecutionService(db)

    async def load_owned_campaign(self, campaign_id: str, user: User) -> Campaign:
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id, Campaign.owner_id == user.id)
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise NotFoundException(detail="Campaign not found")
        if not campaign.workflow_state:
            campaign.workflow_state = WorkflowState.CAMPAIGN_CREATED
        return campaign

    def _assert_transition(self, campaign: Campaign, target: str) -> None:
        current = campaign.workflow_state or WorkflowState.CAMPAIGN_CREATED
        allowed = ALLOWED_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise WorkflowStateException(
                detail=f"Cannot transition from {current} to {target}"
            )

    async def _set_state(self, campaign: Campaign, target: str) -> None:
        self._assert_transition(campaign, target)
        campaign.workflow_state = target
        await self.db.flush()

    async def start(self, *, campaign_id: str, user: User, trigger: str = "manual") -> Dict[str, Any]:
        """Advance the campaign one controlled step (Strategy first)."""
        campaign = await self.load_owned_campaign(campaign_id, user)
        state = campaign.workflow_state or WorkflowState.CAMPAIGN_CREATED

        if state in (WorkflowState.CAMPAIGN_CREATED, WorkflowState.FAILED):
            if state == WorkflowState.FAILED:
                # Retry strategy from failed
                campaign.workflow_state = WorkflowState.CAMPAIGN_CREATED
                await self.db.flush()
            await self._set_state(campaign, WorkflowState.STRATEGY_PENDING)
            result = await self.run_strategy(campaign=campaign, user=user, trigger=trigger)
            if (
                result.get("workflow_state") == WorkflowState.STRATEGY_COMPLETED
                and result.get("agent_run") is not None
                and result["agent_run"].status == AgentRunStatus.COMPLETED
            ):
                campaign = await self.load_owned_campaign(campaign_id, user)
                return await self.run_discovery(campaign=campaign, user=user, trigger=trigger)
            return result

        if state == WorkflowState.STRATEGY_PENDING:
            return await self.run_strategy(campaign=campaign, user=user, trigger=trigger)

        if state == WorkflowState.STRATEGY_COMPLETED:
            return await self.run_discovery(campaign=campaign, user=user, trigger=trigger)

        if state == WorkflowState.DISCOVERY_PENDING:
            return await self.run_discovery(campaign=campaign, user=user, trigger=trigger)

        if state == WorkflowState.SHORTLIST_APPROVAL_PENDING:
            return {
                "campaign_id": campaign.id,
                "workflow_state": campaign.workflow_state,
                "next": "approval",
                "message": "Workflow is waiting for human shortlist approval.",
                "agent_run": None,
            }

        if state in (WorkflowState.SHORTLIST_APPROVED, WorkflowState.OUTREACH_PENDING):
            return await self.run_outreach(campaign=campaign, user=user, trigger=trigger)

        return {
            "campaign_id": campaign.id,
            "workflow_state": campaign.workflow_state,
            "next": None,
            "message": f"No automatic step for state {campaign.workflow_state}",
            "agent_run": None,
        }

    async def run_strategy(
        self,
        *,
        campaign: Campaign,
        user: User,
        trigger: str = "manual",
    ) -> Dict[str, Any]:
        state = campaign.workflow_state or WorkflowState.CAMPAIGN_CREATED
        if state == WorkflowState.CAMPAIGN_CREATED:
            await self._set_state(campaign, WorkflowState.STRATEGY_PENDING)
        elif state not in (WorkflowState.STRATEGY_PENDING, WorkflowState.STRATEGY_COMPLETED):
            # Allow explicit re-run only from strategy stages or after forcing pending
            if state == WorkflowState.STRATEGY_COMPLETED:
                # Re-run: stay completed until new run succeeds, then bump version
                pass
            else:
                raise WorkflowStateException(
                    detail=f"Strategy Agent cannot run while workflow is {state}"
                )
        elif state != WorkflowState.STRATEGY_PENDING:
            campaign.workflow_state = WorkflowState.STRATEGY_PENDING
            await self.db.flush()

        agent = StrategyAgent()
        run = await self.execution.run(
            agent=agent,
            user=user,
            campaign=campaign,
            trigger=trigger,
        )

        if run.status == AgentRunStatus.COMPLETED and run.output_json:
            await self._persist_strategy(campaign, run)
            if campaign.workflow_state == WorkflowState.STRATEGY_PENDING:
                await self._set_state(campaign, WorkflowState.STRATEGY_COMPLETED)
            elif campaign.workflow_state == WorkflowState.STRATEGY_COMPLETED:
                # Re-run keeps completed
                pass
        elif run.status == AgentRunStatus.FAILED:
            # Mark failed without inventing strategy
            if campaign.workflow_state == WorkflowState.STRATEGY_PENDING:
                # Direct assign allowed via FAILED transition from STRATEGY_PENDING
                campaign.workflow_state = WorkflowState.FAILED
                await self.db.flush()

        await self.db.commit()
        await self.db.refresh(run)

        return {
            "campaign_id": campaign.id,
            "workflow_state": campaign.workflow_state,
            "next": "discovery" if run.status == AgentRunStatus.COMPLETED else None,
            "message": (
                "Strategy Agent completed"
                if run.status == AgentRunStatus.COMPLETED
                else f"Strategy Agent {run.status}"
            ),
            "agent_run": run,
        }

    async def _persist_strategy(self, campaign: Campaign, run: AgentRun) -> None:
        data = (run.output_json or {}).get("data") or {}
        version_result = await self.db.execute(
            select(func.coalesce(func.max(CampaignStrategy.version), 0)).where(
                CampaignStrategy.campaign_id == campaign.id
            )
        )
        next_version = int(version_result.scalar_one() or 0) + 1
        strategy = CampaignStrategy(
            campaign_id=campaign.id,
            agent_run_id=run.id,
            strategy_json=data,
            version=next_version,
        )
        self.db.add(strategy)
        await self.db.flush()
        logger.info(
            "Persisted strategy v%s for campaign %s from run %s",
            next_version,
            campaign.id,
            run.id,
        )

    async def run_discovery(
        self,
        *,
        campaign: Campaign,
        user: User,
        trigger: str = "manual",
    ) -> Dict[str, Any]:
        state = campaign.workflow_state or WorkflowState.CAMPAIGN_CREATED
        if state == WorkflowState.STRATEGY_COMPLETED:
            await self._set_state(campaign, WorkflowState.DISCOVERY_PENDING)
        elif state == WorkflowState.SHORTLIST_APPROVAL_PENDING:
            await self._set_state(campaign, WorkflowState.DISCOVERY_PENDING)
        elif state not in (WorkflowState.DISCOVERY_PENDING,):
            raise WorkflowStateException(
                detail=f"Discovery Agent cannot run while workflow is {state}"
            )

        strategy_exists = await self.db.execute(
            select(CampaignStrategy.id)
            .where(CampaignStrategy.campaign_id == campaign.id)
            .limit(1)
        )
        if strategy_exists.scalar_one_or_none() is None:
            raise WorkflowStateException(detail="Strategy must exist before Discovery Agent runs")

        agent = DiscoveryAgent()
        run = await self.execution.run(
            agent=agent,
            user=user,
            campaign=campaign,
            trigger=trigger,
        )

        if run.status == AgentRunStatus.WAITING_APPROVAL and run.output_json:
            await self._persist_discovery_recommendations(campaign, run)
            if campaign.workflow_state == WorkflowState.DISCOVERY_PENDING:
                await self._set_state(campaign, WorkflowState.DISCOVERY_COMPLETED)
                await self._set_state(campaign, WorkflowState.SHORTLIST_APPROVAL_PENDING)
            await self._create_shortlist_approval(campaign, user, run)
        elif run.status == AgentRunStatus.FAILED:
            if campaign.workflow_state == WorkflowState.DISCOVERY_PENDING:
                campaign.workflow_state = WorkflowState.FAILED
                await self.db.flush()

        await self.db.commit()
        await self.db.refresh(run)

        return {
            "campaign_id": campaign.id,
            "workflow_state": campaign.workflow_state,
            "next": "approval" if run.status == AgentRunStatus.WAITING_APPROVAL else None,
            "message": (
                "Discovery Agent completed — awaiting shortlist approval"
                if run.status == AgentRunStatus.WAITING_APPROVAL
                else f"Discovery Agent {run.status}"
            ),
            "agent_run": run,
        }

    async def _persist_discovery_recommendations(self, campaign: Campaign, run: AgentRun) -> None:
        recs = (run.output_json or {}).get("recommendations") or []
        for rec in recs:
            inf_id = str(rec.get("influencer_id", "")).strip()
            if not inf_id:
                continue
            link_result = await self.db.execute(
                select(CampaignInfluencer).where(
                    CampaignInfluencer.campaign_id == campaign.id,
                    CampaignInfluencer.influencer_id == inf_id,
                )
            )
            link = link_result.scalar_one_or_none()
            if not link:
                continue
            ai_block = {
                "source": "discovery_agent_grok",
                "key": "ai_discovery",
                "label": "AI Campaign Fit",
                "weight": int(rec.get("ai_fit_score") or 0),
                "detail": rec.get("recommendation_reason")
                or rec.get("best_use_case")
                or "AI-ranked creator for this campaign",
                "agent_run_id": run.id,
                "rank": rec.get("rank"),
                "ai_fit_score": rec.get("ai_fit_score"),
                "deterministic_match_score": rec.get("deterministic_match_score"),
                "final_score": rec.get("final_score"),
                "campaign_fit": rec.get("campaign_fit"),
                "recommendation_reason": rec.get("recommendation_reason"),
                "strategy_alignment": rec.get("strategy_alignment") or [],
                "strengths": rec.get("strengths") or [],
                "risks": rec.get("risks") or [],
                "best_use_case": rec.get("best_use_case"),
                "confidence": rec.get("confidence"),
            }
            existing = [
                r
                for r in (link.match_reasons or [])
                if r.get("source") != "discovery_agent_grok" and r.get("key") != "ai_discovery"
            ]
            existing.append(ai_block)
            link.match_reasons = existing
        await self.db.flush()
        logger.info(
            "Persisted discovery recommendations for campaign %s from run %s",
            campaign.id,
            run.id,
        )

    async def _create_shortlist_approval(
        self, campaign: Campaign, user: User, run: AgentRun
    ) -> None:
        now = datetime.now(timezone.utc)
        summary = (run.output_json or {}).get("summary") or "Review AI creator recommendations"
        approval = Approval(
            id=f"appr-{uuid.uuid4().hex[:12]}",
            agent="Discovery Agent",
            type="shortlist",
            action="Review AI-recommended creators for campaign shortlist",
            reason=summary[:2000],
            campaign=campaign.name,
            financial_impact="N/A",
            confidence=float(run.confidence or 0),
            timestamp=now.strftime("%Y-%m-%d %H:%M UTC"),
            status="pending",
            user_id=user.id,
            campaign_id=campaign.id,
            agent_run_id=run.id,
        )
        self.db.add(approval)
        await self.db.flush()
        logger.info(
            "Created shortlist approval %s for campaign %s",
            approval.id,
            campaign.id,
        )

    async def run_outreach(
        self,
        *,
        campaign: Campaign,
        user: User,
        influencer_id: Optional[str] = None,
        trigger: str = "manual",
    ) -> Dict[str, Any]:
        state = campaign.workflow_state or WorkflowState.CAMPAIGN_CREATED
        if state == WorkflowState.SHORTLIST_APPROVED:
            await self._set_state(campaign, WorkflowState.OUTREACH_PENDING)

        extras = {}
        if influencer_id:
            extras["influencer_id"] = influencer_id

        agent = OutreachAgent()
        run = await self.execution.run(
            agent=agent,
            user=user,
            campaign=campaign,
            trigger=trigger,
            extras=extras,
        )

        outreach_msg = None
        if run.status == AgentRunStatus.COMPLETED and run.output_json:
            outreach_msg = await self._persist_outreach_message(campaign, run, influencer_id)
            if campaign.workflow_state == WorkflowState.OUTREACH_PENDING:
                await self._set_state(campaign, WorkflowState.OUTREACH_COMPLETED)
        elif run.status == AgentRunStatus.FAILED:
            if campaign.workflow_state == WorkflowState.OUTREACH_PENDING:
                campaign.workflow_state = WorkflowState.FAILED
                await self.db.flush()

        await self.db.commit()
        await self.db.refresh(run)

        return {
            "campaign_id": campaign.id,
            "workflow_state": campaign.workflow_state,
            "next": "contract" if run.status == AgentRunStatus.COMPLETED else None,
            "message": (
                "Outreach Agent completed message generation"
                if run.status == AgentRunStatus.COMPLETED
                else f"Outreach Agent {run.status}"
            ),
            "agent_run": run,
            "outreach_message": outreach_msg,
        }

    async def _persist_outreach_message(
        self, campaign: Campaign, run: AgentRun, influencer_id: Optional[str] = None
    ) -> Optional[OutreachMessage]:
        data = (run.output_json or {}).get("data") or {}
        inf_id = influencer_id or data.get("influencer_id")
        if not inf_id:
            return None

        msg_id = f"outr-{uuid.uuid4().hex[:12]}"
        msg = OutreachMessage(
            id=msg_id,
            campaign_id=campaign.id,
            influencer_id=inf_id,
            agent_run_id=run.id,
            influencer_name=data.get("influencer_name") or "Creator",
            influencer_username=data.get("influencer_username") or "creator",
            campaign_name=campaign.name,
            channel=data.get("channel") or "EMAIL",
            subject=data.get("subject") or "Collaboration Opportunity",
            body=data.get("message") or "",
            short_dm=data.get("short_dm") or "",
            call_to_action=data.get("call_to_action") or "",
            personalization_points=data.get("personalization_points") or [],
            confidence=float(data.get("confidence") or 0.90),
            status="READY",
        )
        self.db.add(msg)
        await self.db.flush()
        logger.info(
            "Persisted outreach message %s for creator %s in campaign %s",
            msg.id,
            inf_id,
            campaign.id,
        )
        return msg
