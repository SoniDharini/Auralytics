"""Read-only interpreter of campaign journey state.

Does not run agents, mutate records, or replace the Supervisor.
It reads existing PostgreSQL rows and tells the UI what is done and what is next.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.optimization import campaign_timeline
from app.ai.workflow_states import AgentNames, AgentRunStatus, ApprovalStatus
from app.models.agent_execution import AgentRun
from app.models.approval import Approval
from app.models.campaign import Campaign
from app.models.campaign_content import (
    CampaignContent,
    ContentPerformanceSnapshot,
    OptimizationPlan,
    PerformanceAnalysis,
)
from app.models.campaign_influencer import CampaignInfluencer, CampaignInfluencerStatus
from app.models.campaign_strategy import CampaignStrategy
from app.models.contract import Contract
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
    PERFORMANCE = "PERFORMANCE"
    OPTIMIZATION = "OPTIMIZATION"


class NextStepKey:
    GENERATE_STRATEGY = "GENERATE_STRATEGY"
    DISCOVER_INFLUENCERS = "DISCOVER_INFLUENCERS"
    SHORTLIST_INFLUENCERS = "SHORTLIST_INFLUENCERS"
    APPROVE_SHORTLIST = "APPROVE_SHORTLIST"
    GENERATE_OUTREACH = "GENERATE_OUTREACH"
    REVIEW_OUTREACH = "REVIEW_OUTREACH"
    CONTRACT = "CONTRACT"
    TRACK_PERFORMANCE = "TRACK_PERFORMANCE"
    ANALYZE_PERFORMANCE = "ANALYZE_PERFORMANCE"
    OPTIMIZE_CAMPAIGN = "OPTIMIZE_CAMPAIGN"
    REVIEW_OPTIMIZATION = "REVIEW_OPTIMIZATION"
    APPROVE_OPTIMIZATION = "APPROVE_OPTIMIZATION"
    CONTINUE_MONITORING = "CONTINUE_MONITORING"
    COMPLETE_CAMPAIGN = "COMPLETE_CAMPAIGN"


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

# Full campaign progress lifecycle.
_PROGRESS_KEYS = (
    WorkflowStepKey.CAMPAIGN_CREATED,
    WorkflowStepKey.STRATEGY,
    WorkflowStepKey.DISCOVERY,
    WorkflowStepKey.SHORTLIST,
    WorkflowStepKey.APPROVAL,
    WorkflowStepKey.OUTREACH,
    WorkflowStepKey.CONTRACT,
    WorkflowStepKey.PERFORMANCE,
    WorkflowStepKey.OPTIMIZATION,
)

_STEPPER: Tuple[Tuple[str, str], ...] = (
    (WorkflowStepKey.CAMPAIGN_CREATED, "Campaign Created"),
    (WorkflowStepKey.STRATEGY, "AI Strategy"),
    (WorkflowStepKey.DISCOVERY, "Influencer Discovery"),
    (WorkflowStepKey.SHORTLIST, "Shortlist"),
    (WorkflowStepKey.APPROVAL, "Approval"),
    (WorkflowStepKey.OUTREACH, "Outreach"),
    (WorkflowStepKey.CONTRACT, "Contract"),
    (WorkflowStepKey.PERFORMANCE, "Performance"),
    (WorkflowStepKey.OPTIMIZATION, "Optimization"),
)


class CampaignWorkflowService:
    """Pure read layer over campaign / strategy / discovery / approval / outreach / contract / performance rows."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_state(self, campaign: Campaign) -> CampaignWorkflowResponse:
        strategy_exists = await self._has_strategy(campaign.id)
        latest_strategy_run = await self._latest_run(campaign.id, AgentNames.STRATEGY)
        latest_discovery_run = await self._latest_run(campaign.id, AgentNames.DISCOVERY)
        latest_outreach_run = await self._latest_run(campaign.id, AgentNames.OUTREACH)
        latest_contract_run = await self._latest_run(campaign.id, AgentNames.CONTRACT)
        latest_performance_run = await self._latest_run(campaign.id, AgentNames.PERFORMANCE)
        latest_optimization_run = await self._latest_run(campaign.id, AgentNames.OPTIMIZATION)

        discovered_count = await self._count_links(campaign.id)
        shortlisted_count = await self._count_shortlisted(campaign.id)
        outreach_count = await self._count_outreach(campaign.id)
        latest_approval = await self._latest_approval(campaign.id)

        accepted_count = await self._count_accepted(campaign.id)
        contract_stats = await self._get_contract_stats(campaign.id)
        content_count = await self._count_content(campaign.id)
        pending_opt_approvals = await self._count_pending_optimization_approvals(campaign.id)

        has_optimization_plan = await self._has_optimization_plan(campaign.id)
        has_performance_analysis = await self._has_performance_analysis(campaign.id)
        completed_content_count = await self._count_completed_content(campaign.id)
        optimization_stale = await self._optimization_is_stale(campaign.id)

        discovery_exists = (
            discovered_count > 0
            or shortlisted_count > 0
            or outreach_count > 0
            or contract_stats["total"] > 0
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
            campaign=campaign,
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
            accepted_count=accepted_count,
            contract_run=latest_contract_run,
            contract_stats=contract_stats,
            content_count=content_count,
            completed_content_count=completed_content_count,
            has_performance_analysis=has_performance_analysis,
            performance_run=latest_performance_run,
            optimization_run=latest_optimization_run,
            has_optimization_plan=has_optimization_plan,
            pending_opt_approvals=pending_opt_approvals,
            optimization_stale=optimization_stale,
        )

        action: WorkflowAction = focus["next_action"]
        if not action.route:
            default_route, _tab = self._step_target(campaign.id, focus["current_step"])
            action = action.model_copy(update={"route": default_route})
            focus["next_action"] = action

        secondary = focus.get("secondary_action")
        if isinstance(secondary, WorkflowAction) and not secondary.route:
            default_route, _tab = self._step_target(campaign.id, focus["current_step"])
            secondary = secondary.model_copy(update={"route": default_route})
            focus["secondary_action"] = secondary

        steps = self._build_steps(campaign.id, focus)
        is_completed = bool(focus.get("is_completed"))
        completed = sum(1 for s in steps if s.key in _PROGRESS_KEYS and s.status == StepStatus.COMPLETED)
        progress = 100 if is_completed else min(89, int(round((completed / len(_PROGRESS_KEYS)) * 100)))
        timeline = campaign_timeline(campaign, datetime.now(timezone.utc))

        return CampaignWorkflowResponse(
            campaign_id=campaign.id,
            current_step=focus["current_step"],
            next_step=focus["next_step"],
            progress_percentage=progress,
            is_completed=is_completed,
            timeline_ended=bool(timeline.get("campaign_timeline_ended")),
            blocking_reason=focus.get("blocking_reason"),
            next_action=action,
            secondary_action=secondary if isinstance(secondary, WorkflowAction) else None,
            steps=steps,
            discovered_count=discovered_count,
            shortlisted_count=shortlisted_count,
            outreach_count=outreach_count,
            pending_approval=approval_pending or pending_opt_approvals > 0,
        )

    # -- focus --------------------------------------------------------------

    def _resolve_focus(self, **ctx: Any) -> Dict[str, Any]:
        campaign: Campaign = ctx["campaign"]
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
        accepted_count: int = ctx.get("accepted_count", 0)
        contract_run: Optional[AgentRun] = ctx.get("contract_run")
        contract_stats: Dict[str, int] = ctx.get(
            "contract_stats", {"total": 0, "approved": 0, "pending": 0}
        )
        content_count: int = ctx.get("content_count", 0)
        completed_content_count: int = ctx.get("completed_content_count", 0)
        has_performance_analysis: bool = ctx.get("has_performance_analysis", False)
        performance_run: Optional[AgentRun] = ctx.get("performance_run")
        optimization_run: Optional[AgentRun] = ctx.get("optimization_run")
        has_optimization_plan: bool = ctx.get("has_optimization_plan", False)
        pending_opt_approvals: int = ctx.get("pending_opt_approvals", 0)
        optimization_stale: bool = ctx.get("optimization_stale", False)

        # 1. Authoritative check: if campaign is completed, all stages are complete.
        if (
            campaign.status == "completed"
            or campaign.workflow_state == "COMPLETED"
        ):
            return {
                "current_step": WorkflowStepKey.OPTIMIZATION,
                "next_step": "",
                "step_status": StepStatus.COMPLETED,
                "is_completed": True,
                "blocking_reason": None,
                "next_action": WorkflowAction(
                    key="",
                    label="Campaign Completed",
                    description="All campaign stages have been completed.",
                    route=f"/app/campaigns/{campaign.id}?tab=overview",
                    tab="overview",
                    enabled=False,
                    running=False,
                ),
            }

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
        if self._is_failed(discovery_run) and discovered_count <= 0 and contract_stats["total"] <= 0:
            return self._focus(
                WorkflowStepKey.DISCOVERY,
                NextStepKey.DISCOVER_INFLUENCERS,
                StepStatus.FAILED,
                "Retry Discovery",
                "Influencer discovery failed. Retry to find creators that match your strategy.",
                tab="influencers",
                blocking_reason="Discovery failed. Shortlist stays locked until creators are found.",
            )

        if shortlisted_count <= 0 and outreach_count <= 0 and contract_stats["total"] <= 0 and accepted_count <= 0:
            return self._focus(
                WorkflowStepKey.SHORTLIST,
                NextStepKey.SHORTLIST_INFLUENCERS,
                StepStatus.NEXT,
                "Review Influencers",
                "Auralytics found and ranked creators for your campaign. Shortlist the ones you want to work with.",
                tab="influencers",
            )

        if (approval_pending or approval_rejected) and contract_stats["total"] <= 0 and outreach_count <= 0:
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
                route=f"/app/campaigns/{campaign.id}?tab=approvals",
                tab="approvals",
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
        if self._is_failed(outreach_run) and outreach_count <= 0 and contract_stats["total"] <= 0:
            return self._focus(
                WorkflowStepKey.OUTREACH,
                NextStepKey.GENERATE_OUTREACH,
                StepStatus.FAILED,
                "Retry Outreach",
                "Outreach generation failed. Retry to create personalized collaboration messages.",
                tab="outreach",
                blocking_reason="Outreach generation failed.",
            )
        if outreach_count <= 0 and contract_stats["total"] <= 0 and accepted_count <= 0:
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

        # Outreach messages generated. If negotiations not completed and no contracts, review outreach.
        if accepted_count <= 0 and contract_stats["total"] <= 0:
            return self._focus(
                WorkflowStepKey.OUTREACH,
                NextStepKey.REVIEW_OUTREACH,
                StepStatus.COMPLETED,
                "Review Outreach",
                "Personalized outreach is ready. Review the drafts and track creator replies.",
                tab="outreach",
            )

        # Contract Stage
        if self._is_active(contract_run):
            return self._focus(
                WorkflowStepKey.CONTRACT,
                NextStepKey.CONTRACT,
                StepStatus.CURRENT,
                "Synthesizing Contract...",
                "Contract Agent is drafting legal agreement and verifying terms.",
                tab="contracts",
                enabled=False,
                running=True,
                running_label="Synthesizing Contract...",
            )

        if self._is_failed(contract_run) and contract_stats["total"] <= 0:
            return self._focus(
                WorkflowStepKey.CONTRACT,
                NextStepKey.CONTRACT,
                StepStatus.FAILED,
                "Retry Contract",
                "Contract drafting failed. Retry Contract Agent to synthesize agreement.",
                tab="contracts",
                blocking_reason="Contract generation failed.",
            )

        if contract_stats["total"] <= 0:
            noun = "creator" if accepted_count == 1 else "creators"
            return self._focus(
                WorkflowStepKey.CONTRACT,
                NextStepKey.CONTRACT,
                StepStatus.NEXT,
                "Generate Contract",
                f"{accepted_count} {noun} agreed to terms. Generate and verify collaboration agreement.",
                tab="contracts",
            )

        if contract_stats["approved"] <= 0:
            return self._focus(
                WorkflowStepKey.CONTRACT,
                NextStepKey.CONTRACT,
                StepStatus.WAITING_APPROVAL,
                "Review & Sign Contract",
                f"{contract_stats['total']} contract draft(s) awaiting review and sign-off.",
                tab="contracts",
            )

        # Contracts approved -> Performance stage
        if self._is_active(performance_run):
            return self._focus(
                WorkflowStepKey.PERFORMANCE,
                NextStepKey.ANALYZE_PERFORMANCE,
                StepStatus.CURRENT,
                "Analyzing Performance...",
                "Performance Agent is evaluating video metrics and baseline lift.",
                tab="performance",
                enabled=False,
                running=True,
                running_label="Analyzing Performance...",
            )

        if self._is_failed(performance_run):
            return self._focus(
                WorkflowStepKey.PERFORMANCE,
                NextStepKey.ANALYZE_PERFORMANCE,
                StepStatus.FAILED,
                "Retry Performance Analysis",
                "Performance analysis encountered an issue. Retry to evaluate KPIs and baseline lift.",
                tab="performance",
                blocking_reason="Performance analysis failed.",
            )

        performance_completed = bool(
            (performance_run and performance_run.status in _SUCCESS_RUN)
            or has_performance_analysis
            or (completed_content_count > 0 and (campaign.status == "completed" or campaign.workflow_state in ("COMPLETED", "OPTIMIZATION_PENDING", "OPTIMIZATION_APPROVAL_PENDING")))
        )

        if not performance_completed:
            if content_count <= 0:
                return self._focus(
                    WorkflowStepKey.PERFORMANCE,
                    NextStepKey.TRACK_PERFORMANCE,
                    StepStatus.NEXT,
                    "Track Campaign Performance",
                    "Contracts approved. Add live video URL or monitor published content performance.",
                    tab="performance",
                )
            return self._focus(
                WorkflowStepKey.PERFORMANCE,
                NextStepKey.ANALYZE_PERFORMANCE,
                StepStatus.NEXT,
                "Analyze Performance",
                f"Tracking {content_count} content video(s). Run Performance Agent to evaluate KPIs.",
                tab="performance",
            )

        # Performance completed -> Optimization stage
        if self._is_active(optimization_run):
            return self._focus(
                WorkflowStepKey.OPTIMIZATION,
                NextStepKey.OPTIMIZE_CAMPAIGN,
                StepStatus.CURRENT,
                "Generating Optimizations...",
                "Optimization Agent is analyzing budget shifts and creator reallocation.",
                tab="optimization",
                enabled=False,
                running=True,
                running_label="Generating Optimizations...",
            )

        if pending_opt_approvals > 0:
            return self._focus(
                WorkflowStepKey.OPTIMIZATION,
                NextStepKey.APPROVE_OPTIMIZATION,
                StepStatus.WAITING_APPROVAL,
                "Review Optimization Approvals",
                f"{pending_opt_approvals} optimization recommendation(s) pending approval.",
                route=f"/app/campaigns/{campaign.id}?tab=approvals",
                tab="approvals",
            )

        optimization_completed = bool(
            (optimization_run and optimization_run.status in _SUCCESS_RUN)
            or has_optimization_plan
        )

        if optimization_completed:
            complete_action = WorkflowAction(
                key=NextStepKey.COMPLETE_CAMPAIGN,
                label="Complete Campaign",
                description="Finish this campaign when monitoring is done. Performance and Optimization history are preserved.",
                route=f"/app/campaigns/{campaign.id}?tab=overview",
                tab="overview",
                enabled=pending_opt_approvals == 0,
                running=False,
            )
            if optimization_stale:
                focus = self._focus(
                    WorkflowStepKey.OPTIMIZATION,
                    NextStepKey.OPTIMIZE_CAMPAIGN,
                    StepStatus.COMPLETED,
                    "Refresh Optimization",
                    "New performance data is available. Refresh Optimization using the latest Performance analysis.",
                    route=f"/app/analytics?campaignId={campaign.id}",
                    tab="optimization",
                )
                focus["secondary_action"] = complete_action
                return focus

            focus = self._focus(
                WorkflowStepKey.OPTIMIZATION,
                NextStepKey.CONTINUE_MONITORING,
                StepStatus.COMPLETED,
                "Continue Monitoring",
                "Optimization is complete. Keep the campaign active to refresh Performance later, or complete the campaign when you are ready.",
                tab="performance",
            )
            focus["secondary_action"] = complete_action
            return focus

        return self._focus(
            WorkflowStepKey.OPTIMIZATION,
            NextStepKey.OPTIMIZE_CAMPAIGN,
            StepStatus.NEXT,
            "Run Optimization Agent",
            "Performance analysis complete. Generate budget reallocation and scaling recommendations.",
            route=f"/app/analytics?campaignId={campaign.id}",
            tab="optimization",
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
        if focus.get("is_completed"):
            return [
                WorkflowStep(
                    key=key,
                    label=label,
                    status=StepStatus.COMPLETED,
                    route=self._step_target(campaign_id, key)[0],
                    tab=self._step_target(campaign_id, key)[1],
                    hint=None,
                )
                for key, label in _STEPPER
            ]

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
            WorkflowStepKey.APPROVAL: (f"{base}?tab=approvals", "approvals"),
            WorkflowStepKey.OUTREACH: (f"{base}?tab=outreach", "outreach"),
            WorkflowStepKey.CONTRACT: (f"{base}?tab=contracts", "contracts"),
            WorkflowStepKey.LAUNCH: (f"{base}?tab=performance", "performance"),
            WorkflowStepKey.PERFORMANCE: (f"{base}?tab=performance", "performance"),
            WorkflowStepKey.OPTIMIZATION: (f"{base}?tab=optimization", "optimization"),
        }
        return mapping.get(key, (f"{base}?tab=overview", "overview"))

    @staticmethod
    def _lock_hint(current_key: str) -> str:
        hints = {
            WorkflowStepKey.STRATEGY: "Complete AI Strategy first.",
            WorkflowStepKey.DISCOVERY: "Complete influencer discovery first.",
            WorkflowStepKey.SHORTLIST: "Shortlist creators first.",
            WorkflowStepKey.APPROVAL: "Approve the shortlist first.",
            WorkflowStepKey.OUTREACH: "Generate outreach first.",
            WorkflowStepKey.CONTRACT: "Complete outreach and negotiation first.",
            WorkflowStepKey.PERFORMANCE: "Complete contract approval first.",
            WorkflowStepKey.OPTIMIZATION: "Complete performance analysis first.",
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

    async def _count_accepted(self, campaign_id: str) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(CampaignInfluencer)
            .where(
                CampaignInfluencer.campaign_id == campaign_id,
                CampaignInfluencer.status == CampaignInfluencerStatus.ACCEPTED,
            )
        )
        ci_count = int(result.scalar_one() or 0)
        if ci_count > 0:
            return ci_count

        result_out = await self.db.execute(
            select(func.count())
            .select_from(OutreachMessage)
            .where(
                OutreachMessage.campaign_id == campaign_id,
                or_(
                    OutreachMessage.status.in_(("ACCEPTED", "CONTRACT_GENERATED")),
                    OutreachMessage.response_status == "ACCEPTED",
                ),
            )
        )
        return int(result_out.scalar_one() or 0)

    async def _get_contract_stats(self, campaign_id: str) -> Dict[str, int]:
        result = await self.db.execute(
            select(Contract.status).where(Contract.campaign_id == campaign_id)
        )
        statuses = [str(s).lower() for (s,) in result.all()]
        total = len(statuses)
        approved = sum(1 for s in statuses if s in ("approved", "signed"))
        pending = sum(
            1
            for s in statuses
            if s in ("pending_signature", "ready_for_review", "changes_requested")
        )
        return {"total": total, "approved": approved, "pending": pending}

    async def _count_content(self, campaign_id: str) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(CampaignContent)
            .where(CampaignContent.campaign_id == campaign_id)
        )
        return int(result.scalar_one() or 0)

    async def _count_pending_optimization_approvals(self, campaign_id: str) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Approval)
            .where(
                Approval.campaign_id == campaign_id,
                Approval.status.in_(_PENDING_APPROVAL),
                or_(
                    Approval.agent.ilike("%optimization%"),
                    Approval.type.in_(
                        (
                            "budget",
                            "optimization",
                            "OPTIMIZATION",
                            "BUDGET",
                            "MONITOR",
                            "CREATOR",
                            "CONTENT",
                            "FORMAT",
                            "CTA",
                            "TIMING",
                        )
                    ),
                ),
            )
        )
        return int(result.scalar_one() or 0)

    async def _has_optimization_plan(self, campaign_id: str) -> bool:
        result = await self.db.execute(
            select(func.count()).select_from(OptimizationPlan).where(
                OptimizationPlan.campaign_id == campaign_id
            )
        )
        return int(result.scalar_one() or 0) > 0

    async def _has_performance_analysis(self, campaign_id: str) -> bool:
        result = await self.db.execute(
            select(func.count()).select_from(PerformanceAnalysis).where(
                PerformanceAnalysis.campaign_id == campaign_id
            )
        )
        return int(result.scalar_one() or 0) > 0

    async def _optimization_is_stale(self, campaign_id: str) -> bool:
        plan_res = await self.db.execute(
            select(OptimizationPlan)
            .where(OptimizationPlan.campaign_id == campaign_id)
            .order_by(OptimizationPlan.created_at.desc())
            .limit(1)
        )
        plan = plan_res.scalar_one_or_none()
        if not plan:
            return False

        analysis_stmt = select(PerformanceAnalysis).where(PerformanceAnalysis.campaign_id == campaign_id)
        if plan.campaign_content_id:
            analysis_stmt = analysis_stmt.where(
                PerformanceAnalysis.campaign_content_id == plan.campaign_content_id
            )
        analysis_res = await self.db.execute(
            analysis_stmt.order_by(PerformanceAnalysis.created_at.desc()).limit(1)
        )
        latest_analysis = analysis_res.scalar_one_or_none()
        if latest_analysis and plan.performance_analysis_id != latest_analysis.id:
            return True
        if latest_analysis and plan.created_at and latest_analysis.created_at:
            if latest_analysis.created_at > plan.created_at:
                return True

        content_id = plan.campaign_content_id or (latest_analysis.campaign_content_id if latest_analysis else None)
        if not content_id:
            return False
        snap_res = await self.db.execute(
            select(ContentPerformanceSnapshot)
            .where(ContentPerformanceSnapshot.campaign_content_id == content_id)
            .order_by(ContentPerformanceSnapshot.captured_at.desc())
            .limit(1)
        )
        latest_snap = snap_res.scalar_one_or_none()
        if not latest_snap:
            return False
        if latest_analysis and latest_analysis.latest_snapshot_id and latest_snap.id != latest_analysis.latest_snapshot_id:
            return True
        if latest_analysis and latest_analysis.created_at and latest_snap.captured_at:
            if latest_snap.captured_at > latest_analysis.created_at:
                return True
        return False

    async def _count_completed_content(self, campaign_id: str) -> int:
        from app.models.campaign_content import CampaignContent, TrackingStatus

        result = await self.db.execute(
            select(func.count()).select_from(CampaignContent).where(
                CampaignContent.campaign_id == campaign_id,
                or_(
                    CampaignContent.tracking_status == TrackingStatus.COMPLETED,
                    CampaignContent.current_views > 0,
                ),
            )
        )
        return int(result.scalar_one() or 0)

