"""Strategy Agent — transforms campaign brief into execution strategy (no creator selection)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.ai.agents.base import SECURITY_RULE, MISSING_DATA_RULE, AgentContext, BaseAgent
from app.ai.creator_tiers import (
    canonical_tier_family,
    range_for_tiers,
    selected_tier_families,
    selected_tier_keys,
    subscriber_ranges_for_tiers,
)
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
    source: str = "AI_RECOMMENDATION"


class OptionalRecommendation(BaseModel):
    type: str = "ADD_CREATOR_TIER"
    tier: str = ""
    reason: str = ""
    requires_user_approval: bool = True


class TierBudgetAllocation(BaseModel):
    tier: str
    percentage: float = Field(default=0, ge=0, le=100)
    amount: Optional[float] = Field(default=None, ge=0)
    source: str = "USER_SELECTED"


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
    tier_allocations: List[TierBudgetAllocation] = Field(default_factory=list)
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
    model_config = ConfigDict(extra="ignore")

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
    user_selected_creator_tiers: List[str] = Field(default_factory=list)
    optional_recommendations: List[OptionalRecommendation] = Field(default_factory=list)
    budget_limitations: List[str] = Field(default_factory=list)
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
                "priority": item.priority,
                "source": item.source,
            }
            for item in self.creator_strategy.preferred_creator_tiers
        ]
        data["recommended_creator_strategy"] = [
            {
                "tier": item.tier,
                "priority": item.priority,
                "source": item.source,
            }
            for item in self.creator_strategy.preferred_creator_tiers
        ]
        data["user_selected_creator_tiers"] = list(self.user_selected_creator_tiers)
        data["optional_recommendations"] = [
            item.model_dump() for item in self.optional_recommendations
        ]
        data["budget_limitations"] = list(self.budget_limitations)
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
    version = "1.2.0"
    description = (
        "Transforms a campaign brief into a structured influencer-marketing plan. "
        "Does not select individual creators."
    )

    async def build_context(self, ctx: AgentContext) -> Dict[str, Any]:
        c = ctx.campaign
        budget = float(c.budget or 0)
        selected_tiers = selected_tier_keys(getattr(c, "creator_tiers", None) or [])
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
            "platforms": c.platforms or [],
            "start_date": c.start_date,
            "end_date": c.end_date,
            "timeline": {"start_date": c.start_date, "end_date": c.end_date},
            "primary_kpi": c.primary_kpi or "NOT_AVAILABLE",
            "secondary_kpis": {
                "target_roas": c.target_roas,
                "target_cpa": c.target_cpa,
            },
            "selected_influencer_types": selected_tiers,
            "user_requirements": {
                "source": "USER_REQUIREMENT",
                "selected_influencer_types": selected_tiers,
                "mandatory": True,
                "subscriber_ranges": subscriber_ranges_for_tiers(selected_tiers),
            },
            "creator_preferences": {
                "creator_tiers": selected_tiers or (c.creator_tiers or []),
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
                "celebrity": "1M+",
            },
            "note": (
                "USER_REQUIREMENT selected_influencer_types are mandatory. "
                "Never silently replace them with another tier. "
                "If budget conflicts with the selected tiers, explain the constraint "
                "and put any other tier in optional_recommendations with requires_user_approval=true. "
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
        selected = selected_tier_keys(getattr(ctx.campaign, "creator_tiers", None) or [])
        selected_clause = (
            f"USER_REQUIREMENT selected_influencer_types={selected}. These tiers are mandatory. "
            "Build the creator-tier strategy and budget pools using ONLY these tiers. "
            "If you believe another tier would help, put it in optional_recommendations "
            "with requires_user_approval=true. Do not merge it into the mandatory strategy."
            if selected
            else (
                "The user did not select creator tiers. You may recommend tiers and must "
                "label them source=AI_RECOMMENDATION."
            )
        )
        return "\n".join(
            [
                "You are the Strategy Agent of Auralytics.",
                "Create a campaign-specific influencer marketing strategy from the actual",
                "company requirements supplied in the user message.",
                "You are NOT responsible for selecting individual influencers, usernames, or handles.",
                "Your output directly guides the Discovery Agent.",
                selected_clause,
                "NEVER silently replace a selected tier with another tier.",
                "If the user selects MACRO, preserve MACRO.",
                "If the user selects CELEBRITY, preserve CELEBRITY.",
                "If multiple tiers are selected, build a strategy using those selected tiers.",
                "If the campaign budget creates a constraint, explain it in budget_limitations",
                "and provide an OPTIONAL alternative. Do not change the user's requirement automatically.",
                "Clearly differentiate USER_REQUIREMENT from AI_RECOMMENDATION using the source field.",
                "Create:",
                "1. Campaign positioning (strategy_objective)",
                "2. Platform strategy",
                "3. Creator-tier strategy with recommended_subscriber_range from USER-SELECTED tiers",
                "4. Budget allocation — percentages MUST sum to ≤ 100% and amounts MUST NOT exceed total_budget",
                "5. tier_allocations budget pools for each USER-SELECTED tier (not fabricated creator prices)",
                "6. Content strategy",
                "7. KPI priorities",
                "8. Discovery requirements and discovery_priorities",
                "9. Budget limitations",
                "10. Optional alternatives in optional_recommendations",
                "Budget rules:",
                "- Set budget_strategy.total_budget to the supplied campaign budget.",
                "- currency = INR unless otherwise supplied.",
                "- Allocate BUDGET POOLS by selected tier. Never invent individual creator rates.",
                "- Do not allocate the primary creator budget to a tier the user did not select.",
                "- Never fabricate creator fees from follower counts.",
                "If important information is missing, note it in strategy_reasoning using NOT_AVAILABLE / INSUFFICIENT_DATA.",
                "Return ONLY valid JSON matching StrategyAgentOutput.",
                MISSING_DATA_RULE,
                SECURITY_RULE,
            ]
        )

    def build_user_prompt(self, ctx: AgentContext, context_payload: Dict[str, Any]) -> str:
        selected = context_payload.get("selected_influencer_types") or []
        return (
            "Create an influencer-marketing execution strategy from this campaign brief. "
            "Do NOT name specific influencers. "
            f"Preserve USER_REQUIREMENT selected_influencer_types={selected}.\n"
            f"{json.dumps(context_payload, default=str, separators=(',', ':'))}"
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
        structured = self._apply_user_tier_constraints_model(ctx, structured)
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
        data = self._apply_user_tier_constraints_dict(ctx, data)
        result.data = data
        self._reject_influencer_selection(data)
        if not data.get("discovery_priorities"):
            raise AgentValidationException(
                detail="Strategy must include discovery_priorities for Discovery Agent guidance"
            )
        if not data.get("creator_strategy"):
            raise AgentValidationException(
                detail="Strategy must include creator_strategy for Discovery Agent guidance"
            )

        selected = selected_tier_keys(getattr(ctx.campaign, "creator_tiers", None) or [])
        if selected:
            creator = data.get("creator_strategy") or {}
            preferred = creator.get("preferred_creator_tiers") or []
            preferred_families = {
                canonical_tier_family(
                    str(item.get("tier") if isinstance(item, dict) else item or "")
                )
                for item in preferred
            }
            missing = [
                t for t in selected if canonical_tier_family(t) not in preferred_families
            ]
            if missing:
                raise AgentValidationException(
                    detail=(
                        "Strategy dropped user-selected creator tiers "
                        f"{missing}; refusing to persist an incorrect strategy."
                    )
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
        selected = selected_tier_keys(getattr(ctx.campaign, "creator_tiers", None) or [])
        if selected:
            mn, mx = range_for_tiers(selected)
            creator["recommended_subscriber_range"] = {"minimum": mn, "maximum": mx}
            data["creator_strategy"] = creator
            result.data = data
        elif not rng.get("minimum") and not rng.get("maximum"):
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

    @staticmethod
    def _campaign_selected_tiers(ctx: AgentContext) -> List[str]:
        return selected_tier_keys(getattr(ctx.campaign, "creator_tiers", None) or [])

    def _apply_user_tier_constraints_model(
        self, ctx: AgentContext, structured: StrategyAgentOutput
    ) -> StrategyAgentOutput:
        data = self._apply_user_tier_constraints_dict(ctx, structured.model_dump())
        return StrategyAgentOutput.model_validate({**structured.model_dump(), **data})

    def _apply_user_tier_constraints_dict(
        self, ctx: AgentContext, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        selected = self._campaign_selected_tiers(ctx)
        data["user_selected_creator_tiers"] = selected
        campaign_budget = float(getattr(ctx.campaign, "budget", 0) or 0)
        creator = data.get("creator_strategy") if isinstance(data.get("creator_strategy"), dict) else {}
        preferred_raw = list(creator.get("preferred_creator_tiers") or [])
        optional = [
            item
            for item in (data.get("optional_recommendations") or [])
            if isinstance(item, dict)
        ]

        if selected:
            selected_families = selected_tier_families(selected)
            grok_by_family: Dict[str, Dict[str, Any]] = {}
            for item in preferred_raw:
                if isinstance(item, str):
                    item = {"tier": item, "priority": "HIGH", "reason": "", "source": "AI_RECOMMENDATION"}
                if not isinstance(item, dict) or not item.get("tier"):
                    continue
                family = canonical_tier_family(str(item["tier"]))
                grok_by_family.setdefault(family, item)
                if family not in selected_families:
                    optional.append(
                        {
                            "type": "ADD_CREATOR_TIER",
                            "tier": item.get("tier"),
                            "reason": item.get("reason")
                            or "AI suggested this tier in addition to the user-selected tiers.",
                            "requires_user_approval": True,
                        }
                    )

            rebuilt: List[Dict[str, Any]] = []
            for tier in selected:
                existing = grok_by_family.get(canonical_tier_family(tier)) or {}
                rebuilt.append(
                    {
                        "tier": tier,
                        "priority": "HIGH",
                        "reason": existing.get("reason")
                        or f"{tier} was explicitly selected by the user.",
                        "source": "USER_SELECTED",
                    }
                )
            creator["preferred_creator_tiers"] = rebuilt
            mn, mx = range_for_tiers(selected)
            creator["recommended_subscriber_range"] = {"minimum": mn, "maximum": mx}
            data["creator_strategy"] = creator
            data["recommended_creator_strategy"] = [
                {"tier": item["tier"], "priority": item["priority"], "source": item["source"]}
                for item in rebuilt
            ]
            data["creator_tier_strategy"] = [
                {
                    "tier": item["tier"],
                    "count_suggestion": None,
                    "budget_share_pct": None,
                    "rationale": item["reason"],
                    "priority": item["priority"],
                    "source": item["source"],
                }
                for item in rebuilt
            ]
            limitations = [
                str(x)
                for x in (data.get("budget_limitations") or [])
                if x
            ]
            families = selected_families
            if campaign_budget > 0 and "mega" in families and campaign_budget < 1_000_000:
                note = (
                    "The available campaign budget may significantly limit celebrity "
                    "collaboration options depending on real negotiated rates."
                )
                if note not in limitations:
                    limitations.append(note)
                if "micro" not in families and not any(
                    canonical_tier_family(str(o.get("tier") or "")) == "micro" for o in optional
                ):
                    optional.append(
                        {
                            "type": "ADD_CREATOR_TIER",
                            "tier": "micro",
                            "reason": (
                                "Optional: ask the user whether they want to include lower-tier "
                                "creators if celebrity rates exceed the available budget."
                            ),
                            "requires_user_approval": True,
                        }
                    )
            elif campaign_budget > 0 and "macro" in families and campaign_budget <= 300_000:
                note = (
                    "Macro influencers were explicitly selected by the user. "
                    f"Given the current ₹{campaign_budget:,.0f} campaign budget, a macro-only "
                    "strategy may have limited flexibility depending on actual creator rates."
                )
                if note not in limitations:
                    limitations.append(note)
                if "micro" not in families and not any(
                    canonical_tier_family(str(o.get("tier") or "")) == "micro" for o in optional
                ):
                    optional.append(
                        {
                            "type": "ADD_CREATOR_TIER",
                            "tier": "micro",
                            "reason": (
                                "Optional: ask the user whether they want to include lower-tier "
                                "creators as an alternative if macro rates exceed the budget."
                            ),
                            "requires_user_approval": True,
                        }
                    )
            data["budget_limitations"] = limitations
            data["optional_recommendations"] = optional
            data["budget_strategy"] = self._tier_aware_budget(
                data.get("budget_strategy") if isinstance(data.get("budget_strategy"), dict) else {},
                selected,
                campaign_budget,
            )
        return data

    @staticmethod
    def _tier_aware_budget(
        budget: Dict[str, Any],
        selected: List[str],
        campaign_budget: float,
    ) -> Dict[str, Any]:
        creator_pct = budget.get("creator_budget_percentage")
        amp_pct = budget.get("content_amplification_percentage")
        reserve_pct = budget.get("reserve_percentage")
        if isinstance(budget.get("creator_allocation"), dict):
            creator_pct = budget["creator_allocation"].get("percentage", creator_pct)
        if isinstance(budget.get("amplification_allocation"), dict):
            amp_pct = budget["amplification_allocation"].get("percentage", amp_pct)
        if isinstance(budget.get("reserve"), dict):
            reserve_pct = budget["reserve"].get("percentage", reserve_pct)
        try:
            creator_pct = float(creator_pct) if creator_pct is not None else 80.0
        except (TypeError, ValueError):
            creator_pct = 80.0
        try:
            amp_pct = float(amp_pct) if amp_pct is not None else 10.0
        except (TypeError, ValueError):
            amp_pct = 10.0
        try:
            reserve_pct = float(reserve_pct) if reserve_pct is not None else 10.0
        except (TypeError, ValueError):
            reserve_pct = 10.0
        pct_total = creator_pct + amp_pct + reserve_pct
        if pct_total > 100.01:
            scale = 100.0 / pct_total
            creator_pct *= scale
            amp_pct *= scale
            reserve_pct *= scale

        selected_families = selected_tier_families(selected)
        existing_allocs = [
            item
            for item in (budget.get("tier_allocations") or [])
            if isinstance(item, dict)
            and canonical_tier_family(str(item.get("tier") or "")) in selected_families
        ]
        existing_families = {
            canonical_tier_family(str(item.get("tier") or "")) for item in existing_allocs
        }
        if selected and existing_families == selected_families and existing_allocs:
            tier_allocs = []
            for item in existing_allocs:
                pct = float(item.get("percentage") or 0)
                amount = item.get("amount")
                if amount is None and campaign_budget > 0:
                    amount = round(campaign_budget * pct / 100.0, 2)
                tier_allocs.append(
                    {
                        "tier": item.get("tier"),
                        "percentage": pct,
                        "amount": amount,
                        "source": "USER_SELECTED",
                    }
                )
        elif selected:
            share = creator_pct / len(selected)
            tier_allocs = []
            remaining_pct = creator_pct
            remaining_amt = round(campaign_budget * creator_pct / 100.0, 2) if campaign_budget > 0 else None
            for idx, tier in enumerate(selected):
                last = idx == len(selected) - 1
                pct = remaining_pct if last else round(share, 2)
                remaining_pct -= 0 if last else pct
                amount = None
                if remaining_amt is not None:
                    amount = remaining_amt if last else round(campaign_budget * pct / 100.0, 2)
                    remaining_amt = round(remaining_amt - (amount or 0), 2) if not last else remaining_amt
                tier_allocs.append(
                    {
                        "tier": tier,
                        "percentage": pct,
                        "amount": amount,
                        "source": "USER_SELECTED",
                    }
                )
        else:
            tier_allocs = budget.get("tier_allocations") or []

        def _amount(pct: Optional[float]) -> Optional[float]:
            if campaign_budget > 0 and pct is not None:
                return round(campaign_budget * float(pct) / 100.0, 2)
            return None

        budget["total_budget"] = campaign_budget if campaign_budget > 0 else budget.get("total_budget")
        budget["currency"] = budget.get("currency") or "INR"
        budget["creator_budget_percentage"] = creator_pct
        budget["content_amplification_percentage"] = amp_pct
        budget["reserve_percentage"] = reserve_pct
        budget["creator_allocation"] = {
            "amount": _amount(creator_pct),
            "percentage": creator_pct,
        }
        budget["amplification_allocation"] = {
            "amount": _amount(amp_pct),
            "percentage": amp_pct,
        }
        budget["reserve"] = {
            "amount": _amount(reserve_pct),
            "percentage": reserve_pct,
        }
        budget["tier_allocations"] = tier_allocs
        return budget
