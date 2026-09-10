"""Performance Agent — Explains and interprets factual campaign content metrics deterministically calculated by backend."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import case, desc, select
from sqlalchemy.orm import selectinload

from app.ai.agents.base import AgentContext, BaseAgent
from app.ai.schemas import AgentResultEnvelope
from app.ai.workflow_states import AgentNames
from app.core.exceptions import AgentValidationException, NotFoundException
from app.models.campaign_content import (
    CampaignContent,
    ContentPerformanceSnapshot,
    PerformanceAnalysis,
    PerformanceStatus,
    ContentStage,
    TrackingStatus,
)
from app.models.campaign_strategy import CampaignStrategy
from app.models.influencer import Influencer

logger = logging.getLogger(__name__)


class PerformanceAgentOutput(BaseModel):
    status: str = Field(..., description="STRONG, ON_TRACK, AVERAGE, NEEDS_ATTENTION, UNDERPERFORMING, EARLY_STAGE")
    content_stage: str = Field(..., description="EARLY_STAGE, INITIAL_MOMENTUM, SHORT_TERM, MATURE, LONG_TERM")
    summary: str = Field(..., description="Clear marketer-friendly summary of content performance")
    what_is_working: List[str] = Field(default_factory=list, description="List of positive signals backed by data")
    needs_attention: List[str] = Field(default_factory=list, description="List of issues, lags, or data gaps")
    financial_interpretation: str = Field(..., description="Explanation of spend, revenue, ROAS, and ROI")
    next_step: str = Field(..., description="Actionable recommendation for the marketer")
    confidence: float = Field(0.9, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")


class PerformanceAgent(BaseAgent):
    name = AgentNames.PERFORMANCE
    version = "1.0.0"
    description = "Interprets factual YouTube content performance and financial attribution."

    async def build_context(self, ctx: AgentContext) -> Dict[str, Any]:
        campaign = ctx.campaign
        db = ctx.db
        content_id = ctx.extras.get("content_id") or ctx.extras.get("campaign_content_id")

        if content_id:
            c_stmt = (
                select(CampaignContent)
                .options(selectinload(CampaignContent.snapshots), selectinload(CampaignContent.influencer))
                .where(CampaignContent.id == content_id, CampaignContent.campaign_id == campaign.id)
            )
        else:
            c_stmt = (
                select(CampaignContent)
                .options(selectinload(CampaignContent.snapshots), selectinload(CampaignContent.influencer))
                .where(CampaignContent.campaign_id == campaign.id)
                .order_by(
                    case(
                        (
                            CampaignContent.tracking_status.in_(
                                [TrackingStatus.ACTIVE, TrackingStatus.TRACKING]
                            ),
                            0,
                        ),
                        else_=1,
                    ),
                    CampaignContent.updated_at.desc(),
                )
                .limit(1)
            )

        c_res = await db.execute(c_stmt)
        content = c_res.scalar_one_or_none()

        if not content:
            raise NotFoundException(detail="No tracked campaign content found to analyze.")

        # Influencer details
        influencer = content.influencer
        if not influencer and content.influencer_id:
            inf_res = await db.execute(select(Influencer).where(Influencer.id == content.influencer_id))
            influencer = inf_res.scalar_one_or_none()

        # Strategy context
        strat_stmt = (
            select(CampaignStrategy)
            .where(CampaignStrategy.campaign_id == campaign.id)
            .order_by(CampaignStrategy.version.desc())
            .limit(1)
        )
        strat_res = await db.execute(strat_stmt)
        strategy = strat_res.scalar_one_or_none()
        strategy_summary = strategy.strategy_json.get("summary") if strategy and strategy.strategy_json else None

        # Snapshots
        snapshots = content.snapshots or []
        latest_snapshot = snapshots[-1] if snapshots else None
        prev_snapshot = snapshots[-2] if len(snapshots) >= 2 else None

        snapshot_growth = {
            "snapshots_recorded": len(snapshots),
            "views_gained": (latest_snapshot.views - prev_snapshot.views) if (latest_snapshot and prev_snapshot) else 0,
            "growth_percentage": latest_snapshot.view_growth_percentage if latest_snapshot else 0.0,
        }

        # Format deterministic KPIs
        kpis = {
            "views": content.current_views,
            "likes": content.current_likes,
            "comments": content.current_comments,
            "engagements": (content.current_likes or 0) + (content.current_comments or 0),
            "engagement_rate_percent": content.engagement_rate,
            "baseline_median_views": content.baseline_median_views,
            "baseline_avg_views": content.baseline_avg_views,
            "baseline_engagement_rate": content.baseline_engagement_rate,
            "baseline_sample_size": content.baseline_sample_size,
            "performance_lift_percent": content.performance_lift_percent,
            "view_momentum": content.momentum,
            "cost_per_view_inr": content.cost_per_view,
            "cost_per_engagement_inr": content.cost_per_engagement,
            "cpm_inr": content.cpm,
            "actual_spend_inr": content.agreed_cost if content.agreed_cost is not None else campaign.spend,
            "attributed_revenue_inr": content.attributed_revenue if content.attributed_revenue is not None else campaign.revenue,
            "attributed_orders": content.attributed_orders,
            "average_order_value_inr": content.average_order_value,
            "gross_margin_percent": content.gross_margin_percent,
            "attributed_profit_inr": content.attributed_profit,
            "roas": content.roas if content.roas is not None else campaign.roas,
            "roi_percent": content.roi if content.roi is not None else campaign.roi,
            "attribution_source": content.attribution_source or "Unspecified",
            "is_demo_content": content.is_demo,
            "performance_status": content.performance_status,
        }

        hist_res = await db.execute(
            select(CampaignContent).where(
                CampaignContent.campaign_id == campaign.id,
                CampaignContent.attribution_source == "HISTORICAL_REPORTED_RESULTS",
                CampaignContent.id != content.id,
            )
        )
        historical_imported = [
            {
                "content_id": row.id,
                "views": row.current_views,
                "revenue": row.attributed_revenue,
                "agreed_cost": row.agreed_cost,
                "attribution_source": row.attribution_source,
                "metric_kind": "HISTORICAL_REPORTED",
            }
            for row in hist_res.scalars().all()
        ]

        return {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "campaign_objective": campaign.objective or "AWARENESS",
            "campaign_budget": campaign.budget,
            "campaign_spend": campaign.spend,
            "campaign_revenue": campaign.revenue,
            "campaign_reported_roas": campaign.roas,
            "campaign_reported_roi": campaign.roi,
            "strategy_summary": strategy_summary,
            "influencer_name": influencer.name if influencer else (content.channel_title or "Creator"),
            "influencer_username": influencer.username if influencer else "creator",
            "content_id": content.id,
            "content_title": content.title or content.external_content_id,
            "content_type": content.content_type,
            "content_url": content.content_url,
            "published_at": content.published_at.isoformat() if content.published_at else None,
            "content_age_hours": content.content_age_hours,
            "content_age_days": content.content_age_days,
            "content_stage": content.content_stage,
            "kpis": kpis,
            "historical_imported_performance": historical_imported,
            "snapshot_growth": snapshot_growth,
            "latest_snapshot_id": latest_snapshot.id if latest_snapshot else None,
        }

    def build_system_prompt(self, ctx: AgentContext) -> str:
        return (
            "You are the Performance Agent of Auralytics.\n\n"
            "Your responsibility is to explain how campaign content is performing based only on the factual "
            "information supplied by the backend.\n\n"
            "You MUST NOT invent or recalculate:\n"
            "- views\n"
            "- likes\n"
            "- comments\n"
            "- followers\n"
            "- revenue\n"
            "- orders\n"
            "- ROAS\n"
            "- ROI\n"
            "- conversions\n"
            "- demographics\n\n"
            "Always consider:\n"
            "- campaign objective (e.g. AWARENESS vs CONVERSIONS)\n"
            "- content age (hours/days)\n"
            "- current momentum (RISING, STABLE, SLOWING, INSUFFICIENT_DATA)\n"
            "- creator baseline (median views, historical engagement)\n"
            "- engagement rate\n"
            "- actual campaign spend\n"
            "- attributed revenue if provided\n"
            "- ROAS if provided\n"
            "- ROI only when provided (if profit/margin is not provided, ROI is not available)\n\n"
            "CRITICAL RULES:\n"
            "1. A new video (e.g. 0-24 hours old) must NOT be judged using the same expectations as mature content. "
            "Label it EARLY_STAGE and state that more time/data is required before final conclusions.\n"
            "2. When data is insufficient, explicitly state that more tracking time/data is required.\n"
            "3. If campaign objective is AWARENESS, prioritize reach, views, engagement, and CPV over sales attribution.\n"
            "4. If attributed revenue has not been recorded or is unprovided/null, you MUST explicitly state in the financial_interpretation: "
            "'Direct revenue attribution has not been recorded for this deliverable.' NEVER invent conversions, conversion rates, or sales.\n"
            "5. Use clear, simple language suitable for marketers.\n\n"
            "Return structured JSON matching the exact schema:\n"
            "{\n"
            '  "status": "STRONG" | "ON_TRACK" | "AVERAGE" | "NEEDS_ATTENTION" | "UNDERPERFORMING" | "EARLY_STAGE",\n'
            '  "content_stage": "EARLY_STAGE" | "INITIAL_MOMENTUM" | "SHORT_TERM" | "MATURE" | "LONG_TERM",\n'
            '  "summary": "...",\n'
            '  "what_is_working": ["...", "..."],\n'
            '  "needs_attention": ["...", "..."],\n'
            '  "financial_interpretation": "...",\n'
            '  "next_step": "...",\n'
            '  "confidence": 0.9\n'
            "}"
        )

    def build_user_prompt(self, ctx: AgentContext, context_payload: Dict[str, Any]) -> str:
        return (
            f"Analyze the campaign content performance for the following verified data:\n\n"
            f"{json.dumps(context_payload, indent=2)}\n\n"
            "Interpret what these factual numbers mean for the marketer. Do not recalculate or invent any numbers."
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
                response_model=PerformanceAgentOutput,
                temperature=0.1,
            )
        except Exception as exc:
            logger.error("Performance Agent LLM call failed: %s", exc)
            raise AgentValidationException(detail=f"Performance Agent AI analysis failed: {exc}")

        return AgentResultEnvelope(
            status=output.status,
            summary=output.summary,
            confidence=output.confidence,
            recommendations=[{"action": output.next_step}] if output.next_step else [],
            requires_approval=False,
            data=output.model_dump(),
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
        data = result.data or {}
        # Ensure status is valid
        if data.get("status") not in PerformanceStatus.ALL:
            data["status"] = context_payload["kpis"].get("performance_status") or PerformanceStatus.ON_TRACK
        result.status = data["status"]

        # Ensure explicit unrecorded attribution statement if revenue is missing
        attr_rev = context_payload.get("kpis", {}).get("attributed_revenue_inr")
        if attr_rev is None or attr_rev < 0:
            fin_text = data.get("financial_interpretation", "")
            required_phrase = "Direct revenue attribution has not been recorded for this deliverable."
            if required_phrase.lower() not in fin_text.lower():
                if fin_text:
                    data["financial_interpretation"] = f"{required_phrase} {fin_text}"
                else:
                    data["financial_interpretation"] = required_phrase
                result.data = data

        return result
