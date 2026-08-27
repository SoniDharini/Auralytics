"""Read-only interpreter of campaign journey state.

Does not run agents, mutate records, or replace the Supervisor.
It reads existing PostgreSQL rows and tells the UI what is done and what is next.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.workflow_states import AgentNames, AgentRunStatus, ApprovalStatus
from app.models.agent_execution import AgentRun
from app.models.approval import Approval
from app.models.campaign import Campaign
from app.models.campaign_influencer import CampaignInfluencer, CampaignInfluencerStatus
from app.models.campaign_strategy import CampaignStrategy
from app.models.influencer import Influencer
from app.models.outreach import OutreachMessage
from app.schemas.campaign_workflow import (
    CampaignWorkflowResponse,
    WorkflowAction,
    WorkflowStep,
)


class StepStatus:
    COMPLETED = "COMPLETED"
    CURRENT = "CURRENT"
    NEXT = "NEXT"
    PENDING = "PENDING"
    LOCKED = "LOCKED"
    FAILED = "FAILED"
    WAITING_APPROVAL = "WAITING_APPROVAL"


class WorkflowStepKey:
    CAMPAIGN_CREATED = "CAMPAIGN_CREATED"
    STRATEGY = "STRATEGY"
    DISCOVERY = "DISCOVERY"
    SHORTLIST = "SHORTLIST"
    APPROVAL = "APPROVAL"
    OUTREACH = "OUTREACH"
    CONTRACT = "CONTRACT"
    LAUNCH = "LAUNCH"


class NextStepKey:
    GENERATE_STRATEGY = "GENERATE_STRATEGY"
    DISCOVER_INFLUENCERS = "DISCOVER_INFLUENCERS"
    SHORTLIST_INFLUENCERS = "SHORTLIST_INFLUENCERS"
    APPROVE_SHORTLIST = "APPROVE_SHORTLIST"
    GENERATE_OUTREACH = "GENERATE_OUTREACH"
    REVIEW_OUTREACH = "REVIEW_OUTREACH"
    CONTRACT = "CONTRACT"


_ACTIVE_RUN = {AgentRunStatus.QUEUED, AgentRunStatus.RUNNING}
_SUCCESS_RUN = {AgentRunStatus.COMPLETED, AgentRunStatus.WAITING_APPROVAL}
_PENDING_APPROVAL = {ApprovalStatus.PENDING, ApprovalStatus.PENDING_U, "PENDING"}
_APPROVED_APPROVAL = {
    ApprovalStatus.APPROVED,
    ApprovalStatus.APPROVED_U,
    ApprovalStatus.MODIFIED,
    ApprovalStatus.MODIFIED_U,
    "approved",
    "APPROVED",
    "edit",
    "modified",
}
_REJECTED_APPROVAL = {ApprovalStatus.REJECTED, ApprovalStatus.REJECTED_U, "rejected", "REJECTED"}

# Progress is the six currently implemented stages.
_PROGRESS_KEYS = (
    WorkflowStepKey.CAMPAIGN_CREATED,
    WorkflowStepKey.STRATEGY,
    WorkflowStepKey.DISCOVERY,
    WorkflowStepKey.SHORTLIST,
    WorkflowStepKey.APPROVAL,
    WorkflowStepKey.OUTREACH,
)

_STEPPER: Tuple[Tuple[str, str], ...] = (
    (WorkflowStepKey.CAMPAIGN_CREATED, "Campaign Created"),
    (WorkflowStepKey.STRATEGY, "AI Strategy"),
    (WorkflowStepKey.DISCOVERY, "Influencer Discovery"),
    (WorkflowStepKey.SHORTLIST, "Shortlist"),
    (WorkflowStepKey.APPROVAL, "Approval"),
    (WorkflowStepKey.OUTREACH, "Outreach"),
    (WorkflowStepKey.CONTRACT, "Contract"),
    (WorkflowStepKey.LAUNCH, "Campaign Live"),
)


class CampaignWorkflowService:
    """Pure read layer over campaign / strategy / discovery / approval / outreach rows."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_state(self, campaign: Campaign) -> CampaignWorkflowResponse:
        strategy_exists = await self._has_strategy(campaign.id)
        latest_strategy_run = await self._latest_run(campaign.id, AgentNames.STRATEGY)
        latest_discovery_run = await self._latest_run(campaign.id, AgentNames.DISCOVERY)
        latest_outreach_run = await self._latest_run(campaign.id, AgentNames.OUTREACH)

        discovered_count = await self._count_links(campaign.id)
        shortlisted_count = await self._count_shortlisted(campaign.id)
        outreach_count = await self._count_outreach(campaign.id)
        latest_approval = await self._latest_approval(campaign.id)

        discovery_exists = (
            discovered_count > 0
            or campaign.last_discovery_at is not None
            or (latest_discovery_run is not None and latest_discovery_run.status in _SUCCESS_RUN)
        )
        approval_pending = bool(
            latest_approval and str(latest_approval.status) in _PENDING_APPROVAL
        )
        approval_done = bool(
            latest_approval and str(latest_approval.status) in _APPROVED_APPROVAL
        )
        approval_rejected = bool(
            latest_approval and str(latest_approval.status) in _REJECTED_APPROVAL
        )

        focus = self._resolve_focus(
            strategy_exists=strategy_exists,
            strategy_run=latest_strategy_run,
            discovery_exists=discovery_exists,
            discovery_run=latest_discovery_run,
            discovered_count=discovered_count,
            shortlisted_count=shortlisted_count,
            approval_pending=approval_pending,
            approval_done=approval_done,
            approval_rejected=approval_rejected,
            outreach_count=outreach_count,
            outreach_run=latest_outreach_run,
        )

        action: WorkflowAction = focus["next_action"]
        if not action.route:
            default_route, _tab = self._step_target(campaign.id, focus["current_step"])
            action = action.model_copy(update={"route": default_route})
            focus["next_action"] = action

        steps = self._build_steps(campaign.id, focus)
        completed = sum(1 for s in steps if s.key in _PROGRESS_KEYS and s.status == StepStatus.COMPLETED)
        progress = int(round((completed / len(_PROGRESS_KEYS)) * 100))

        return CampaignWorkflowResponse(
            campaign_id=campaign.id,
            current_step=focus["current_step"],
            next_step=focus["next_step"],
            progress_percentage=progress,
            blocking_reason=focus.get("blocking_reason"),
            next_action=action,
            steps=steps,
            discovered_count=discovered_count,
            shortlisted_count=shortlisted_count,
            outreach_count=outreach_count,
            pending_approval=approval_pending,
        )

    # -- focus --------------------------------------------------------------

    def _resolve_focus(self, **ctx: Any) -> Dict[str, Any]:
        strategy_exists: bool = ctx["strategy_exists"]
        strategy_run: Optional[AgentRun] = ctx["strategy_run"]
        discovery_exists: bool = ctx["discovery_exists"]
        discovery_run: Optional[AgentRun] = ctx["discovery_run"]
        discovered_count: int = ctx["discovered_count"]
        shortlisted_count: int = ctx["shortlisted_count"]
        approval_pending: bool = ctx["approval_pending"]
        approval_done: bool = ctx["approval_done"]
        approval_rejected: bool = ctx["approval_rejected"]
        outreach_count: int = ctx["outreach_count"]
        outreach_run: Optional[AgentRun] = ctx["outreach_run"]

        if self._is_active(strategy_run):
            return self._focus(
                WorkflowStepKey.STRATEGY,
                NextStepKey.GENERATE_STRATEGY,
                StepStatus.CURRENT,
                "Generate AI Strategy",
                "Auralytics is analyzing your campaign brief and writing the strategy.",
                tab="strategy",
                enabled=False,
                running=True,
                running_label="Generating Strategy...",
            )
        if self._is_failed(strategy_run) and not strategy_exists:
            return self._focus(
                WorkflowStepKey.STRATEGY,
                NextStepKey.GENERATE_STRATEGY,
                StepStatus.FAILED,
                "Retry Strategy",
                "The strategy could not be generated. Retry the Strategy Agent to continue.",
                tab="strategy",
                blocking_reason="Strategy generation failed. Discovery stays locked until a strategy exists.",
            )
        if not strategy_exists:
            return self._focus(
                WorkflowStepKey.STRATEGY,
                NextStepKey.GENERATE_STRATEGY,
                StepStatus.NEXT,
                "Generate AI Strategy",
                "Auralytics will analyze your campaign brief and create the strategy that will guide influencer discovery.",
                tab="strategy",
            )

        if self._is_active(discovery_run):
            return self._focus(
                WorkflowStepKey.DISCOVERY,
                NextStepKey.DISCOVER_INFLUENCERS,
                StepStatus.CURRENT,
                "Discovering Influencers...",
                "Analyzing creators that match this campaign strategy.",
                tab="influencers",
                enabled=False,
                running=True,
                running_label="Discovering Influencers...",
            )
        if not discovery_exists:
            return self._focus(
                WorkflowStepKey.DISCOVERY,
                NextStepKey.DISCOVER_INFLUENCERS,
                StepStatus.NEXT,
                "Discover Influencers",
                "Your AI strategy is ready. Find real creators that best match this campaign.",
                tab="influencers",
            )
        # YouTube facts are the discovery source of truth. A failed Grok ranking
        # after real creators were saved must not lock the shortlist step.
        if self._is_failed(discovery_run) and discovered_count <= 0:
            return self._focus(
                WorkflowStepKey.DISCOVERY,
                NextStepKey.DISCOVER_INFLUENCERS,
                StepStatus.FAILED,
                "Retry Discovery",
                "Influencer discovery failed. Retry to find creators that match your strategy.",
                tab="influencers",
                blocking_reason="Discovery failed. Shortlist stays locked until creators are found.",
            )

        if shortlisted_count <= 0:
            return self._focus(
                WorkflowStepKey.SHORTLIST,
                NextStepKey.SHORTLIST_INFLUENCERS,
                StepStatus.NEXT,
                "Review Influencers",
                "Auralytics found and ranked creators for your campaign. Shortlist the ones you want to work with.",
                tab="influencers",
            )

        if approval_pending or approval_rejected:
            status = StepStatus.WAITING_APPROVAL if approval_pending else StepStatus.NEXT
            description = (
                "Waiting for your approval. Review the shortlisted creators before starting outreach."
                if approval_pending
                else "The shortlist was not approved. Review it in Approval Center to continue."
            )
            return self._focus(
                WorkflowStepKey.APPROVAL,
                NextStepKey.APPROVE_SHORTLIST,
                status,
                "Review Shortlist",
                description,
                route="/app/approvals",
                tab=None,
            )

        if self._is_active(outreach_run):
            return self._focus(
                WorkflowStepKey.OUTREACH,
                NextStepKey.GENERATE_OUTREACH,
                StepStatus.CURRENT,
                "Generating Outreach...",
                "Generating personalized outreach for your approved creators.",
                tab="outreach",
                enabled=False,
                running=True,
                running_label="Generating Outreach...",
            )
        if self._is_failed(outreach_run) and outreach_count <= 0:
            return self._focus(
                WorkflowStepKey.OUTREACH,
                NextStepKey.GENERATE_OUTREACH,
                StepStatus.FAILED,
                "Retry Outreach",
                "Outreach generation failed. Retry to create personalized collaboration messages.",
                tab="outreach",
                blocking_reason="Outreach generation failed.",
            )
        if outreach_count <= 0:
            ready = shortlisted_count
            noun = "influencer" if ready == 1 else "influencers"
            prefix = f"{ready} approved {noun} are ready for personalized outreach."
            if not approval_done:
                prefix = f"{ready} shortlisted {noun} are ready for personalized outreach."
            return self._focus(
                WorkflowStepKey.OUTREACH,
                NextStepKey.GENERATE_OUTREACH,
                StepStatus.NEXT,
                "Generate Outreach",
                prefix,
                tab="outreach",
            )

        return self._focus(
            WorkflowStepKey.OUTREACH,
            NextStepKey.REVIEW_OUTREACH,
            StepStatus.COMPLETED,
            "Review Outreach",
            "Personalized outreach is ready. Review the drafts before sending.",
            tab="outreach",
        )

    def _focus(
        self,
        current_step: str,
        next_step: str,
        step_status: str,
        label: str,
        description: str,
        tab: Optional[str] = None,
        route: Optional[str] = None,
        enabled: bool = True,
        running: bool = False,
        running_label: Optional[str] = None,
        blocking_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        display_label = running_label if running else label
        return {
            "current_step": current_step,
            "next_step": next_step,
            "step_status": step_status,
            "blocking_reason": blocking_reason,
            "next_action": WorkflowAction(
                key=next_step,
                label=display_label,
                description=description,
                route=route or "",
                tab=tab,
                enabled=enabled,
                running=running,
            ),
        }

    def _build_steps(self, campaign_id: str, focus: Dict[str, Any]) -> List[WorkflowStep]:
        current_key: str = focus["current_step"]
        current_status: str = focus["step_status"]
        reached_current = False
        steps: List[WorkflowStep] = []

        for key, label in _STEPPER:
            route, tab = self._step_target(campaign_id, key)
            if key == WorkflowStepKey.CAMPAIGN_CREATED:
                status = StepStatus.COMPLETED
            elif key == current_key:
                status = current_status
                reached_current = True
            elif not reached_current:
                status = StepStatus.COMPLETED
            else:
                status = StepStatus.LOCKED

            hint = None
            if status == StepStatus.LOCKED:
                hint = self._lock_hint(current_key)
            elif status == StepStatus.FAILED:
                hint = focus.get("blocking_reason")

            steps.append(
                WorkflowStep(
                    key=key,
                    label=label,
                    status=status,
                    route=route if status != StepStatus.LOCKED else None,
                    tab=tab if status != StepStatus.LOCKED else None,
                    hint=hint,
                )
            )
        return steps

    @staticmethod
    def _step_target(campaign_id: str, key: str) -> Tuple[str, Optional[str]]:
        base = f"/app/campaigns/{campaign_id}"
        mapping = {
            WorkflowStepKey.CAMPAIGN_CREATED: (f"{base}?tab=overview", "overview"),
            WorkflowStepKey.STRATEGY: (f"{base}?tab=strategy", "strategy"),
            WorkflowStepKey.DISCOVERY: (f"{base}?tab=influencers", "influencers"),
            WorkflowStepKey.SHORTLIST: (f"{base}?tab=influencers", "influencers"),
            WorkflowStepKey.APPROVAL: ("/app/approvals", None),
            WorkflowStepKey.OUTREACH: (f"{base}?tab=outreach", "outreach"),
            WorkflowStepKey.CONTRACT: (f"{base}?tab=contracts", "contracts"),
            WorkflowStepKey.LAUNCH: (f"{base}?tab=overview", "overview"),
        }
        return mapping[key]

    @staticmethod
    def _lock_hint(current_key: str) -> str:
        hints = {
            WorkflowStepKey.STRATEGY: "Complete AI Strategy first.",
            WorkflowStepKey.DISCOVERY: "Complete influencer discovery first.",
            WorkflowStepKey.SHORTLIST: "Shortlist creators first.",
            WorkflowStepKey.APPROVAL: "Approve the shortlist first.",
            WorkflowStepKey.OUTREACH: "Generate outreach first.",
        }
        return hints.get(current_key, "Complete the previous step first.")

    @staticmethod
    def _is_active(run: Optional[AgentRun]) -> bool:
        return bool(run and run.status in _ACTIVE_RUN)

    @staticmethod
    def _is_failed(run: Optional[AgentRun]) -> bool:
        return bool(run and run.status == AgentRunStatus.FAILED)

    # -- queries ------------------------------------------------------------

    async def _has_strategy(self, campaign_id: str) -> bool:
        result = await self.db.execute(
            select(func.count()).select_from(CampaignStrategy).where(
                CampaignStrategy.campaign_id == campaign_id
            )
        )
        return int(result.scalar_one() or 0) > 0

    async def _latest_run(self, campaign_id: str, agent_name: str) -> Optional[AgentRun]:
        result = await self.db.execute(
            select(AgentRun)
            .where(AgentRun.campaign_id == campaign_id, AgentRun.agent_name == agent_name)
            .order_by(AgentRun.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _count_links(self, campaign_id: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(CampaignInfluencer).where(
                CampaignInfluencer.campaign_id == campaign_id
            )
        )
        return int(result.scalar_one() or 0)

    async def _count_shortlisted(self, campaign_id: str) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(CampaignInfluencer)
            .join(Influencer, CampaignInfluencer.influencer_id == Influencer.id)
            .where(
                CampaignInfluencer.campaign_id == campaign_id,
                or_(
                    CampaignInfluencer.status.in_(
                        (CampaignInfluencerStatus.SHORTLISTED, CampaignInfluencerStatus.CONTACTED)
                    ),
                    Influencer.shortlisted.is_(True),
                ),
            )
        )
        return int(result.scalar_one() or 0)

    async def _count_outreach(self, campaign_id: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(OutreachMessage).where(
                OutreachMessage.campaign_id == campaign_id
            )
        )
        return int(result.scalar_one() or 0)

    async def _latest_approval(self, campaign_id: str) -> Optional[Approval]:
        result = await self.db.execute(
            select(Approval)
            .where(Approval.campaign_id == campaign_id)
            .order_by(Approval.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
