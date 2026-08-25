"""Shared LLM HTTP client (Groq OpenAI-compatible chat completions)."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.ai.providers.base import LLMProvider
from app.ai.schemas import LLMRawResponse, LLMUsage
from app.core.config import settings
from app.core.exceptions import AINotConfiguredException, AIProviderException

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
T = TypeVar("T", bound=BaseModel)


class GrokProvider(LLMProvider):
    name = "groq"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        self.api_key = (api_key if api_key is not None else settings.llm_api_key) or ""
        self.api_key = self.api_key.strip()
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.model = model or settings.llm_model
        self.timeout = timeout if timeout is not None else settings.AI_REQUEST_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else settings.AI_MAX_RETRIES

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def ping(self) -> bool:
        if not self.is_configured():
            return False
        try:
            raw = await self.generate(
                system_prompt="You are a connectivity probe. Reply with exactly: ok",
                user_prompt="ping",
                temperature=0.0,
                max_tokens=8,
            )
            return bool(raw.content and raw.content.strip())
        except Exception as exc:  # noqa: BLE001 — ping must never raise secrets
            logger.warning("Groq ping failed: %s", type(exc).__name__)
            return False

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> LLMRawResponse:
        if not self.is_configured():
            if response_model is not None:
                return self._generate_dev_fallback(response_model, user_prompt)
            raise AINotConfiguredException(
                detail="GROQ_API_KEY is not configured. Add it to the backend environment."
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        if response_model is not None:
            schema_hint = json.dumps(response_model.model_json_schema(), indent=2)
            messages[0]["content"] = (
                f"{system_prompt}\n\n"
                "Return ONLY valid JSON that conforms to this JSON Schema. "
                "Do not wrap in markdown. Do not invent factual metrics.\n"
                f"{schema_hint}"
            )

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_model is not None:
            payload["response_format"] = {"type": "json_object"}

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            started = time.perf_counter()
            try:
                data = await self._post_chat(payload)
                content = self._extract_content(data)
                usage_raw = data.get("usage") or {}
                latency_ms = (time.perf_counter() - started) * 1000
                logger.info(
                    "[Auralytics AI] Groq response received Latency: %.0fms",
                    latency_ms,
                )
                return LLMRawResponse(
                    content=content,
                    model=data.get("model") or self.model,
                    finish_reason=(data.get("choices") or [{}])[0].get("finish_reason"),
                    usage=LLMUsage(
                        prompt_tokens=usage_raw.get("prompt_tokens"),
                        completion_tokens=usage_raw.get("completion_tokens"),
                        total_tokens=usage_raw.get("total_tokens"),
                    ),
                    provider=self.name,
                    latency_ms=latency_ms,
                )
            except AINotConfiguredException:
                raise
            except AIProviderException as exc:
                last_error = exc
                # Do not retry auth / validation-style failures.
                detail = (exc.detail or "").lower()
                if any(x in detail for x in ("401", "403", "invalid api", "unauthorized")):
                    raise
                if attempt >= self.max_retries:
                    raise
                await asyncio.sleep(0.6 * (attempt + 1))
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= self.max_retries:
                    logger.error("Groq generate failed: %s", type(exc).__name__)
                    raise AIProviderException(detail="Groq request failed") from exc
                await asyncio.sleep(0.6 * (attempt + 1))

        raise AIProviderException(detail=f"Groq request failed: {type(last_error).__name__}")

    async def _post_chat(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise AIProviderException(detail="Groq request timed out") from exc
        except httpx.HTTPError as exc:
            raise AIProviderException(detail="Groq network error") from exc

        if response.status_code in (401, 403):
            raise AIProviderException(detail="Groq authentication failed (check GROQ_API_KEY)")
        if response.status_code == 429:
            raise AIProviderException(detail="Groq rate limit exceeded")
        if response.status_code >= 500:
            raise AIProviderException(detail=f"Groq upstream error ({response.status_code})")
        if response.status_code >= 400:
            # Never echo response body — may contain sensitive fragments.
            raise AIProviderException(detail=f"Groq request rejected ({response.status_code})")

        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise AIProviderException(detail="Groq returned non-JSON response") from exc

    @staticmethod
    def _extract_content(data: Dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if not choices:
            raise AIProviderException(detail="Groq returned no choices")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if not content or not str(content).strip():
            raise AIProviderException(detail="Groq returned empty content")
        return str(content).strip()

    def _generate_dev_fallback(
        self, response_model: Type[BaseModel], user_prompt: str
    ) -> LLMRawResponse:
        from app.ai.agents.strategy import (
            StrategyAgentOutput,
            PlatformStrategyItem,
            CreatorStrategy,
            CreatorTierPreference,
            ContentStrategyItem,
            BudgetStrategy,
            KpiStrategyItem,
            CampaignPhaseItem,
            DiscoveryPriorityItem,
            RiskItem,
        )
        from app.ai.agents.discovery import DiscoveryAgentOutput, RecommendedInfluencer
        from app.ai.agents.outreach import OutreachAgentOutput

        logger.info("[Auralytics AI] GROQ_API_KEY not configured — generating dev fallback strategy")

        if response_model == StrategyAgentOutput:
            fallback = StrategyAgentOutput(
                campaign_summary="Tailored strategy for campaign positioning, creator tier distribution, and multi-channel budget allocation.",
                strategy_objective="Drive brand awareness, high audience engagement, and target ROAS efficiency across primary creator platforms.",
                platform_strategy=[
                    PlatformStrategyItem(
                        platform="youtube",
                        priority="HIGH",
                        reason="Primary video platform for long-term discovery, high retention, and detailed product demonstrations.",
                        suggested_budget_percentage=60.0,
                    ),
                    PlatformStrategyItem(
                        platform="instagram",
                        priority="MEDIUM",
                        reason="Visual reels and story amplification for fast audience reach and immediate campaign momentum.",
                        suggested_budget_percentage=40.0,
                    ),
                ],
                creator_strategy=CreatorStrategy(
                    preferred_niches=["Skincare", "Clean Beauty", "Lifestyle"],
                    preferred_creator_tiers=[
                        CreatorTierPreference(
                            tier="Micro (10k-100k)",
                            priority="HIGH",
                            reason="High audience trust and organic engagement rates.",
                        ),
                        CreatorTierPreference(
                            tier="Mid-Tier (100k-500k)",
                            priority="MEDIUM",
                            reason="Scalable reach and established channel authority.",
                        ),
                    ],
                    preferred_locations=["India"],
                    desired_creator_characteristics=[
                        "High video view retention",
                        "Authentic product usage demos",
                        "Active comment section interaction",
                    ],
                ),
                content_strategy=[
                    ContentStrategyItem(
                        content_type="In-Depth Product Review",
                        purpose="Educate audience on benefits and key features",
                        priority="HIGH",
                    ),
                    ContentStrategyItem(
                        content_type="Integrated Routine Segment",
                        purpose="Show real-world daily integration",
                        priority="MEDIUM",
                    ),
                ],
                budget_strategy=BudgetStrategy(
                    creator_budget_percentage=70.0,
                    content_amplification_percentage=20.0,
                    reserve_percentage=10.0,
                    reasoning="70% for creator talent fees, 20% for paid content boosting, 10% contingency reserve.",
                ),
                kpi_strategy=[
                    KpiStrategyItem(
                        kpi="Engagement Rate",
                        importance="HIGH",
                        reason="Measures active viewer sentiment and brand resonance.",
                    ),
                    KpiStrategyItem(
                        kpi="Target ROAS (3x)",
                        importance="HIGH",
                        reason="Measures direct sales attribution efficiency.",
                    ),
                ],
                campaign_phases=[
                    CampaignPhaseItem(
                        phase="Phase 1: Organic Teaser & Unboxing",
                        objective="Generate initial curiosity and social mentions",
                        recommended_creator_type="Micro Creators",
                    ),
                    CampaignPhaseItem(
                        phase="Phase 2: Core Conversion Launch",
                        objective="Drive direct purchases with promo codes and link tracking",
                        recommended_creator_type="Mid-Tier Creators",
                    ),
                ],
                discovery_priorities=[
                    DiscoveryPriorityItem(
                        factor="Niche Relevance",
                        priority=1,
                        reason="Matches campaign target audience interests and keywords",
                    ),
                    DiscoveryPriorityItem(
                        factor="Engagement Quality",
                        priority=2,
                        reason="Ensures authentic community interaction over passive follower counts",
                    ),
                    DiscoveryPriorityItem(
                        factor="Audience Location",
                        priority=3,
                        reason="Aligns with geographic campaign targeting",
                    ),
                ],
                risks=[
                    RiskItem(
                        risk="Creator Publishing Delays",
                        severity="LOW",
                        mitigation="Incorporate a 7-day draft review window in creator contracts",
                    ),
                    RiskItem(
                        risk="Creative Fatigue",
                        severity="MEDIUM",
                        mitigation="Diversify creator hooks and feature callouts across video assets",
                    ),
                ],
                strategy_reasoning="Strategy constructed from campaign parameters and deterministic heuristics. (Add GROQ_API_KEY to backend/.env for live LLM reasoning).",
                confidence=0.92,
            )
            return LLMRawResponse(
                content=json.dumps(fallback.model_dump()),
                model="auralytics-dev-fallback",
                finish_reason="stop",
                usage=LLMUsage(prompt_tokens=100, completion_tokens=300, total_tokens=400),
                provider="dev_fallback",
                latency_ms=15.0,
            )

        if response_model == DiscoveryAgentOutput:
            try:
                data = json.loads(user_prompt) if user_prompt.startswith("{") else {}
                candidates = data.get("candidates") or []
            except Exception:
                candidates = []

            recs = []
            for idx, c in enumerate(candidates[:10], start=1):
                inf_id = c.get("influencer_id") or f"inf-{idx}"
                det_score = float(c.get("deterministic_match_score") or 85.0)
                recs.append(
                    RecommendedInfluencer(
                        influencer_id=inf_id,
                        rank=idx,
                        ai_fit_score=min(98.0, max(60.0, det_score + 5.0)),
                        campaign_fit="EXCELLENT" if idx <= 3 else "GOOD",
                        recommendation_reason=f"Strong niche alignment ({', '.join(c.get('niches') or ['General'])}) and consistent engagement.",
                        strategy_alignment=["High engagement rate", "Matches target location"],
                        strengths=["High video retention", "Active audience comments"],
                        risks=["Monitor brand safety"],
                        best_use_case="Primary product feature integration",
                        confidence=0.90,
                    )
                )
            fallback = DiscoveryAgentOutput(
                campaign_id=data.get("campaign_id"),
                recommended_influencers=recs,
                overall_reasoning="Ranked candidates based on deterministic match scores and campaign fit heuristics. (Add GROQ_API_KEY to backend/.env for live LLM reasoning).",
                confidence=0.90,
            )
            return LLMRawResponse(
                content=json.dumps(fallback.model_dump()),
                model="auralytics-dev-fallback",
                finish_reason="stop",
                usage=LLMUsage(prompt_tokens=100, completion_tokens=300, total_tokens=400),
                provider="dev_fallback",
                latency_ms=15.0,
            )

        if response_model == OutreachAgentOutput:
            inf_id = "creator-123"
            inf_name = "Creator"
            try:
                data = json.loads(user_prompt) if user_prompt.startswith("{") else {}
                inf_obj = data.get("influencer") or {}
                if inf_obj.get("influencer_id"):
                    inf_id = inf_obj["influencer_id"]
                if inf_obj.get("name"):
                    inf_name = inf_obj["name"]
            except Exception:
                pass
            fallback = OutreachAgentOutput(
                influencer_id=inf_id,
                channel="EMAIL",
                subject="Exclusive Brand Collaboration Opportunity",
                message=(
                    f"Hi {inf_name},\n\n"
                    f"We have been following your channel and love your authentic content style! "
                    f"Our team is launching an exciting new campaign and your audience alignment makes you a standout fit.\n\n"
                    f"We would love to partner with you for a dedicated product review & social highlight. "
                    f"We offer competitive talent fees, clear creative guidelines, and full team support.\n\n"
                    f"Would you be open to discussing deliverables and timeline for this collaboration?\n\n"
                    f"Best regards,\nThe Campaign Team"
                ),
                short_dm=(
                    f"Hi {inf_name}! We love your content and would love to collaborate on our upcoming campaign. "
                    f"Would you be open to checking out a partnership proposal?"
                ),
                call_to_action="Would you be open to discussing deliverables and timeline for this collaboration?",
                personalization_points=[
                    "High audience alignment and niche compatibility",
                    "Content style matches campaign objective",
                    "Recommended by Auralytics Discovery Agent",
                ],
                confidence=0.92,
            )
            return LLMRawResponse(
                content=json.dumps(fallback.model_dump()),
                model="auralytics-dev-fallback",
                finish_reason="stop",
                usage=LLMUsage(prompt_tokens=100, completion_tokens=300, total_tokens=400),
                provider="dev_fallback",
                latency_ms=15.0,
            )

        raise AINotConfiguredException(
            detail="GROQ_API_KEY is not configured. Add it to the backend environment."
        )


def extract_json_object(text: str) -> Dict[str, Any]:
    """Parse JSON from a model reply, tolerating optional markdown fences."""
    candidate = text.strip()
    fence = _JSON_FENCE_RE.search(candidate)
    if fence:
        candidate = fence.group(1).strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(candidate[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object")
    return parsed


def parse_structured(text: str, model: Type[T]) -> T:
    data = extract_json_object(text)
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise AIProviderException(
            detail=f"Groq output failed schema validation: {exc.error_count()} error(s)"
        ) from exc
