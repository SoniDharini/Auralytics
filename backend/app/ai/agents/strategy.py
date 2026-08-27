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


class SubscriberRange(BaseModel):
    minimum: Optional[int] = Field(default=None, ge=0)
    maximum: Optional[int] = Field(default=None, ge=0)


class CreatorCountRange(BaseModel):
    minimum: Optional[int] = Field(default=None, ge=0)
    maximum: Optional[int] = Field(default=None, ge=0)


class CreatorStrategy(BaseModel):
    preferred_niches: List[str] = Field(default_factory=list)
    preferred_creator_tiers: List[CreatorTierPreference] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    desired_creator_characteristics: List[str] = Field(default_factory=list)
    recommended_subscriber_range: SubscriberRange = Field(default_factory=SubscriberRange)
    recommended_creator_count: CreatorCountRange = Field(default_factory=CreatorCountRange)


class ContentStrategyItem(BaseModel):
    content_type: str
    purpose: str = ""
    priority: str = "MEDIUM"


class BudgetAllocationSlice(BaseModel):
    amount: Optional[float] = Field(default=None, ge=0)
    percentage: Optional[float] = Field(default=None, ge=0, le=100)


class BudgetStrategy(BaseModel):
    total_budget: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = None
    creator_budget_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    content_amplification_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    reserve_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    creator_allocation: Optional[BudgetAllocationSlice] = None
    amplification_allocation: Optional[BudgetAllocationSlice] = None
    reserve: Optional[BudgetAllocationSlice] = None
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


class DiscoveryRequirements(BaseModel):
    niche_priority: str = ""
    location_priority: str = ""
    engagement_priority: str = ""
    creator_tier_priority: str = ""
    content_priority: str = ""


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
    discovery_requirements: DiscoveryRequirements = Field(default_factory=DiscoveryRequirements)
    risks: List[RiskItem] = Field(default_factory=list)
    tradeoffs: List[str] = Field(default_factory=list)
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
        bs = self.budget_strategy
        total = bs.total_budget
        creator_pct = bs.creator_budget_percentage
        amp_pct = bs.content_amplification_percentage
        reserve_pct = bs.reserve_percentage
        if bs.creator_allocation and bs.creator_allocation.percentage is not None:
            creator_pct = bs.creator_allocation.percentage
        if bs.amplification_allocation and bs.amplification_allocation.percentage is not None:
            amp_pct = bs.amplification_allocation.percentage
        if bs.reserve and bs.reserve.percentage is not None:
            reserve_pct = bs.reserve.percentage

        def _amount(pct: Optional[float], explicit: Optional[float]) -> Optional[float]:
            if explicit is not None:
                return explicit
            if total is not None and pct is not None:
                return round(float(total) * float(pct) / 100.0, 2)
            return None

        creator_amt = _amount(
            creator_pct,
            bs.creator_allocation.amount if bs.creator_allocation else None,
        )
        amp_amt = _amount(
            amp_pct,
            bs.amplification_allocation.amount if bs.amplification_allocation else None,
        )
        reserve_amt = _amount(reserve_pct, bs.reserve.amount if bs.reserve else None)

        data["budget_strategy"] = {
            **bs.model_dump(),
            "creator_budget_percentage": creator_pct,
            "content_amplification_percentage": amp_pct,
            "reserve_percentage": reserve_pct,
            "creator_allocation": {"amount": creator_amt, "percentage": creator_pct},
            "amplification_allocation": {"amount": amp_amt, "percentage": amp_pct},
            "reserve": {"amount": reserve_amt, "percentage": reserve_pct},
        }
        data["budget_distribution"] = [
            {
                "category": "creator fees",
                "amount": creator_amt,
                "percentage": creator_pct,
                "rationale": bs.reasoning,
            },
            {
                "category": "content amplification",
                "amount": amp_amt,
                "percentage": amp_pct,
                "rationale": bs.reasoning,
            },
            {
                "category": "reserve",
                "amount": reserve_amt,
                "percentage": reserve_pct,
                "rationale": bs.reasoning,
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
        budget = float(c.budget or 0)
        return {
            "campaign_id": c.id,
            "campaign_name": c.name,
            "brand_name": c.brand,
            "product_name": c.name,
            "product_description": c.description or "NOT_AVAILABLE",
            "campaign_objective": c.objective,
            "budget": budget if budget > 0 else None,
            "budget_status": "AVAILABLE" if budget > 0 else "REQUIRES_USER_INPUT",
            "currency": "INR",
            "target_audience": {
                "locations": c.target_locations or "NOT_AVAILABLE",
                "age_min": c.target_age_min,
                "age_max": c.target_age_max,
                "gender": c.target_gender or "NOT_AVAILABLE",
                "interests": c.interests or [],
                "languages": c.languages or [],
            },
            "selected_platforms": c.platforms or [],
            "start_date": c.start_date,
            "end_date": c.end_date,
            "primary_kpi": c.primary_kpi or "NOT_AVAILABLE",
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
            "creator_tier_reference": {
                "nano": "1K–10K",
                "micro": "10K–100K",
                "mid_tier": "100K–500K",
                "macro": "500K–1M",
                "mega": "1M+",
            },
            "note": (
                "Use ONLY supplied campaign facts. Never invent budget, audience, geography, "
                "creator prices, influencers, emails, or performance metrics. "
                "If budget_status is REQUIRES_USER_INPUT, do not invent a budget."
            ),
        }

    def validate_input(self, ctx: AgentContext) -> None:
        super().validate_input(ctx)
        budget = float(ctx.campaign.budget or 0)
        if budget <= 0:
            raise AgentValidationException(
                detail=(
                    "REQUIRES_USER_INPUT: Campaign budget is required before budget "
                    "allocation can be generated."
                )
            )

    def build_system_prompt(self, ctx: AgentContext) -> str:
        return "\n".join(
            [
                "You are the Strategy Agent of Auralytics.",
                "Transform the supplied company campaign requirements into a realistic,",
                "budget-aware influencer marketing strategy.",
                "You are NOT responsible for selecting individual influencers, usernames, or handles.",
                "Your output directly guides the Discovery Agent.",
                "Use ONLY the campaign facts provided. Do NOT invent budget, audience, geography,",
                "creator pricing, platform metrics, or influencer identities.",
                "Create:",
                "1. Campaign strategy / positioning (strategy_objective)",
                "2. Platform strategy",
                "3. Creator-tier strategy with recommended_subscriber_range derived from tiers + budget",
                "4. Recommended creator count range where reasonable (or null if unknown)",
                "5. Content strategy",
                "6. KPI priorities",
                "7. Budget allocation — percentages MUST sum to ≤ 100% and amounts MUST NOT exceed total_budget",
                "8. Discovery requirements and discovery_priorities",
                "9. Risks and tradeoffs",
                "Budget rules:",
                "- Set budget_strategy.total_budget to the supplied campaign budget.",
                "- currency = INR unless otherwise supplied.",
                "- Prefer nano/micro tiers for limited budgets; allow mid/macro only when budget supports scale.",
                "- Never recommend celebrity-heavy mixes for small budgets.",
                "- Never fabricate creator fees from follower counts.",
                "If important information is missing, note it in strategy_reasoning using NOT_AVAILABLE / INSUFFICIENT_DATA.",
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
        # Authoritative budget comes from PostgreSQL campaign, never from LLM invention.
        campaign_budget = float(ctx.campaign.budget or 0)
        if campaign_budget > 0:
            structured.budget_strategy.total_budget = campaign_budget
            structured.budget_strategy.currency = structured.budget_strategy.currency or "INR"
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
        creator_pct = budget.get("creator_budget_percentage")
        amp_pct = budget.get("content_amplification_percentage")
        reserve_pct = budget.get("reserve_percentage")
        if isinstance(budget.get("creator_allocation"), dict):
            creator_pct = budget["creator_allocation"].get("percentage", creator_pct)
        if isinstance(budget.get("amplification_allocation"), dict):
            amp_pct = budget["amplification_allocation"].get("percentage", amp_pct)
        if isinstance(budget.get("reserve"), dict):
            reserve_pct = budget["reserve"].get("percentage", reserve_pct)

        pct_total = sum(float(v or 0) for v in (creator_pct, amp_pct, reserve_pct))
        if pct_total > 100.01:
            raise AgentValidationException(
                detail=f"Budget strategy percentages sum to {pct_total:.1f}%, exceeding 100%"
            )

        campaign_budget = float(ctx.campaign.budget or 0)
        alloc_sum = 0.0
        for key in ("creator_allocation", "amplification_allocation", "reserve"):
            slice_ = budget.get(key)
            if isinstance(slice_, dict) and slice_.get("amount") is not None:
                try:
                    alloc_sum += float(slice_["amount"])
                except (TypeError, ValueError) as exc:
                    raise AgentValidationException(
                        detail=f"Invalid monetary amount in budget_strategy.{key}"
                    ) from exc
        if alloc_sum <= 0 and data.get("budget_distribution"):
            alloc_sum = sum(
                float(r.get("amount") or 0)
                for r in data["budget_distribution"]
                if isinstance(r, dict)
            )
        if campaign_budget > 0 and alloc_sum > campaign_budget + 0.01:
            raise AgentValidationException(
                detail=(
                    f"Budget allocation ₹{alloc_sum:,.0f} exceeds campaign budget "
                    f"₹{campaign_budget:,.0f}"
                )
            )

        if isinstance(budget, dict) and campaign_budget > 0:
            budget["total_budget"] = campaign_budget
            budget.setdefault("currency", "INR")
            data["budget_strategy"] = budget
            result.data = data

        creator = data.get("creator_strategy") or {}
        rng = creator.get("recommended_subscriber_range") or {}
        if not rng.get("minimum") and not rng.get("maximum"):
            from app.ai.creator_tiers import range_for_tiers

            tiers = []
            for item in creator.get("preferred_creator_tiers") or []:
                if isinstance(item, dict) and item.get("tier"):
                    tiers.append(str(item["tier"]))
                elif isinstance(item, str):
                    tiers.append(item)
            mn, mx = range_for_tiers(tiers)
            if mn is not None or mx is not None:
                creator["recommended_subscriber_range"] = {
                    "minimum": mn,
                    "maximum": mx,
                }
                data["creator_strategy"] = creator
                result.data = data

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
