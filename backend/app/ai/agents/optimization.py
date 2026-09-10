"""Optimization Agent — evidence-based next actions from the latest Performance analysis."""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field
from sqlalchemy import case, select
from sqlalchemy.orm import selectinload

from app.ai.agents.base import AgentContext, BaseAgent
from app.ai.schemas import AgentResultEnvelope
from app.ai.workflow_states import AgentNames
from app.core.exceptions import AgentValidationException, NotFoundException
from app.models.campaign import Campaign
from app.models.campaign_content import (
    CampaignContent,
    ContentPerformanceSnapshot,
    OptimizationPlan,
    PerformanceAnalysis,
    TrackingStatus,
)
from app.models.campaign_influencer import CampaignInfluencer
from app.models.influencer import Influencer

logger = logging.getLogger(__name__)

NOT_AVAILABLE = "NOT_AVAILABLE"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
UNKNOWN = "UNKNOWN"

_MISSING = {None, "", NOT_AVAILABLE, "N/A", INSUFFICIENT_DATA, UNKNOWN, "DATA_UNAVAILABLE"}

_UNAVAILABLE_CITATION_TERMS: Dict[str, Tuple[str, ...]] = {
    "roi": ("roi", "return on investment"),
    "roas": ("roas",),
    "attributed_revenue": ("attributed revenue", "revenue"),
    "remaining_budget": ("remaining budget",),
    "conversions": ("conversion rate", "conversions"),
    "orders": ("attributed orders", "orders"),
}

_GENERIC_ACTIONS = (
    re.compile(r"^improve engagement\.?$", re.I),
    re.compile(r"^make better content\.?$", re.I),
    re.compile(r"^work with more influencers\.?$", re.I),
    re.compile(r"^increase engagement\.?$", re.I),
)

_ALLOWED_WINDOWS = {1, 2, 3, 5, 7, 8, 10, 12, 14, 18, 20, 24, 30, 36, 48, 72, 90, 168, 720}
_NUMBER_RE = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?x?%?", re.I)


class OptimizationRecommendationItem(BaseModel):
    priority: str = Field(..., description="HIGH, MEDIUM, LOW")
    category: str = Field(..., description="MONITOR, CREATOR, CONTENT, FORMAT, CTA, TIMING, BUDGET")
    action: str = Field(..., description="Specific recommended next step")
    reason: str = Field(..., description="Why this action is recommended")
    evidence: List[str] = Field(default_factory=list, description="Factual metrics supporting this recommendation")
    requires_human_approval: bool = Field(True, description="Always true — requires marketer approval")


class OptimizationAgentOutput(BaseModel):
    overall_assessment: Optional[str] = Field(
        default=None,
        description="CONTINUE_MONITORING | NO_ACTION_NEEDED | ADJUST_STRATEGY | INSUFFICIENT_DATA",
    )
    recommendations: List[OptimizationRecommendationItem] = Field(
        default_factory=list,
        max_length=3,
        description="At most 3 actionable, evidence-based recommendations.",
    )


def present(value: Any) -> Any:
    if value in _MISSING:
        return NOT_AVAILABLE
    return value


def parse_campaign_date(raw: Any) -> Optional[date]:
    if raw in _MISSING:
        return None
    text = str(raw).strip()
    if not text:
        return None
    for fmt, chunk in (
        ("%Y-%m-%d", text[:10]),
        ("%d-%m-%Y", text[:10]),
        ("%m/%d/%Y", text[:10]),
        ("%d/%m/%Y", text[:10]),
    ):
        try:
            return datetime.strptime(chunk, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def campaign_timeline(campaign: Campaign, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    today = now.date()
    start = parse_campaign_date(campaign.start_date)
    end = parse_campaign_date(campaign.end_date)

    age_days: Any = NOT_AVAILABLE
    days_remaining: Any = NOT_AVAILABLE
    time_progress: Any = NOT_AVAILABLE
    timeline_ended = False
    timeline_status = UNKNOWN

    if start is not None:
        age_days = max(0, (today - start).days)
        timeline_status = "ACTIVE"
    if end is not None:
        remaining = (end - today).days
        timeline_ended = remaining < 0
        days_remaining = 0 if timeline_ended else remaining
        timeline_status = "ENDED" if timeline_ended else "ACTIVE"
    if isinstance(age_days, int) and isinstance(days_remaining, int):
        total = age_days + days_remaining
        if total > 0:
            time_progress = round(age_days / total, 3)
        elif timeline_ended:
            time_progress = 1.0

    return {
        "current_datetime": now.isoformat(),
        "start_date": campaign.start_date or NOT_AVAILABLE,
        "end_date": campaign.end_date or NOT_AVAILABLE,
        "campaign_age_days": age_days,
        "days_remaining": days_remaining,
        "campaign_time_progress": time_progress,
        "campaign_timeline_ended": timeline_ended,
        "campaign_timeline_status": timeline_status,
    }


def classify_data_quality(
    *,
    snapshot_count: int,
    content_age_hours: Any,
    baseline_available: bool,
    has_kpis: bool,
) -> str:
    if not has_kpis and snapshot_count <= 0:
        return "INSUFFICIENT"
    early = isinstance(content_age_hours, (int, float)) and content_age_hours <= 24
    if snapshot_count <= 1 or early or not baseline_available:
        return "LIMITED"
    return "SUFFICIENT"


def collect_allowed_numbers(payload: Dict[str, Any]) -> Set[str]:
    found: Set[str] = set(str(n) for n in _ALLOWED_WINDOWS)

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            for value in node.values():
                _walk(value)
            return
        if isinstance(node, (list, tuple)):
            for value in node:
                _walk(value)
            return
        if isinstance(node, bool) or node in _MISSING:
            return
        if isinstance(node, int):
            found.add(str(node))
            return
        if isinstance(node, float):
            found.add(str(node))
            if node == int(node):
                found.add(str(int(node)))
            return
        if isinstance(node, str):
            for match in _NUMBER_RE.findall(node):
                found.add(match.rstrip("xX%"))
            return

    _walk(payload)
    return found


def unavailable_metric_keys(facts: Dict[str, Any]) -> Set[str]:
    missing: Set[str] = set()
    for key, aliases in _UNAVAILABLE_CITATION_TERMS.items():
        value = facts.get(key)
        if value in _MISSING:
            missing.update(aliases)
            missing.add(key.replace("_", " "))
    return missing


def recommendation_text(rec: Dict[str, Any]) -> str:
    evidence = rec.get("evidence") or []
    evidence_text = " ".join(str(item) for item in evidence)
    return " ".join(
        [
            str(rec.get("action") or ""),
            str(rec.get("reason") or ""),
            evidence_text,
        ]
    )


def cites_unavailable_metric(rec: Dict[str, Any], unavailable: Set[str]) -> bool:
    blob = recommendation_text(rec).lower()
    for term in unavailable:
        if not term:
            continue
        for match in re.finditer(rf"(?<![a-z]){re.escape(term.lower())}(?![a-z])", blob):
            window = blob[match.start() : match.end() + 48]
            if any(
                marker in window
                for marker in (
                    "not_available",
                    "not available",
                    "n/a",
                    "unavailable",
                    "insufficient",
                    "unknown",
                )
            ):
                continue
            return True
    return False


def cites_unsupplied_number(rec: Dict[str, Any], allowed: Set[str]) -> bool:
    blob = recommendation_text(rec)
    for raw in _NUMBER_RE.findall(blob):
        token = raw.rstrip("xX%").lstrip("+-")
        if not token:
            continue
        if token in allowed:
            continue
        try:
            as_float = float(token)
        except ValueError:
            return True
        if str(int(as_float)) in allowed if as_float == int(as_float) else False:
            continue
        if str(as_float) in allowed:
            continue
        # Allow small monitoring windows the backend already calculated.
        if as_float in _ALLOWED_WINDOWS:
            continue
        return True
    return False


def _cites_unknown_creator(rec: Dict[str, Any], creator_names: Set[str]) -> bool:
    blob = recommendation_text(rec)
    mentioned = re.findall(r"(?:creator|influencer)\s+([A-Za-z][A-Za-z0-9_ .'&-]{1,40})", blob, flags=re.I)
    for raw_name in mentioned:
        name = raw_name.strip().lower().rstrip(".,;:")
        if name and name not in creator_names and not any(name in known or known in name for known in creator_names):
            return True
    return False


def is_generic_recommendation(rec: Dict[str, Any]) -> bool:
    action = str(rec.get("action") or "").strip()
    evidence = rec.get("evidence") or []
    if any(pattern.match(action) for pattern in _GENERIC_ACTIONS):
        return True
    return not action or (not evidence and len(action.split()) < 4)


def previous_plan_is_stale(prev_plan: Any, current_analysis_id: Optional[str]) -> bool:
    """True when a prior Optimization dict points at a different Performance analysis."""
    if not isinstance(prev_plan, dict) or not current_analysis_id:
        return False
    prev_id = prev_plan.get("performance_analysis_id")
    if prev_id in _MISSING:
        return False
    return str(prev_id) != str(current_analysis_id)


def infer_overall_assessment(recs: List[Dict[str, Any]], data_quality: str) -> str:
    if data_quality == "INSUFFICIENT":
        return "INSUFFICIENT_DATA"
    if not recs:
        return "NO_ACTION_NEEDED"
    categories = {str(r.get("category") or "").upper() for r in recs}
    if categories and categories.issubset({"MONITOR"}):
        return "CONTINUE_MONITORING"
    return "ADJUST_STRATEGY"


def latest_snapshot(content: Optional[CampaignContent]) -> Optional[ContentPerformanceSnapshot]:
    if not content or not content.snapshots:
        return None
    return max(
        content.snapshots,
        key=lambda snap: snap.captured_at or datetime.min.replace(tzinfo=timezone.utc),
    )


class OptimizationAgent(BaseAgent):
    name = AgentNames.OPTIMIZATION
    version = "1.1.0"
    description = "Recommends maximum 3 evidence-based campaign optimization actions from the latest Performance analysis."

    async def build_context(self, ctx: AgentContext) -> Dict[str, Any]:
        campaign = ctx.campaign
        db = ctx.db
        content_id = ctx.extras.get("content_id") or ctx.extras.get("campaign_content_id")
        requested_analysis_id = ctx.extras.get("performance_analysis_id")
        now = datetime.now(timezone.utc)
        timeline = campaign_timeline(campaign, now)

        if requested_analysis_id:
            p_stmt = select(PerformanceAnalysis).where(
                PerformanceAnalysis.id == requested_analysis_id,
                PerformanceAnalysis.campaign_id == campaign.id,
            )
        else:
            p_stmt = (
                select(PerformanceAnalysis)
                .outerjoin(CampaignContent, CampaignContent.id == PerformanceAnalysis.campaign_content_id)
                .where(PerformanceAnalysis.campaign_id == campaign.id)
            )
            if content_id:
                p_stmt = p_stmt.where(PerformanceAnalysis.campaign_content_id == content_id)
            p_stmt = p_stmt.order_by(
                case(
                    (
                        CampaignContent.tracking_status.in_([TrackingStatus.ACTIVE, TrackingStatus.TRACKING]),
                        0,
                    ),
                    else_=1,
                ),
                PerformanceAnalysis.created_at.desc(),
            ).limit(1)

        p_res = await db.execute(p_stmt)
        perf_analysis = p_res.scalar_one_or_none()

        if not perf_analysis:
            raise NotFoundException(
                detail="Performance Agent analysis must be completed before running the Optimization Agent."
            )
        if perf_analysis.campaign_id != campaign.id:
            raise AgentValidationException(detail="Performance analysis does not belong to this campaign.")

        c_stmt = (
            select(CampaignContent)
            .options(selectinload(CampaignContent.influencer), selectinload(CampaignContent.snapshots))
            .where(CampaignContent.id == perf_analysis.campaign_content_id)
        )
        c_res = await db.execute(c_stmt)
        content = c_res.scalar_one_or_none()
        snap = latest_snapshot(content)

        creator_name = "NOT_AVAILABLE"
        if content and content.influencer:
            creator_name = content.influencer.name
        elif content and content.channel_title:
            creator_name = content.channel_title

        creator_names = await self._campaign_creator_names(db, campaign.id)
        if creator_name not in _MISSING and creator_name not in creator_names:
            creator_names.append(creator_name)

        kpis_raw = dict(perf_analysis.raw_kpis or {})
        financial = {
            "actual_spend": present(
                content.agreed_cost if content and content.agreed_cost is not None else campaign.spend
            ),
            "campaign_budget": present(campaign.budget),
            "attributed_revenue": present(
                content.attributed_revenue if content is not None else campaign.revenue
            ),
            "roas": present(content.roas if content is not None else campaign.roas),
            "roi": present(content.roi if content is not None else campaign.roi),
            "remaining_budget": NOT_AVAILABLE,
        }
        if campaign.budget is not None and campaign.spend is not None:
            financial["remaining_budget"] = round(max(0.0, float(campaign.budget) - float(campaign.spend)), 2)

        kpis = {
            "views": present(kpis_raw.get("current_views", content.current_views if content else None)),
            "likes": present(kpis_raw.get("current_likes", content.current_likes if content else None)),
            "comments": present(kpis_raw.get("current_comments", content.current_comments if content else None)),
            "engagement_rate": present(kpis_raw.get("engagement_rate", content.engagement_rate if content else None)),
            "performance_lift_percent": present(
                kpis_raw.get("performance_lift_percent", content.performance_lift_percent if content else None)
            ),
            "cost_per_view": present(kpis_raw.get("cost_per_view", content.cost_per_view if content else None)),
            "cpm": present(kpis_raw.get("cpm", content.cpm if content else None)),
            "cost_per_engagement": present(
                kpis_raw.get("cost_per_engagement", content.cost_per_engagement if content else None)
            ),
            "creator_baseline_median_views": present(content.baseline_median_views if content else None),
            "creator_baseline_avg_views": present(content.baseline_avg_views if content else None),
            "baseline_engagement_rate": present(content.baseline_engagement_rate if content else None),
            "momentum": present(kpis_raw.get("momentum") or (content.momentum if content else None)),
            "roi": financial["roi"],
            "roas": financial["roas"],
            "attributed_revenue": financial["attributed_revenue"],
            "remaining_budget": financial["remaining_budget"],
            "orders": present(content.attributed_orders if content else None),
            "conversions": present(campaign.conversions),
        }

        age_hours = content.content_age_hours if content else None
        published_at = content.published_at.isoformat() if content and content.published_at else NOT_AVAILABLE
        content_stage = present(perf_analysis.content_stage)
        if content and not content.published_at and not perf_analysis.content_stage:
            content_stage = NOT_AVAILABLE

        snapshot_count = len(content.snapshots or []) if content else 0
        baseline_available = bool(content and content.baseline_median_views is not None)
        data_quality = classify_data_quality(
            snapshot_count=snapshot_count,
            content_age_hours=age_hours,
            baseline_available=baseline_available,
            has_kpis=any(v not in _MISSING for v in (kpis.get("views"), kpis.get("likes"))),
        )

        prev_plan = await self._previous_plan(db, campaign.id, content.id if content else None)

        return {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "campaign_objective": campaign.objective or NOT_AVAILABLE,
            "campaign_status": campaign.status,
            "campaign_timeline": timeline,
            "current_datetime": timeline["current_datetime"],
            "start_date": timeline["start_date"],
            "end_date": timeline["end_date"],
            "campaign_age_days": timeline["campaign_age_days"],
            "days_remaining": timeline["days_remaining"],
            "campaign_time_progress": timeline["campaign_time_progress"],
            "campaign_timeline_ended": timeline["campaign_timeline_ended"],
            "financial": financial,
            "performance_analysis_id": perf_analysis.id,
            "latest_snapshot_id": snap.id if snap else present(perf_analysis.latest_snapshot_id),
            "performance_generated_at": perf_analysis.created_at.isoformat() if perf_analysis.created_at else NOT_AVAILABLE,
            "performance_analysis": {
                "status": present(perf_analysis.status),
                "content_stage": content_stage,
                "summary": present(perf_analysis.summary),
                "what_is_working": perf_analysis.what_is_working or [],
                "needs_attention": perf_analysis.needs_attention or [],
                "financial_interpretation": present(perf_analysis.financial_interpretation),
                "next_step": present(perf_analysis.next_step),
                "confidence": present(perf_analysis.confidence),
            },
            "content_id": content.id if content else NOT_AVAILABLE,
            "creator_name": creator_name,
            "campaign_creator_names": creator_names,
            "content_type": content.content_type if content else NOT_AVAILABLE,
            "published_at": published_at,
            "content_age_hours": present(age_hours),
            "content_age_days": present(content.content_age_days if content else None),
            "content_stage": content_stage,
            "momentum": kpis["momentum"],
            "snapshot_count": snapshot_count,
            "latest_snapshot": {
                "id": snap.id,
                "views": snap.views,
                "likes": snap.likes,
                "comments": snap.comments,
                "captured_at": snap.captured_at.isoformat() if snap.captured_at else NOT_AVAILABLE,
            }
            if snap
            else NOT_AVAILABLE,
            "kpis": kpis,
            "data_quality": data_quality,
            "previous_optimization": prev_plan if isinstance(prev_plan, dict) else NOT_AVAILABLE,
            "new_performance_since_previous_optimization": previous_plan_is_stale(
                prev_plan, perf_analysis.id
            ),
        }

    async def _campaign_creator_names(self, db, campaign_id: str) -> List[str]:
        stmt = (
            select(Influencer.name)
            .join(CampaignInfluencer, CampaignInfluencer.influencer_id == Influencer.id)
            .where(CampaignInfluencer.campaign_id == campaign_id)
        )
        res = await db.execute(stmt)
        return [name for (name,) in res.all() if name]

    async def _previous_plan(self, db, campaign_id: str, content_id: Optional[str]) -> Any:
        stmt = select(OptimizationPlan).where(OptimizationPlan.campaign_id == campaign_id)
        if content_id:
            stmt = stmt.where(OptimizationPlan.campaign_content_id == content_id)
        stmt = stmt.order_by(OptimizationPlan.created_at.desc()).limit(1)
        res = await db.execute(stmt)
        plan = res.scalar_one_or_none()
        if not plan:
            return None
        recs = [r for r in (plan.recommendations_json or []) if isinstance(r, dict)]
        return {
            "id": plan.id,
            "generated_at": plan.created_at.isoformat() if plan.created_at else NOT_AVAILABLE,
            "performance_analysis_id": plan.performance_analysis_id or NOT_AVAILABLE,
            "recommendation_actions": [r.get("action") for r in recs if r.get("action")][:3],
            "approval_states": [r.get("status") for r in recs if r.get("status")][:3],
        }

    def build_system_prompt(self, ctx: AgentContext) -> str:
        return (
            "You are the Optimization Agent of Auralytics.\n\n"
            "You receive validated, factual campaign Performance information generated by the "
            "backend and Performance Agent.\n"
            "Your job is to recommend what the marketer should consider doing next.\n"
            "Never invent or recalculate factual metrics.\n"
            "Never invent: views, likes, comments, revenue, spend, ROI, ROAS, conversion rates, "
            "remaining budget, or future performance.\n\n"
            "Always consider:\n"
            "- campaign objective\n"
            "- current date/time\n"
            "- campaign start/end dates\n"
            "- content age\n"
            "- latest Performance snapshot\n"
            "- current momentum\n"
            "- creator baseline\n"
            "- Performance lift\n"
            "- cost efficiency\n"
            "- attributed revenue if available\n"
            "- ROAS if available\n"
            "- ROI if available\n"
            "- remaining campaign duration\n\n"
            "If Performance data is too new or insufficient, recommend monitoring rather than "
            "forcing an optimization action.\n"
            "If no meaningful action is supported by the evidence, return NO_ACTION_NEEDED "
            "with zero recommendations or a single MONITOR recommendation.\n"
            "Return at most 3 recommendations.\n\n"
            "Every recommendation must include: priority, category, action, reason, evidence, "
            "requires_human_approval.\n"
            "Use simple marketer-friendly language.\n"
            "Do not automatically apply any changes.\n"
            "Do not recommend stopping spend on EARLY_STAGE content unless overwhelming factual evidence exists.\n"
            "If campaign_timeline_ended is true, focus on final interpretation and future creator/content "
            "learnings, not real-time tactical posting times.\n"
            "Never cite ROI, ROAS, revenue, remaining budget, or conversions unless those fields are "
            "supplied as real values (not NOT_AVAILABLE / INSUFFICIENT_DATA).\n"
            "Do not generate generic advice such as 'Improve engagement' or 'Make better content'.\n"
            "Return structured JSON only."
        )

    def build_user_prompt(self, ctx: AgentContext, context_payload: Dict[str, Any]) -> str:
        return (
            "Based on the following validated Performance Agent findings and campaign context, "
            "recommend what the marketer should consider doing next.\n\n"
            f"{json.dumps(context_payload, indent=2)}\n\n"
            "Return at most 3 evidence-based recommendations. "
            "If evidence supports no campaign change, set overall_assessment to NO_ACTION_NEEDED "
            "and return an empty recommendations list or a single MONITOR item. "
            "Return strictly valid JSON."
        )

    async def call_llm(
        self,
        ctx: AgentContext,
        system_prompt: str,
        user_prompt: str,
        context_payload: Dict[str, Any],
    ) -> AgentResultEnvelope:
        try:
            output, raw = await self.llm.generate_structured_with_meta(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=OptimizationAgentOutput,
                temperature=0.1,
            )
        except Exception as exc:
            logger.error("Optimization Agent LLM call failed: %s", exc)
            raise AgentValidationException(detail=f"Optimization Agent AI analysis failed: {exc}") from exc

        recs = [r.model_dump() for r in (output.recommendations or [])[:3]]
        data_quality = str(context_payload.get("data_quality") or "LIMITED")
        assessment = output.overall_assessment or infer_overall_assessment(recs, data_quality)
        requires_approval = any(recs)
        if not recs:
            summary = "Current performance does not justify a campaign change. Continue monitoring."
            if data_quality == "INSUFFICIENT":
                summary = "Performance data is insufficient for an optimization change. Continue monitoring."
        else:
            summary = f"Generated {len(recs)} optimization recommendation(s)."

        return AgentResultEnvelope(
            status="SUCCESS",
            summary=summary,
            confidence=0.92,
            recommendations=recs,
            requires_approval=requires_approval,
            data={
                "overall_assessment": assessment,
                "data_quality": data_quality,
                "recommendations": recs,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "performance_analysis_id": context_payload.get("performance_analysis_id"),
                "latest_snapshot_id": context_payload.get("latest_snapshot_id"),
            },
            provider=raw.provider,
            model=raw.model,
            provider_latency_ms=raw.latency_ms,
            grok_called=True,
        )

    async def validate_output(
        self,
        ctx: AgentContext,
        result: AgentResultEnvelope,
        context_payload: Dict[str, Any],
    ) -> AgentResultEnvelope:
        data = dict(result.data or {})
        recs = data.get("recommendations")
        if recs is None:
            recs = result.recommendations or []
        if not isinstance(recs, list):
            raise AgentValidationException(detail="Optimization Agent returned malformed recommendations.")

        recs = recs[:3]
        kpis = context_payload.get("kpis") or {}
        financial = context_payload.get("financial") or {}
        facts = {
            "roi": kpis.get("roi", financial.get("roi")),
            "roas": kpis.get("roas", financial.get("roas")),
            "attributed_revenue": kpis.get("attributed_revenue", financial.get("attributed_revenue")),
            "remaining_budget": kpis.get("remaining_budget", financial.get("remaining_budget")),
            "conversions": kpis.get("conversions"),
            "orders": kpis.get("orders"),
        }
        unavailable = unavailable_metric_keys(facts)
        allowed_numbers = collect_allowed_numbers(context_payload)
        creator_names = {
            str(name).strip().lower()
            for name in (context_payload.get("campaign_creator_names") or [])
            if name and name not in _MISSING
        }
        selected_creator = str(context_payload.get("creator_name") or "").strip().lower()
        if selected_creator and selected_creator not in {NOT_AVAILABLE.lower(), ""}:
            creator_names.add(selected_creator)

        valid: List[Dict[str, Any]] = []
        for rec in recs:
            if not isinstance(rec, dict):
                continue
            rec = dict(rec)
            rec["requires_human_approval"] = True
            rec["priority"] = str(rec.get("priority") or "MEDIUM").upper()
            rec["category"] = str(rec.get("category") or "MONITOR").upper()
            rec["evidence"] = [str(item) for item in (rec.get("evidence") or []) if str(item).strip()]
            if cites_unavailable_metric(rec, unavailable):
                logger.info("Dropped optimization recommendation that cited unavailable metrics: %s", rec.get("action"))
                continue
            if cites_unsupplied_number(rec, allowed_numbers):
                logger.info("Dropped optimization recommendation with unsupplied numeric claims: %s", rec.get("action"))
                continue
            if is_generic_recommendation(rec):
                logger.info("Dropped generic optimization recommendation: %s", rec.get("action"))
                continue
            if creator_names and _cites_unknown_creator(rec, creator_names):
                logger.info("Dropped optimization recommendation for a creator not in this campaign: %s", rec.get("action"))
                continue
            valid.append(rec)

        data_quality = str(context_payload.get("data_quality") or data.get("data_quality") or "LIMITED")
        assessment = infer_overall_assessment(valid, data_quality)
        data["recommendations"] = valid
        data["overall_assessment"] = assessment
        data["data_quality"] = data_quality
        data["performance_analysis_id"] = context_payload.get("performance_analysis_id")
        data["latest_snapshot_id"] = context_payload.get("latest_snapshot_id")
        data["generated_at"] = data.get("generated_at") or datetime.now(timezone.utc).isoformat()
        data["campaign_id"] = context_payload.get("campaign_id")

        result.data = data
        result.recommendations = valid
        result.requires_approval = bool(valid)
        if not valid:
            if data_quality == "INSUFFICIENT":
                result.summary = "Performance data is insufficient for an optimization change. Continue monitoring."
            else:
                result.summary = "Current performance does not justify a campaign change. Continue monitoring."
        else:
            result.summary = f"Generated {len(valid)} optimization recommendation(s)."
        return result
