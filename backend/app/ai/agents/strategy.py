"""Strategy Agent — transforms campaign brief into execution strategy (no creator selection)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.ai.agents.base import SECURITY_RULE, MISSING_DATA_RULE, AgentContext, BaseAgent
from app.ai.schemas import AgentResultEnvelope
from app.ai.workflow_states import AgentNames
from app.core.exceptions import AgentValidationException

logger = logging.getLogger(__name__)

_INFLUENCER_HANDLE_RE = re.compile(r"@\w{2,}")


class PlatformStrategyItem(BaseModel):
    platform: str
    priority: str = Field(default="MEDIUM", description="HIGH | MEDIUM | LOW")
    reason: str = ""
    suggested_budget_percentage: Optional[float] = Field(default=None, ge=0, le=100)


class CreatorTierPreference(BaseModel):
    tier: str
    priority: str = "MEDIUM"
    reason: str = ""


class CreatorStrategy(BaseModel):
    preferred_niches: List[str] = Field(default_factory=list)
    preferred_creator_tiers: List[CreatorTierPreference] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    desired_creator_characteristics: List[str] = Field(default_factory=list)


class ContentStrategyItem(BaseModel):
    content_type: str
    purpose: str = ""
    priority: str = "MEDIUM"


class BudgetStrategy(BaseModel):
    creator_budget_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    content_amplification_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    reserve_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    reasoning: str = ""


class KpiStrategyItem(BaseModel):
    kpi: str
    importance: str = "MEDIUM"
    reason: str = ""


class CampaignPhaseItem(BaseModel):
    phase: str
    objective: str = ""
    recommended_creator_type: str = ""


class DiscoveryPriorityItem(BaseModel):
    factor: str
    priority: int = Field(ge=1, le=20)
    reason: str = ""


class RiskItem(BaseModel):
    risk: str
    severity: str = "MEDIUM"
    mitigation: str = ""


class StrategyAgentOutput(BaseModel):
    campaign_summary: str
    strategy_objective: str = ""
    platform_strategy: List[PlatformStrategyItem] = Field(default_factory=list)
    creator_strategy: CreatorStrategy = Field(default_factory=CreatorStrategy)
    content_strategy: List[ContentStrategyItem] = Field(default_factory=list)
    budget_strategy: BudgetStrategy = Field(default_factory=BudgetStrategy)
    kpi_strategy: List[KpiStrategyItem] = Field(default_factory=list)
    campaign_phases: List[CampaignPhaseItem] = Field(default_factory=list)
    discovery_priorities: List[DiscoveryPriorityItem] = Field(default_factory=list)
    risks: List[RiskItem] = Field(default_factory=list)
    strategy_reasoning: str = ""
    confidence: float = Field(ge=0, le=1)

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v: Any) -> float:
        try:
            value = float(v)
        except (TypeError, ValueError) as exc:
            raise ValueError("confidence must be numeric") from exc
        if value > 1 and value <= 100:
            value = value / 100.0
        return max(0.0, min(1.0, value))

    def to_persisted_dict(self) -> Dict[str, Any]:
        """Persist canonical schema plus legacy mirrors for existing UI consumers."""
        data = self.model_dump()
        data["recommended_platform_mix"] = [
            {
                "platform": item.platform,
                "percentage": item.suggested_budget_percentage or 0,
                "rationale": item.reason,
            }
            for item in self.platform_strategy
        ]
        data["creator_tier_strategy"] = [
            {
                "tier": item.tier,
                "count_suggestion": None,
                "budget_share_pct": None,
                "rationale": item.reason,
            }
            for item in self.creator_strategy.preferred_creator_tiers
        ]
        data["content_strategy_legacy"] = data["content_strategy"]
        data["content_strategy"] = [
            f"{item.content_type} — {item.purpose} ({item.priority})".strip(" — ()")
            for item in self.content_strategy
        ]
        data["budget_distribution"] = [
            {
                "category": "creator fees",
                "amount": None,
                "percentage": self.budget_strategy.creator_budget_percentage,
                "rationale": self.budget_strategy.reasoning,
            },
            {
                "category": "content amplification",
                "amount": None,
                "percentage": self.budget_strategy.content_amplification_percentage,
                "rationale": self.budget_strategy.reasoning,
            },
            {
                "category": "reserve",
                "amount": None,
                "percentage": self.budget_strategy.reserve_percentage,
                "rationale": self.budget_strategy.reasoning,
            },
        ]
        data["recommended_kpis"] = [item.kpi for item in self.kpi_strategy]
        data["reasoning"] = self.strategy_reasoning
        data["risks_legacy"] = data["risks"]
        data["risks"] = [
            f"{item.risk} ({item.severity}) — {item.mitigation}".strip(" — ")
            for item in self.risks
        ]
        return data


class StrategyAgent(BaseAgent):
    name = AgentNames.STRATEGY
    version = "1.1.0"
    description = (
        "Transforms a campaign brief into a structured influencer-marketing plan. "
        "Does not select individual creators."
    )

    async def build_context(self, ctx: AgentContext) -> Dict[str, Any]:
        c = ctx.campaign
        return {
            "campaign_id": c.id,
            "campaign_name": c.name,
            "brand_name": c.brand,
            "product_name": c.name,
            "product_description": c.description or None,
            "campaign_objective": c.objective,
            "budget": c.budget,
            "currency": None,
            "target_audience": {
                "locations": c.target_locations or None,
                "age_min": c.target_age_min,
                "age_max": c.target_age_max,
                "gender": c.target_gender or None,
                "interests": c.interests or [],
                "languages": c.languages or [],
            },
            "selected_platforms": c.platforms or [],
            "start_date": c.start_date,
            "end_date": c.end_date,
            "primary_kpi": c.primary_kpi or None,
            "secondary_kpis": {
                "target_roas": c.target_roas,
                "target_cpa": c.target_cpa,
            },
            "creator_preferences": {
                "creator_tiers": c.creator_tiers or [],
                "min_followers": c.min_followers,
                "max_followers": c.max_followers,
            },
            "content_preferences": c.campaign_types or [],
            "campaign_constraints": {
                "keywords": c.keywords or [],
                "budget_allocation": c.budget_allocation or [],
            },
            "note": (
                "Use null for unavailable fields. Never invent influencers, usernames, "
                "emails, or performance metrics."
            ),
        }

    def build_system_prompt(self, ctx: AgentContext) -> str:
        return "\n".join(
            [
                "You are the Strategy Agent of Auralytics.",
                "Transform a campaign brief into a practical influencer-marketing strategy.",
                "You are NOT responsible for selecting individual influencers, usernames, or handles.",
                "Your job is to determine what the Discovery Agent should look for.",
                "Analyze ONLY the campaign data provided by Auralytics.",
                "Determine:",
                "1. Campaign positioning (strategy_objective)",
                "2. Platform strategy",
                "3. Creator profile requirements (creator_strategy)",
                "4. Creator tier distribution",
                "5. Content strategy",
                "6. Budget strategy (percentages only — must not exceed 100% combined)",
                "7. KPI strategy",
                "8. Campaign phases",
                "9. Selection priorities for Discovery Agent (discovery_priorities — required)",
                "10. Campaign risks",
                "Never invent campaign facts. Never invent influencers. Never exceed provided budget.",
                "If important information is missing, note it in strategy_reasoning.",
                "Return ONLY valid JSON matching StrategyAgentOutput.",
                MISSING_DATA_RULE,
                SECURITY_RULE,
            ]
        )

    def build_user_prompt(self, ctx: AgentContext, context_payload: Dict[str, Any]) -> str:
        return (
            "Create an influencer-marketing execution strategy from this campaign brief. "
            "Do NOT name specific influencers.\n"
            f"{json.dumps(context_payload, default=str)}"
        )

    async def call_llm(
        self,
        ctx: AgentContext,
        system_prompt: str,
        user_prompt: str,
        context_payload: Dict[str, Any],
    ) -> AgentResultEnvelope:
        structured, raw = await self.llm.generate_structured_with_meta(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=StrategyAgentOutput,
            temperature=0.2,
            max_tokens=4096,
        )
        persisted = structured.to_persisted_dict()
        return AgentResultEnvelope(
            status="COMPLETED",
            summary=structured.campaign_summary,
            confidence=structured.confidence,
            recommendations=[],
            requires_approval=False,
            data=persisted,
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
        self._reject_influencer_selection(data)
        if not data.get("discovery_priorities"):
            raise AgentValidationException(
                detail="Strategy must include discovery_priorities for Discovery Agent guidance"
            )
        if not data.get("creator_strategy"):
            raise AgentValidationException(
                detail="Strategy must include creator_strategy for Discovery Agent guidance"
            )
        budget = data.get("budget_strategy") or {}
        pct_total = sum(
            float(budget.get(key) or 0)
            for key in (
                "creator_budget_percentage",
                "content_amplification_percentage",
                "reserve_percentage",
            )
        )
        if pct_total > 100.01:
            raise AgentValidationException(
                detail=f"Budget strategy percentages sum to {pct_total:.1f}%, exceeding 100%"
            )
        if result.confidence is None:
            result.confidence = float(data.get("confidence") or 0)
        return result

    @staticmethod
    def _reject_influencer_selection(data: Dict[str, Any]) -> None:
        blob = json.dumps(data, default=str).lower()
        if _INFLUENCER_HANDLE_RE.search(blob):
            raise AgentValidationException(
                detail="Strategy Agent must not select or name individual influencers (@handles)"
            )
        for forbidden in ("influencer_id", "recommended_influencers", "username"):
            if forbidden in blob and "desired_creator_characteristics" not in blob:
                # Allow the word username only in unrelated contexts — check structured keys
                if data.get("recommended_influencers"):
                    raise AgentValidationException(
                        detail="Strategy Agent must not recommend specific influencers"
                    )
