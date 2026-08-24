"""Agent execution lifecycle — create run, execute, persist, update catalog Agent cards."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.base import AgentContext, BaseAgent
from app.ai.schemas import AgentResultEnvelope
from app.ai.workflow_states import AgentRunStatus
from app.core.exceptions import AINotConfiguredException, AIProviderException, AgentValidationException
from app.models.agent_execution import AgentRun
from app.models.agent_run import Agent, TimelineEvent
from app.models.campaign import Campaign
from app.models.user import User

logger = logging.getLogger(__name__)

AGENT_CARD_IDS = {
    "supervisor": "agent-supervisor",
    "strategy": "agent-strategy",
    "discovery": "agent-discovery",
    "outreach": "agent-outreach",
    "contract": "agent-contract",
    "performance": "agent-performance",
    "optimization": "agent-optimization",
}


class AgentExecutionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run(
        self,
        *,
        agent: BaseAgent,
        user: User,
        campaign: Campaign,
        trigger: str = "manual",
        extras: Optional[Dict[str, Any]] = None,
    ) -> AgentRun:
        run = AgentRun(
            id=f"arun-{uuid.uuid4().hex[:12]}",
            user_id=user.id,
            campaign_id=campaign.id,
            agent_name=agent.name,
            agent_version=agent.version,
            status=AgentRunStatus.QUEUED,
            trigger=trigger,
            requires_approval=False,
        )
        self.db.add(run)
        await self.db.flush()

        ctx = AgentContext(
            user=user,
            campaign=campaign,
            db=self.db,
            trigger=trigger,
            extras=extras or {},
        )

        run.status = AgentRunStatus.RUNNING
        run.started_at = datetime.now(timezone.utc)
        await self._set_agent_card(
            agent.name,
            status="active",
            current_task=f"Running on {campaign.name}",
            last_action=f"Started ({trigger})",
            progress=20,
        )
        await self._add_timeline(
            agent=agent.name.title() + " Agent",
            message=f"Started {agent.name} for campaign {campaign.name}",
            event_type="action",
        )
        await self.db.flush()

        try:
            context_payload = await agent.build_context(ctx)
            run.input_summary = agent.input_summary(ctx, context_payload)
            logger.info(
                "[Auralytics AI] Campaign: %s Agent: %s Provider: Groq Status: Calling provider",
                campaign.id,
                agent.name,
            )
            # Full execute path (validate → prompt → llm → validate output)
            result: AgentResultEnvelope = await agent.execute(ctx)
            run.provider = result.provider
            run.model = result.model
            run.provider_latency_ms = result.provider_latency_ms
            if result.grok_called:
                logger.info(
                    "[Auralytics AI] Campaign: %s Agent: %s Groq validation successful",
                    campaign.id,
                    agent.name,
                )
            run.output_json = {
                "status": result.status,
                "summary": result.summary,
                "confidence": result.confidence,
                "recommendations": result.recommendations,
                "requires_approval": result.requires_approval,
                "data": result.data,
            }
            run.confidence = result.confidence
            run.requires_approval = result.requires_approval
            run.status = (
                AgentRunStatus.WAITING_APPROVAL
                if result.requires_approval
                else AgentRunStatus.COMPLETED
            )
            run.completed_at = datetime.now(timezone.utc)
            await self._bump_agent_card_success(agent.name, campaign.name, result.summary)
            await self._add_timeline(
                agent=agent.name.title() + " Agent",
                message=result.summary[:400] or f"{agent.name} completed",
                event_type="success",
            )
            await self.db.flush()
            return run
        except (AINotConfiguredException, AIProviderException, AgentValidationException) as exc:
            return await self._fail(run, agent.name, campaign.name, str(exc.detail))
        except PermissionError as exc:
            return await self._fail(run, agent.name, campaign.name, str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent %s failed for campaign %s", agent.name, campaign.id)
            return await self._fail(run, agent.name, campaign.name, f"Unexpected agent failure: {type(exc).__name__}")

    async def _fail(self, run: AgentRun, agent_name: str, campaign_name: str, message: str) -> AgentRun:
        run.status = AgentRunStatus.FAILED
        run.error_message = message[:2000]
        run.completed_at = datetime.now(timezone.utc)
        run.output_json = None
        await self._set_agent_card(
            agent_name,
            status="error",
            current_task="Failed — see agent run error",
            last_action=message[:200],
            progress=0,
        )
        await self._add_timeline(
            agent=agent_name.title() + " Agent",
            message=f"Failed on {campaign_name}: {message[:300]}",
            event_type="info",
        )
        await self.db.flush()
        return run

    async def _set_agent_card(
        self,
        agent_name: str,
        *,
        status: str,
        current_task: str,
        last_action: str,
        progress: Optional[int],
    ) -> None:
        card_id = AGENT_CARD_IDS.get(agent_name)
        if not card_id:
            return
        result = await self.db.execute(select(Agent).where(Agent.id == card_id))
        card = result.scalar_one_or_none()
        if not card:
            return
        card.status = status
        card.current_task = current_task[:500]
        card.last_action = last_action[:500]
        card.last_active = "Just now"
        card.progress = progress
        card.started_at = datetime.now(timezone.utc).strftime("%H:%M")

    async def _bump_agent_card_success(self, agent_name: str, campaign_name: str, summary: str) -> None:
        card_id = AGENT_CARD_IDS.get(agent_name)
        if not card_id:
            return
        result = await self.db.execute(select(Agent).where(Agent.id == card_id))
        card = result.scalar_one_or_none()
        if not card:
            return
        card.status = "idle"
        card.tasks_completed = int(card.tasks_completed or 0) + 1
        card.current_task = f"Last: {campaign_name}"[:500]
        card.last_action = (summary or "Completed")[:500]
        card.last_active = "Just now"
        card.progress = 100
        card.started_at = None

    async def _add_timeline(self, *, agent: str, message: str, event_type: str) -> None:
        now = datetime.now(timezone.utc)
        event = TimelineEvent(
            id=f"tl-{uuid.uuid4().hex[:10]}",
            time=now.strftime("%H:%M"),
            agent=agent,
            message=message[:1000],
            type=event_type,
            created_at=now,
        )
        self.db.add(event)
