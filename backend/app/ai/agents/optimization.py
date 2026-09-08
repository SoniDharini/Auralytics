"""Optimization Agent — Produces maximum 3 evidence-based next actions connected to Approval Center."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload

from app.ai.agents.base import AgentContext, BaseAgent
from app.ai.schemas import AgentResultEnvelope
from app.ai.workflow_states import AgentNames
from app.core.exceptions import AgentValidationException, NotFoundException
from app.models.approval import Approval
from app.models.campaign_content import (
    CampaignContent,
    OptimizationPlan,
    PerformanceAnalysis,
)

logger = logging.getLogger(__name__)


class OptimizationRecommendationItem(BaseModel):
    priority: str = Field(..., description="HIGH, MEDIUM, LOW")
    category: str = Field(..., description="MONITOR, CREATOR, CONTENT, FORMAT, CTA, TIMING, BUDGET")
    action: str = Field(..., description="Specific recommended next step")
    reason: str = Field(..., description="Why this action is recommended")
    evidence: List[str] = Field(default_factory=list, description="Factual metrics or observations supporting this recommendation")
    requires_human_approval: bool = Field(True, description="Always true - requires marketer approval before action")


class OptimizationAgentOutput(BaseModel):
    recommendations: List[OptimizationRecommendationItem] = Field(
        ...,
        max_length=3,
        description="At most 3 actionable, evidence-based recommendations.",
    )


class OptimizationAgent(BaseAgent):
    name = AgentNames.OPTIMIZATION
    version = "1.0.0"
    description = "Recommends maximum 3 evidence-based campaign optimization actions."

    async def build_context(self, ctx: AgentContext) -> Dict[str, Any]:
        campaign = ctx.campaign
        db = ctx.db
        content_id = ctx.extras.get("content_id") or ctx.extras.get("campaign_content_id")

        # 1. Fetch latest Performance Analysis
        p_stmt = (
            select(PerformanceAnalysis)
            .where(PerformanceAnalysis.campaign_id == campaign.id)
        )
        if content_id:
            p_stmt = p_stmt.where(PerformanceAnalysis.campaign_content_id == content_id)
        p_stmt = p_stmt.order_by(PerformanceAnalysis.created_at.desc()).limit(1)

        p_res = await db.execute(p_stmt)
        perf_analysis = p_res.scalar_one_or_none()

        if not perf_analysis:
            raise NotFoundException(
                detail="Performance Agent analysis must be completed before running the Optimization Agent."
            )

        # 2. Fetch tracked content
        c_stmt = (
            select(CampaignContent)
            .options(selectinload(CampaignContent.influencer))
            .where(CampaignContent.id == perf_analysis.campaign_content_id)
        )
        c_res = await db.execute(c_stmt)
        content = c_res.scalar_one_or_none()

        spent = float(campaign.spend or 0.0)
        budget = float(campaign.budget or 0.0)
        remaining_budget = max(0.0, budget - spent) if budget > 0 else None

        perf_summary = {
            "status": perf_analysis.status,
            "content_stage": perf_analysis.content_stage,
            "summary": perf_analysis.summary,
            "what_is_working": perf_analysis.what_is_working,
            "needs_attention": perf_analysis.needs_attention,
            "financial_interpretation": perf_analysis.financial_interpretation,
            "next_step": perf_analysis.next_step,
            "confidence": perf_analysis.confidence,
        }

        return {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "campaign_objective": campaign.objective or "AWARENESS",
            "campaign_budget_inr": budget,
            "actual_spend_inr": spent,
            "remaining_budget_inr": remaining_budget,
            "start_date": campaign.start_date,
            "end_date": campaign.end_date,
            "performance_analysis_id": perf_analysis.id,
            "performance_analysis": perf_summary,
            "content_id": content.id if content else None,
            "creator_name": content.influencer.name if content and content.influencer else (content.channel_title if content else "Creator"),
            "content_type": content.content_type if content else "YOUTUBE_VIDEO",
            "content_age_hours": content.content_age_hours if content else None,
            "content_stage": content.content_stage if content else "MATURE",
            "momentum": content.momentum if content else "INSUFFICIENT_DATA",
            "kpis": perf_analysis.raw_kpis or {},
        }

    def build_system_prompt(self, ctx: AgentContext) -> str:
        return (
            "You are the Optimization Agent of Auralytics.\n\n"
            "You receive a validated campaign Performance analysis and factual backend KPIs.\n"
            "Recommend NO MORE THAN 3 useful, high-impact next actions for the marketer.\n"
            "Every recommendation must be directly supported by supplied factual evidence.\n\n"
            "Possible categories:\n"
            "- MONITOR: Content is too new or trending normally; continue tracking.\n"
            "- CREATOR: Commission further content from high-performing creator or pause engagement.\n"
            "- CONTENT: Creative, messaging, or hook refinement based on engagement.\n"
            "- FORMAT: Shifts between Shorts and long-form based on CPV and lift.\n"
            "- CTA: Call-to-action or link placement adjustment based on conversion rate.\n"
            "- TIMING: Publishing time or cadence recommendations.\n"
            "- BUDGET: Scaling budget on positive ROAS or protecting spend on lagging content.\n\n"
            "CRITICAL RULES:\n"
            "1. MAXIMUM 3 recommendations. Never produce more than 3.\n"
            "2. Do NOT recommend drastic budget or creator cuts when content is in EARLY_STAGE (<= 24h) or INITIAL_MOMENTUM.\n"
            "3. Do not invent metrics or outcomes.\n"
            "4. Do NOT automatically execute any recommendation. Each must have requires_human_approval = true.\n"
            "5. Always align with the campaign objective (e.g. AWARENESS -> focus on reach/momentum/CPV; CONVERSIONS -> focus on ROAS/orders).\n\n"
            "Return structured JSON matching the exact schema:\n"
            "{\n"
            '  "recommendations": [\n'
            "    {\n"
            '      "priority": "HIGH" | "MEDIUM" | "LOW",\n'
            '      "category": "MONITOR" | "CREATOR" | "CONTENT" | "FORMAT" | "CTA" | "TIMING" | "BUDGET",\n'
            '      "action": "...",\n'
            '      "reason": "...",\n'
            '      "evidence": ["...", "..."],\n'
            '      "requires_human_approval": true\n'
            "    }\n"
            "  ]\n"
            "}"
        )

    def build_user_prompt(self, ctx: AgentContext, context_payload: Dict[str, Any]) -> str:
        return (
            f"Based on the following validated Performance Agent findings and campaign context:\n\n"
            f"{json.dumps(context_payload, indent=2)}\n\n"
            "Generate at most 3 evidence-based optimization recommendations. Return strictly valid JSON."
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
            raise AgentValidationException(detail=f"Optimization Agent AI analysis failed: {exc}")

        # Enforce maximum 3 recommendations
        recs = output.recommendations[:3]
        action_summaries = [f"[{r.priority}] {r.action}" for r in recs]

        return AgentResultEnvelope(
            status="SUCCESS",
            summary=f"Generated {len(recs)} optimization recommendation(s).",
            confidence=0.92,
            recommendations=[r.model_dump() for r in recs],
            requires_approval=True,
            data={"recommendations": [r.model_dump() for r in recs]},
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
        recs = data.get("recommendations", [])
        # Strict cap of 3
        if len(recs) > 3:
            data["recommendations"] = recs[:3]
            result.data = data
        return result
