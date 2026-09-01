"""Supervisor — deterministic workflow coordinator (Grok does not choose transitions)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.contract import ContractAgent
from app.ai.agents.discovery import DiscoveryAgent
from app.ai.agents.outreach import OutreachAgent
from app.ai.agents.strategy import StrategyAgent
from app.ai.execution import AgentExecutionService
from app.ai.workflow_states import ALLOWED_TRANSITIONS, AgentNames, AgentRunStatus, WorkflowState
from app.core.exceptions import NotFoundException, WorkflowStateException
from app.models.agent_execution import AgentRun
from app.models.approval import Approval
from app.models.campaign import Campaign
from app.models.campaign_activity import CampaignActivity
from app.models.campaign_influencer import CampaignInfluencer, CampaignInfluencerStatus
from app.models.campaign_strategy import CampaignStrategy
from app.models.contract import Contract
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

    async def _candidate_count(self, campaign_id: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(CampaignInfluencer).where(
                CampaignInfluencer.campaign_id == campaign_id
            )
        )
        return int(result.scalar_one() or 0)

    async def start(self, *, campaign_id: str, user: User, trigger: str = "manual") -> Dict[str, Any]:
        """Advance the campaign one controlled step (Strategy first)."""
        campaign = await self.load_owned_campaign(campaign_id, user)
        state = campaign.workflow_state or WorkflowState.CAMPAIGN_CREATED

        if state in (WorkflowState.CAMPAIGN_CREATED, WorkflowState.FAILED):
            if state == WorkflowState.FAILED:
                has_strategy = await self.db.execute(
                    select(CampaignStrategy.id)
                    .where(CampaignStrategy.campaign_id == campaign.id)
                    .limit(1)
                )
                if has_strategy.scalar_one_or_none() is not None:
                    # Strategy already succeeded; previous FAILED was almost always Discovery
                    # running with no creators yet. Resume from strategy complete.
                    campaign.workflow_state = WorkflowState.STRATEGY_COMPLETED
                    await self.db.commit()
                    return {
                        "campaign_id": campaign.id,
                        "workflow_state": campaign.workflow_state,
                        "next": "discovery",
                        "message": "Strategy Agent completed. Discover creators next.",
                        "agent_run": None,
                    }
                campaign.workflow_state = WorkflowState.CAMPAIGN_CREATED
                await self.db.flush()
            await self._set_state(campaign, WorkflowState.STRATEGY_PENDING)
            result = await self.run_strategy(campaign=campaign, user=user, trigger=trigger)
            if (
                result.get("workflow_state") == WorkflowState.STRATEGY_COMPLETED
                and result.get("agent_run") is not None
                and result["agent_run"].status == AgentRunStatus.COMPLETED
                and await self._candidate_count(campaign_id) > 0
            ):
                campaign = await self.load_owned_campaign(campaign_id, user)
                return await self.run_discovery(campaign=campaign, user=user, trigger=trigger)
            return result

        if state == WorkflowState.STRATEGY_PENDING:
            return await self.run_strategy(campaign=campaign, user=user, trigger=trigger)

        if state == WorkflowState.STRATEGY_COMPLETED:
            if await self._candidate_count(campaign.id) == 0:
                return {
                    "campaign_id": campaign.id,
                    "workflow_state": campaign.workflow_state,
                    "next": "discovery",
                    "message": "Strategy Agent completed. Discover creators before running the Discovery Agent.",
                    "agent_run": None,
                }
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
        elif state == WorkflowState.FAILED:
            await self._set_state(campaign, WorkflowState.STRATEGY_PENDING)
        elif state not in (WorkflowState.STRATEGY_PENDING, WorkflowState.STRATEGY_COMPLETED):
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
        elif state == WorkflowState.FAILED:
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
                candidate_count = await self._candidate_count(campaign.id)
                if candidate_count > 0:
                    logger.warning(
                        "Discovery ranking failed for campaign %s after %s YouTube creators were saved; unlocking shortlist.",
                        campaign.id,
                        candidate_count,
                    )
                    await self._set_state(campaign, WorkflowState.DISCOVERY_COMPLETED)
                else:
                    missing_creators = self._is_missing_creator_failure(run.error_message)
                    # Empty candidate set is not a campaign failure — strategy is still valid.
                    campaign.workflow_state = (
                        WorkflowState.STRATEGY_COMPLETED if missing_creators else WorkflowState.FAILED
                    )
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
        link_result = await self.db.execute(
            select(CampaignInfluencer).where(CampaignInfluencer.campaign_id == campaign.id)
        )
        links = list(link_result.scalars().all())
        rec_by_id = {
            str(rec.get("influencer_id", "")).strip(): rec
            for rec in recs
            if str(rec.get("influencer_id", "")).strip()
        }

        for link in links:
            existing = [
                r
                for r in (link.match_reasons or [])
                if r.get("source") != "discovery_agent_grok" and r.get("key") != "ai_discovery"
            ]
            rec = rec_by_id.get(str(link.influencer_id))
            if not rec:
                link.match_reasons = existing
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
                "requirements_match": rec.get("requirements_match") or {},
                "eligibility": rec.get("eligibility") or "ELIGIBLE",
                "classification": rec.get("classification") or {},
                "requirement_match": rec.get("requirement_match") or {},
                "creator_tier": rec.get("creator_tier"),
                "tier_match": rec.get("tier_match"),
                "best_use_case": rec.get("best_use_case"),
                "confidence": rec.get("confidence"),
            }
            existing.append(ai_block)
            link.match_reasons = existing
            score = rec.get("final_score")
            if score is None:
                score = rec.get("ai_fit_score")
            try:
                if score is not None:
                    link.match_score = int(round(float(score)))
            except (TypeError, ValueError):
                pass
        await self.db.flush()
        logger.info(
            "Persisted discovery recommendations campaign=%s run=%s recommended=%s linked=%s",
            campaign.id,
            run.id,
            len(rec_by_id),
            len(links),
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

    @staticmethod
    def _is_missing_creator_failure(error_message: Optional[str]) -> bool:
        text = (error_message or "").lower()
        return "no influencer candidates" in text or "pre-filtering" in text

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

    async def run_negotiation(
        self,
        *,
        campaign: Campaign,
        user: User,
        outreach_message_id: str,
        influencer_reply: str,
        user_instruction: Optional[str] = None,
        trigger: str = "manual",
    ) -> Dict[str, Any]:
        msg_stmt = select(OutreachMessage).where(OutreachMessage.id == outreach_message_id)
        msg_res = await self.db.execute(msg_stmt)
        outreach_msg = msg_res.scalar_one_or_none()
        if not outreach_msg:
            raise NotFoundException(detail=f"Outreach message {outreach_message_id} not found")

        history = list(outreach_msg.conversation_history or [])
        if not history:
            history.append({
                "sender": "BRAND",
                "message": outreach_msg.body,
                "subject": outreach_msg.subject,
                "message_type": "INITIAL_OUTREACH",
                "timestamp": (outreach_msg.created_at or datetime.now(timezone.utc)).isoformat(),
            })

        history.append({
            "sender": "INFLUENCER",
            "message": influencer_reply,
            "message_type": "INFLUENCER_REPLY",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        extras = {
            "mode": "NEGOTIATION_FOLLOWUP",
            "influencer_id": outreach_msg.influencer_id,
            "influencer_reply": influencer_reply,
            "user_instruction": user_instruction,
            "conversation_history": history,
            "previous_subject": outreach_msg.subject or "Collaboration Opportunity",
            "outreach_message": outreach_msg,
        }

        agent = OutreachAgent()
        run = await self.execution.run(
            agent=agent,
            user=user,
            campaign=campaign,
            trigger=trigger,
            extras=extras,
        )

        data = (run.output_json or {}).get("data") or {}
        if run.status == AgentRunStatus.COMPLETED and data:
            followup_msg = data.get("message") or ""
            history.append({
                "sender": "AI_DRAFT",
                "message": followup_msg,
                "subject": data.get("subject"),
                "message_type": "FOLLOW_UP",
                "extracted_terms": data.get("extracted_terms") or {},
                "conversation_state": data.get("conversation_state"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            outreach_msg.conversation_history = history
            outreach_msg.extracted_terms = data.get("extracted_terms") or {}
            outreach_msg.negotiation_state = data.get("conversation_state") or "NEGOTIATING_PRICE"
            outreach_msg.reply = influencer_reply
            outreach_msg.body = followup_msg
            if data.get("subject"):
                outreach_msg.subject = data.get("subject")
            if data.get("short_dm"):
                outreach_msg.short_dm = data.get("short_dm")

            # Update CampaignInfluencer status if negotiating
            link_stmt = select(CampaignInfluencer).where(
                CampaignInfluencer.campaign_id == campaign.id,
                CampaignInfluencer.influencer_id == outreach_msg.influencer_id,
            )
            link_res = await self.db.execute(link_stmt)
            link = link_res.scalar_one_or_none()
            if link and link.status not in (CampaignInfluencerStatus.ACCEPTED, CampaignInfluencerStatus.DECLINED):
                link.status = CampaignInfluencerStatus.NEGOTIATING

            await self.db.flush()

        await self.db.commit()
        await self.db.refresh(run)
        await self.db.refresh(outreach_msg)

        return {
            "campaign_id": campaign.id,
            "workflow_state": campaign.workflow_state,
            "agent_run": run,
            "outreach_message": outreach_msg,
            "negotiation_data": data,
        }

    async def run_contract(
        self,
        *,
        campaign: Campaign,
        user: User,
        influencer_id: str,
        agreed_terms: Optional[Dict[str, Any]] = None,
        confirmed_terms: Optional[Dict[str, Any]] = None,
        contract_text: Optional[str] = None,
        trigger: str = "manual",
    ) -> Dict[str, Any]:
        state = campaign.workflow_state or WorkflowState.CAMPAIGN_CREATED
        if state in (WorkflowState.OUTREACH_COMPLETED, WorkflowState.SHORTLIST_APPROVED):
            await self._set_state(campaign, WorkflowState.CONTRACT_PENDING)

        # Record activity
        req_activity = CampaignActivity(
            user_id=user.id,
            campaign_id=campaign.id,
            activity_type="contract_requested",
            title="Contract analysis requested",
            description=f"Initiated contract analysis for creator {influencer_id}",
        )
        self.db.add(req_activity)
        await self.db.flush()

        extras = {
            "influencer_id": influencer_id,
            "agreed_terms": agreed_terms or {},
            "confirmed_terms": confirmed_terms or agreed_terms or {},
            "contract_text": contract_text,
        }

        agent = ContractAgent()
        run = await self.execution.run(
            agent=agent,
            user=user,
            campaign=campaign,
            trigger=trigger,
            extras=extras,
        )

        contract_obj = None
        if run.status in (AgentRunStatus.COMPLETED, AgentRunStatus.WAITING_APPROVAL) and run.output_json:
            contract_obj = await self._persist_contract(campaign, run, influencer_id)
        elif run.status == AgentRunStatus.FAILED:
            if campaign.workflow_state == WorkflowState.CONTRACT_PENDING:
                campaign.workflow_state = WorkflowState.FAILED
                await self.db.flush()

        await self.db.commit()
        await self.db.refresh(run)

        return {
            "campaign_id": campaign.id,
            "workflow_state": campaign.workflow_state,
            "next": "review" if run.status in (AgentRunStatus.COMPLETED, AgentRunStatus.WAITING_APPROVAL) else None,
            "message": (
                "Contract Agent completed analysis"
                if run.status in (AgentRunStatus.COMPLETED, AgentRunStatus.WAITING_APPROVAL)
                else f"Contract Agent {run.status}"
            ),
            "agent_run": run,
            "contract": contract_obj,
        }

    async def _persist_contract(
        self, campaign: Campaign, run: AgentRun, influencer_id: Optional[str] = None
    ) -> Optional[Contract]:
        data = (run.output_json or {}).get("data") or {}
        inf_id = influencer_id or data.get("influencer_id")

        existing_stmt = select(Contract).where(
            (Contract.campaign_id == campaign.id) & (Contract.influencer_id == inf_id)
        )
        existing_res = await self.db.execute(existing_stmt)
        contract = existing_res.scalar_one_or_none()

        overall_status = data.get("overall_status") or "READY_FOR_REVIEW"
        risk_level = str(data.get("risk_level") or "LOW").lower()
        if data.get("risk_flags"):
            severities = [f.get("severity", "LOW").upper() for f in data["risk_flags"] if isinstance(f, dict)]
            if "HIGH" in severities:
                risk_level = "high"
            elif "MEDIUM" in severities and risk_level != "high":
                risk_level = "medium"

        if not contract:
            cntr_id = f"cntr-{uuid.uuid4().hex[:12]}"
            contract = Contract(
                id=cntr_id,
                campaign_id=campaign.id,
                influencer_id=inf_id,
                outreach_id=data.get("outreach_id"),
                agent_run_id=run.id,
                creator=data.get("creator_name") or "Creator",
                username=data.get("creator_username") or "creator",
                campaign=campaign.name,
                value=float(data.get("agreed_value") or 0.0),
                currency=str(data.get("currency") or "INR"),
                status="pending_signature",
                version=1,
                start_date=data.get("start_date") or (campaign.start_date or "Launch Date"),
                end_date=data.get("end_date") or (campaign.end_date or "Launch + 30"),
                payment_due=data.get("payment_due") or "Net 30 post delivery",
                risk=risk_level,
                deliverables=data.get("deliverables") or [],
                usage_rights=str(data.get("usage_rights") or "Digital & social media usage"),
                exclusivity=str(data.get("exclusivity") or "Non-exclusive"),
                additional_terms=data.get("additional_terms") or "",
                contract_body=data.get("contract_body") or "",
                ai_risks=data.get("ai_risks") or [],
                analysis_json=data,
                missing_clauses=data.get("missing_clauses") or [],
                conflicts=data.get("conflicts") or [],
                risk_flags=data.get("risk_flags") or [],
                commercial_terms_match=data.get("commercial_terms") or {},
                overall_status=overall_status,
            )
            self.db.add(contract)
        else:
            contract.agent_run_id = run.id
            contract.value = float(data.get("agreed_value") or contract.value)
            contract.currency = str(data.get("currency") or contract.currency)
            contract.start_date = data.get("start_date") or contract.start_date
            contract.end_date = data.get("end_date") or contract.end_date
            contract.payment_due = data.get("payment_due") or contract.payment_due
            contract.risk = risk_level
            contract.deliverables = data.get("deliverables") or contract.deliverables
            contract.usage_rights = str(data.get("usage_rights") or contract.usage_rights)
            contract.exclusivity = str(data.get("exclusivity") or contract.exclusivity)
            contract.additional_terms = data.get("additional_terms") or contract.additional_terms
            contract.contract_body = data.get("contract_body") or contract.contract_body
            contract.ai_risks = data.get("ai_risks") or contract.ai_risks
            contract.analysis_json = data
            contract.missing_clauses = data.get("missing_clauses") or []
            contract.conflicts = data.get("conflicts") or []
            contract.risk_flags = data.get("risk_flags") or []
            contract.commercial_terms_match = data.get("commercial_terms") or {}
            contract.overall_status = overall_status
            # Keep status as pending_signature or current if not yet approved
            if contract.status not in ("APPROVED", "signed"):
                contract.status = "pending_signature"

        await self.db.flush()

        # Update matching OutreachMessage
        if inf_id:
            outreach_stmt = (
                select(OutreachMessage)
                .where(
                    OutreachMessage.campaign_id == campaign.id,
                    OutreachMessage.influencer_id == inf_id,
                )
                .order_by(OutreachMessage.created_at.desc())
                .limit(1)
            )
            outreach_res = await self.db.execute(outreach_stmt)
            outreach_msg = outreach_res.scalar_one_or_none()
            if outreach_msg:
                outreach_msg.contract_id = contract.id
                outreach_msg.status = "CONTRACT_GENERATED"
                await self.db.flush()

        # Record activity
        act = CampaignActivity(
            user_id=campaign.owner_id,
            campaign_id=campaign.id,
            activity_type="contract_analyzed",
            title=f"Contract analyzed: {contract.creator}",
            description=f"Verified terms for {contract.creator} (Value: {contract.currency} {contract.value:,.2f} | Risk: {contract.risk.upper()})",
        )
        self.db.add(act)
        await self.db.flush()

        logger.info("Persisted contract %s for campaign %s", contract.id, campaign.id)
        return contract

    async def approve_contract(
        self,
        *,
        campaign: Campaign,
        user: User,
        contract: Contract,
        notes: Optional[str] = None,
    ) -> Contract:
        """Human approval of creator contract."""
        now = datetime.now(timezone.utc)
        contract.status = "APPROVED"
        contract.approved_by = str(user.id)
        contract.approved_at = now

        # Create or update approval record
        appr_id = f"appr-{uuid.uuid4().hex[:12]}"
        appr = Approval(
            id=appr_id,
            agent="Contract Agent",
            type="contract",
            action=f"Approve collaboration agreement with {contract.creator}",
            reason=notes or f"Approved contract with fee {contract.currency} {contract.value:,.2f}",
            campaign=campaign.name,
            financial_impact=f"{contract.currency} {contract.value:,.2f}",
            confidence=1.0,
            timestamp=now.strftime("%Y-%m-%d %H:%M UTC"),
            status="approved",
            user_id=user.id,
            campaign_id=campaign.id,
            agent_run_id=contract.agent_run_id,
        )
        self.db.add(appr)

        # Record campaign activity
        act = CampaignActivity(
            user_id=user.id,
            campaign_id=campaign.id,
            activity_type="contract_approved",
            title=f"Contract approved: {contract.creator}",
            description=f"Collaboration contract approved for {contract.creator} ({contract.currency} {contract.value:,.2f}).",
        )
        self.db.add(act)
        await self.db.flush()

        # Check if all accepted creators now have approved contracts
        accepted_stmt = select(CampaignInfluencer).where(
            CampaignInfluencer.campaign_id == campaign.id,
            CampaignInfluencer.status.in_([CampaignInfluencerStatus.ACCEPTED, "ACCEPTED"]),
        )
        acc_res = await self.db.execute(accepted_stmt)
        accepted_creators = acc_res.scalars().all()

        if accepted_creators:
            approved_contracts_stmt = select(Contract).where(
                Contract.campaign_id == campaign.id,
                Contract.status.in_(["APPROVED", "signed"]),
            )
            app_res = await self.db.execute(approved_contracts_stmt)
            approved_contracts = app_res.scalars().all()
            approved_inf_ids = {c.influencer_id for c in approved_contracts if c.influencer_id}

            all_accepted_approved = all(c.influencer_id in approved_inf_ids for c in accepted_creators)
            if all_accepted_approved and campaign.workflow_state in (
                WorkflowState.CONTRACT_PENDING,
                WorkflowState.OUTREACH_COMPLETED,
            ):
                campaign.workflow_state = WorkflowState.CONTRACT_COMPLETED
                await self.db.flush()

        await self.db.commit()
        await self.db.refresh(contract)
        return contract

    async def request_contract_changes(
        self,
        *,
        campaign: Campaign,
        user: User,
        contract: Contract,
        requested_changes: str,
        reason: str,
    ) -> Contract:
        """Human request for changes on creator contract."""
        now = datetime.now(timezone.utc)
        contract.status = "CHANGES_REQUESTED"
        contract.version = (contract.version or 1) + 1

        history = list(contract.change_requests or [])
        history.append({
            "version": contract.version,
            "requested_changes": requested_changes,
            "reason": reason,
            "requested_by": str(user.id),
            "timestamp": now.isoformat(),
        })
        contract.change_requests = history

        # Record activity
        act = CampaignActivity(
            user_id=user.id,
            campaign_id=campaign.id,
            activity_type="contract_changes_requested",
            title=f"Changes requested for {contract.creator} contract",
            description=f"Version {contract.version}: {reason}",
        )
        self.db.add(act)
        await self.db.commit()
        await self.db.refresh(contract)
        return contract

    async def reject_contract(
        self,
        *,
        campaign: Campaign,
        user: User,
        contract: Contract,
        reason: str,
        notes: Optional[str] = None,
    ) -> Contract:
        """Human rejection of creator contract."""
        contract.status = "REJECTED"

        act = CampaignActivity(
            user_id=user.id,
            campaign_id=campaign.id,
            activity_type="contract_rejected",
            title=f"Contract rejected: {contract.creator}",
            description=f"Reason: {reason}" + (f" | Notes: {notes}" if notes else ""),
        )
        self.db.add(act)
        await self.db.commit()
        await self.db.refresh(contract)
        return contract
