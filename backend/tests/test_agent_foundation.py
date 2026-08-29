"""Tests for Grok provider foundation, Supervisor, and Strategy Agent (mocked LLM)."""

from __future__ import annotations

import json
from copy import deepcopy
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.ai.agents.base import AgentContext
from app.ai.agents.discovery import (
    DiscoveryAgent,
    DiscoveryAgentOutput,
    combine_scores,
    extract_strategy_guidance,
)
from app.ai.agents.strategy import StrategyAgent, StrategyAgentOutput
from app.ai.llm_service import LLMService
from app.ai.providers.grok import (
    compact_json_schema,
    extract_json_object,
    parse_structured,
    schema_hint_for_prompt,
)
from app.ai.schemas import AgentResultEnvelope, LLMRawResponse
from app.ai.workflow_states import AgentRunStatus, WorkflowState
from app.core.config import settings
from app.core.exceptions import AgentValidationException, AIProviderException

SAMPLE_STRATEGY = {
    "campaign_summary": "Launch with micro creators on YouTube focused on skincare education.",
    "strategy_objective": "Drive awareness and consideration for fitness products in India.",
    "platform_strategy": [
        {"platform": "youtube", "priority": "HIGH", "reason": "Long-form demos", "suggested_budget_percentage": 70},
        {"platform": "instagram", "priority": "MEDIUM", "reason": "Reach", "suggested_budget_percentage": 30},
    ],
    "creator_strategy": {
        "preferred_niches": ["fitness", "wellness"],
        "preferred_creator_tiers": [
            {"tier": "micro", "priority": "HIGH", "reason": "Efficient CPA"}
        ],
        "preferred_locations": ["India"],
        "desired_creator_characteristics": [
            "Educational workout content",
            "High engagement",
        ],
    },
    "content_strategy": [
        {"content_type": "Reels", "purpose": "Awareness", "priority": "HIGH"},
        {"content_type": "YouTube Review", "purpose": "Consideration", "priority": "MEDIUM"},
    ],
    "budget_strategy": {
        "creator_budget_percentage": 70,
        "content_amplification_percentage": 20,
        "reserve_percentage": 10,
        "reasoning": "Prioritize creator fees.",
    },
    "kpi_strategy": [
        {"kpi": "Engagement Rate", "importance": "HIGH", "reason": "Awareness objective"},
        {"kpi": "ROAS", "importance": "MEDIUM", "reason": "Sales support"},
    ],
    "campaign_phases": [
        {"phase": "Launch", "objective": "Awareness", "recommended_creator_type": "micro fitness"}
    ],
    "discovery_priorities": [
        {"factor": "Niche Match", "priority": 1, "reason": "Fitness alignment"},
        {"factor": "Engagement Quality", "priority": 2, "reason": "Active audience"},
        {"factor": "Audience Match", "priority": 3, "reason": "India focus"},
    ],
    "risks": [
        {"risk": "Seasonality", "severity": "MEDIUM", "mitigation": "Plan content calendar early"}
    ],
    "strategy_reasoning": "Matches brief budget and platforms.",
    "confidence": 0.82,
}


def _mock_grok_meta(structured):
    return structured, LLMRawResponse(
        content=json.dumps(structured.model_dump() if hasattr(structured, "model_dump") else structured),
        model="openai/gpt-oss-120b",
        provider="groq",
        latency_ms=42.0,
    )


SAMPLE_DISCOVERY = {
    "campaign_id": "camp-test",
    "recommended_influencers": [
        {
            "influencer_id": "PLACEHOLDER",
            "rank": 1,
            "ai_fit_score": 92,
            "campaign_fit": "EXCELLENT",
            "recommendation_reason": "Strong fitness niche alignment",
            "strategy_alignment": ["Matches micro creator tier", "Fitness educational content"],
            "strengths": ["Engaged audience", "Consistent uploads"],
            "risks": ["Seasonal content dip"],
            "best_use_case": "Instagram Reels + workout tutorial",
            "confidence": 0.91,
        }
    ],
    "overall_reasoning": "Micro fitness creators align best with strategy priorities.",
    "confidence": 0.9,
}


async def _register(client: AsyncClient, email: str) -> dict:
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Agent Tester",
            "email": email,
            "password": "securePassword456",
            "company_name": "Auralytics",
            "role": "marketing_manager",
        },
    )
    assert res.status_code in (200, 201), res.text
    return res.json()


async def _create_campaign(client: AsyncClient, headers: dict) -> str:
    res = await client.post(
        "/api/v1/campaigns",
        headers=headers,
        json={
            "name": "Summer Fitness Launch",
            "brand": "FitCo",
            "budget": 200000,
            "objective": "Awareness",
            "start_date": "2026-08-01",
            "end_date": "2026-09-01",
            "status": "planning",
            "platforms": ["youtube"],
            "interests": ["fitness"],
            "description": "Fitness launch India",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_extract_json_object_strips_fences():
    assert extract_json_object('```json\n{"a": 1}\n```') == {"a": 1}


def test_groq_schema_hint_is_compact():
    pretty = json.dumps(StrategyAgentOutput.model_json_schema(), indent=2)
    hint = schema_hint_for_prompt(StrategyAgentOutput)
    assert len(hint) < len(pretty)
    assert "\n" not in hint
    assert '"title"' not in hint
    compact = compact_json_schema(StrategyAgentOutput.model_json_schema())
    assert "campaign_summary" in json.dumps(compact)
    assert "creator_strategy" in json.dumps(compact)


def test_parse_structured_strategy():
    parsed = parse_structured(json.dumps(SAMPLE_STRATEGY), StrategyAgentOutput)
    assert parsed.confidence == 0.82


@pytest.mark.asyncio
async def test_ai_status_authenticated(client: AsyncClient):
    auth = await _register(client, "ai.status@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    with patch.object(LLMService, "status", new_callable=AsyncMock) as status_mock:
        status_mock.return_value = {
            "provider": "groq",
            "configured": False,
            "reachable": False,
            "model_configured": True,
            "model": "openai/gpt-oss-120b",
            "detail": "GROQ_API_KEY is missing",
        }
        res = await client.get("/api/v1/ai/status?probe=false", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["provider"] == "groq"
    # Ensure the raw API key value is never returned (detail may mention the env var name).
    assert body.get("detail") != settings.llm_api_key if settings.llm_api_key else True
    dumped = json.dumps(body).lower()
    assert "bearer " not in dumped
    assert not any(k for k in ("sk-", "gsk_") if k in dumped and len(k) > 3)


@pytest.mark.asyncio
async def test_strategy_agent_end_to_end(client: AsyncClient):
    auth = await _register(client, "strategy.ok@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    camp_id = await _create_campaign(client, headers)
    structured = StrategyAgentOutput.model_validate(SAMPLE_STRATEGY)

    with patch.object(LLMService, "generate_structured_with_meta", new_callable=AsyncMock) as gen:
        gen.return_value = _mock_grok_meta(structured)
        res = await client.post(f"/api/v1/campaigns/{camp_id}/agents/strategy", headers=headers)

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["workflowState"] == WorkflowState.STRATEGY_COMPLETED
    assert body["agentRun"]["status"] == AgentRunStatus.COMPLETED
    assert body["agentRun"]["outputJson"]["data"]["campaign_summary"]
    assert body["agentRun"]["provider"] == "groq"

    strat = await client.get(f"/api/v1/campaigns/{camp_id}/agents/strategy", headers=headers)
    assert strat.status_code == 200
    assert strat.json()["version"] == 1

    runs = await client.get("/api/v1/agent-runs", headers=headers)
    assert runs.status_code == 200
    assert len(runs.json()) >= 1


@pytest.mark.asyncio
async def test_strategy_isolation(client: AsyncClient):
    auth_a = await _register(client, "owner.a@example.com")
    auth_b = await _register(client, "owner.b@example.com")
    headers_a = {"Authorization": f"Bearer {auth_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {auth_b['access_token']}"}
    camp_id = await _create_campaign(client, headers_a)

    res = await client.post(f"/api/v1/campaigns/{camp_id}/agents/strategy", headers=headers_b)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_strategy_budget_validation_rejects_overspend():
    agent = StrategyAgent()
    camp = type("C", (), {"budget": 200000, "owner_id": "x", "id": "c1", "name": "n"})()
    user = type("U", (), {"id": "x"})()
    ctx = AgentContext(user=user, campaign=camp, db=None)  # type: ignore[arg-type]
    bad = AgentResultEnvelope(
        status="COMPLETED",
        summary="bad",
        confidence=0.5,
        data={
            **SAMPLE_STRATEGY,
            "budget_strategy": {
                "creator_budget_percentage": 80,
                "content_amplification_percentage": 30,
                "reserve_percentage": 10,
                "reasoning": "overspend",
            },
        },
    )
    with pytest.raises(AgentValidationException):
        await agent.validate_output(ctx, bad, {"budget": 200000})


@pytest.mark.asyncio
async def test_strategy_rejects_influencer_handles():
    agent = StrategyAgent()
    camp = type("C", (), {"owner_id": "x", "id": "c1", "name": "n"})()
    user = type("U", (), {"id": "x"})()
    ctx = AgentContext(user=user, campaign=camp, db=None)  # type: ignore[arg-type]
    bad = AgentResultEnvelope(
        status="COMPLETED",
        summary="bad",
        confidence=0.5,
        data={**SAMPLE_STRATEGY, "campaign_summary": "Choose @fitguru for this campaign"},
    )
    with pytest.raises(AgentValidationException):
        await agent.validate_output(ctx, bad, {})


def test_strategy_output_includes_discovery_priorities():
    parsed = StrategyAgentOutput.model_validate(SAMPLE_STRATEGY)
    persisted = parsed.to_persisted_dict()
    assert persisted["discovery_priorities"]
    assert persisted["creator_strategy"]
    assert persisted["recommended_platform_mix"]  # legacy mirror for UI


def test_creator_tier_ranges_are_centralized():
    from app.ai.creator_tiers import (
        extract_subscriber_range,
        followers_match_selected_tiers,
        range_for_tiers,
        selected_tier_keys,
        tier_for_followers,
    )

    assert tier_for_followers(50_000) == "micro"
    assert tier_for_followers(200_000) == "mid"
    assert tier_for_followers(700_000) == "macro"
    assert tier_for_followers(2_500_000) == "mega"
    mn, mx = range_for_tiers(["micro", "mid"])
    assert mn == 10_000
    assert mx == 500_000
    mn2, mx2 = extract_subscriber_range(
        {
            "creator_strategy": {
                "preferred_creator_tiers": [{"tier": "MICRO", "priority": "HIGH"}],
            }
        }
    )
    assert mn2 == 10_000
    assert mx2 == 100_000
    assert selected_tier_keys(["MACRO", "CELEBRITY"]) == ["macro", "celebrity"]
    assert followers_match_selected_tiers(700_000, ["macro", "celebrity"]) is True
    assert followers_match_selected_tiers(2_500_000, ["macro", "celebrity"]) is True
    assert followers_match_selected_tiers(50_000, ["macro", "celebrity"]) is False
    assert followers_match_selected_tiers(200_000, ["micro", "macro"]) is False
    assert followers_match_selected_tiers(40_000, ["micro", "macro"]) is True


@pytest.mark.asyncio
async def test_strategy_rejects_zero_budget():
    agent = StrategyAgent()
    camp = type(
        "C",
        (),
        {"budget": 0, "owner_id": "x", "id": "c1", "name": "n"},
    )()
    user = type("U", (), {"id": "x"})()
    ctx = AgentContext(user=user, campaign=camp, db=None)  # type: ignore[arg-type]
    with pytest.raises(AgentValidationException) as exc:
        agent.validate_input(ctx)
    assert "REQUIRES_USER_INPUT" in str(exc.value.detail)


def _strategy_campaign(**kwargs):
    defaults = dict(
        budget=3_000_000,
        owner_id="x",
        id="c1",
        name="n",
        creator_tiers=None,
        platforms=["youtube"],
        brand="B",
        description="d",
        objective="Launch",
    )
    defaults.update(kwargs)
    return type("C", (), defaults)()


@pytest.mark.asyncio
async def test_strategy_preserves_macro_celebrity_when_grok_returns_micro():
    agent = StrategyAgent()
    camp = _strategy_campaign(creator_tiers=["MACRO", "CELEBRITY"], budget=3_000_000)
    user = type("U", (), {"id": "x"})()
    ctx = AgentContext(user=user, campaign=camp, db=None)  # type: ignore[arg-type]
    result = AgentResultEnvelope(
        status="COMPLETED",
        summary="ok",
        confidence=0.8,
        data=deepcopy(SAMPLE_STRATEGY),
    )
    validated = await agent.validate_output(ctx, result, {})
    preferred = validated.data["creator_strategy"]["preferred_creator_tiers"]
    families = {str(item["tier"]).lower() for item in preferred}
    assert "macro" in families
    assert "celebrity" in families
    assert "micro" not in families
    assert all(item.get("source") == "USER_SELECTED" for item in preferred)
    assert validated.data["user_selected_creator_tiers"] == ["macro", "celebrity"]
    alloc_tiers = {
        str(item["tier"]).lower()
        for item in (validated.data["budget_strategy"].get("tier_allocations") or [])
    }
    assert "macro" in alloc_tiers
    assert "celebrity" in alloc_tiers
    assert "micro" not in alloc_tiers
    optional = validated.data.get("optional_recommendations") or []
    assert any(str(o.get("tier") or "").lower() == "micro" for o in optional)
    assert all(o.get("requires_user_approval") for o in optional)


@pytest.mark.asyncio
async def test_strategy_low_budget_macro_keeps_macro_as_optional_micro():
    agent = StrategyAgent()
    camp = _strategy_campaign(creator_tiers=["macro"], budget=300_000)
    user = type("U", (), {"id": "x"})()
    ctx = AgentContext(user=user, campaign=camp, db=None)  # type: ignore[arg-type]
    result = AgentResultEnvelope(
        status="COMPLETED",
        summary="ok",
        confidence=0.8,
        data=deepcopy(SAMPLE_STRATEGY),
    )
    validated = await agent.validate_output(ctx, result, {})
    preferred = validated.data["creator_strategy"]["preferred_creator_tiers"]
    assert [item["tier"] for item in preferred] == ["macro"]
    assert validated.data["budget_limitations"]
    optional = validated.data.get("optional_recommendations") or []
    assert any(str(o.get("tier") or "").lower() == "micro" and o.get("requires_user_approval") for o in optional)
    alloc = validated.data["budget_strategy"]["tier_allocations"]
    assert alloc and alloc[0]["tier"] == "macro"
    total = sum(float(item.get("amount") or 0) for item in alloc)
    assert total <= 300_000 + 0.01


@pytest.mark.asyncio
async def test_strategy_high_budget_macro_does_not_make_micro_primary():
    agent = StrategyAgent()
    camp = _strategy_campaign(creator_tiers=["macro"], budget=3_000_000)
    user = type("U", (), {"id": "x"})()
    ctx = AgentContext(user=user, campaign=camp, db=None)  # type: ignore[arg-type]
    result = AgentResultEnvelope(
        status="COMPLETED",
        summary="ok",
        confidence=0.8,
        data=deepcopy(SAMPLE_STRATEGY),
    )
    validated = await agent.validate_output(ctx, result, {})
    preferred = [item["tier"] for item in validated.data["creator_strategy"]["preferred_creator_tiers"]]
    assert preferred == ["macro"]
    assert "micro" not in {
        str(item["tier"]).lower()
        for item in validated.data["budget_strategy"].get("tier_allocations") or []
    }

def test_combine_scores_explicit_formula():
    assert combine_scores(80, 90, det_weight=0.65, ai_weight=0.35) == 83.5


def test_extract_strategy_guidance_from_legacy():
    legacy = {
        "campaign_summary": "Legacy strategy",
        "recommended_platform_mix": [{"platform": "youtube", "percentage": 100}],
        "creator_tier_strategy": [{"tier": "micro", "rationale": "efficient"}],
        "recommended_kpis": ["Engagement"],
    }
    guidance = extract_strategy_guidance(legacy)
    assert guidance["platform_strategy"]
    assert guidance["discovery_priorities"]


@pytest.mark.asyncio
async def test_strategy_failure_marks_run_failed(client: AsyncClient):
    auth = await _register(client, "strategy.fail@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    camp_id = await _create_campaign(client, headers)

    with patch.object(LLMService, "generate_structured_with_meta", new_callable=AsyncMock) as gen:
        gen.side_effect = AIProviderException(detail="simulated grok failure")
        res = await client.post(f"/api/v1/campaigns/{camp_id}/agents/strategy", headers=headers)

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["agentRun"]["status"] == AgentRunStatus.FAILED
    assert body["workflowState"] == WorkflowState.FAILED

    strat = await client.get(f"/api/v1/campaigns/{camp_id}/agents/strategy", headers=headers)
    assert strat.json() is None


DISCOVERY_PATH = "app.services.creator_discovery_service.YouTubeProvider"


def _youtube_channel(channel_id: str, title: str, subscribers: str = "82000"):
    from app.integrations.youtube.schemas import (
        YouTubeChannelItem,
        YouTubeContentDetails,
        YouTubeRelatedPlaylists,
        YouTubeSnippet,
        YouTubeStatistics,
    )

    return YouTubeChannelItem(
        id=channel_id,
        snippet=YouTubeSnippet(
            title=title,
            description="Fitness and workout content from India.",
            customUrl=f"@{channel_id.lower()}",
            country="IN",
            thumbnails={"high": {"url": f"https://yt3.ggpht.com/{channel_id}.jpg"}},
        ),
        statistics=YouTubeStatistics(
            subscriberCount=subscribers,
            viewCount="18000000",
            videoCount="248",
            hiddenSubscriberCount=False,
        ),
        contentDetails=YouTubeContentDetails(
            relatedPlaylists=YouTubeRelatedPlaylists(uploads=f"UU{channel_id[2:]}")
        ),
    )


def _recent_videos(count: int = 5):
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    return [
        {
            "id": f"vid{i}",
            "title": f"Workout video {i}",
            "published_at": (now - timedelta(days=i * 3)).isoformat().replace("+00:00", "Z"),
            "view_count": 60000 + i * 1000,
            "like_count": 3000 + i * 100,
            "comment_count": 200 + i * 10,
        }
        for i in range(count)
    ]


async def _seed_youtube_candidates(client: AsyncClient, headers: dict, campaign_id: str) -> str:
    channel = _youtube_channel("UCfit001", "Fitness With Rahul")
    with patch(f"{DISCOVERY_PATH}.is_configured", return_value=True), patch(
        f"{DISCOVERY_PATH}.search_channel_candidates", new_callable=AsyncMock
    ) as mock_search, patch(
        f"{DISCOVERY_PATH}.fetch_channels", new_callable=AsyncMock
    ) as mock_channels, patch(
        f"{DISCOVERY_PATH}.fetch_recent_video_stats", new_callable=AsyncMock
    ) as mock_videos:
        mock_search.return_value = {"UCfit001": "fitness India"}
        mock_channels.return_value = [channel]
        mock_videos.return_value = _recent_videos()
        res = await client.post(
            f"/api/v1/campaigns/{campaign_id}/discover-creators",
            headers=headers,
        )
    assert res.status_code == 200, res.text
    return res.json()["creators"][0]["creator"]["id"]


@pytest.mark.asyncio
async def test_discovery_combines_deterministic_and_ai_scores():
    agent = DiscoveryAgent()
    camp = type("C", (), {"owner_id": "x", "id": "c1", "name": "n"})()
    user = type("U", (), {"id": "x"})()
    ctx = AgentContext(user=user, campaign=camp, db=None)  # type: ignore[arg-type]
    result = AgentResultEnvelope(
        status="COMPLETED",
        summary="ok",
        confidence=0.9,
        recommendations=[
            {"influencer_id": "inf-a", "ai_fit_score": 95, "confidence": 0.9, "rank": 2},
            {"influencer_id": "inf-b", "ai_fit_score": 70, "confidence": 0.8, "rank": 1},
        ],
        data={},
    )
    context = {
        "candidate_ids": ["inf-a", "inf-b"],
        "candidates": [
            {"influencer_id": "inf-a", "deterministic_match_score": 60},
            {"influencer_id": "inf-b", "deterministic_match_score": 90},
        ],
    }
    validated = await agent.validate_output(ctx, result, context)
    ranks = {r["influencer_id"]: r["rank"] for r in validated.recommendations}
    assert ranks["inf-b"] == 1
    assert all("final_score" in r for r in validated.recommendations)


@pytest.mark.asyncio
async def test_discovery_rejects_hallucinated_influencer_id():
    agent = DiscoveryAgent()
    camp = type("C", (), {"owner_id": "x", "id": "c1", "name": "n"})()
    user = type("U", (), {"id": "x"})()
    ctx = AgentContext(user=user, campaign=camp, db=None)  # type: ignore[arg-type]
    bad = AgentResultEnvelope(
        status="COMPLETED",
        summary="bad",
        confidence=0.5,
        recommendations=[
            {"influencer_id": "fake-id-not-in-set", "ai_fit_score": 90, "confidence": 0.9, "rank": 1}
        ],
        data={},
    )
    with pytest.raises(AgentValidationException):
        await agent.validate_output(ctx, bad, {"candidate_ids": ["real-inf-1"]})


@pytest.mark.asyncio
async def test_discovery_agent_end_to_end(client: AsyncClient):
    auth = await _register(client, "discovery.ai@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    camp_id = await _create_campaign(client, headers)

    strategy_structured = StrategyAgentOutput.model_validate(SAMPLE_STRATEGY)
    with patch.object(LLMService, "generate_structured_with_meta", new_callable=AsyncMock) as gen:
        gen.return_value = _mock_grok_meta(strategy_structured)
        strat_res = await client.post(f"/api/v1/campaigns/{camp_id}/agents/strategy", headers=headers)
    assert strat_res.status_code == 200, strat_res.text

    influencer_id = await _seed_youtube_candidates(client, headers, camp_id)

    discovery_payload = dict(SAMPLE_DISCOVERY)
    discovery_payload["recommended_influencers"][0]["influencer_id"] = influencer_id
    discovery_structured = DiscoveryAgentOutput.model_validate(discovery_payload)

    with patch.object(LLMService, "generate_structured_with_meta", new_callable=AsyncMock) as gen:
        gen.return_value = _mock_grok_meta(discovery_structured)
        res = await client.post(f"/api/v1/campaigns/{camp_id}/agents/discovery", headers=headers)

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["workflowState"] == WorkflowState.SHORTLIST_APPROVAL_PENDING
    assert body["agentRun"]["status"] == AgentRunStatus.WAITING_APPROVAL
    assert body["agentRun"]["provider"] == "groq"

    approvals = await client.get("/api/v1/approvals", headers=headers)
    assert approvals.status_code == 200
    assert len(approvals.json()) >= 1

    creators = await client.get(f"/api/v1/campaigns/{camp_id}/influencers", headers=headers)
    assert creators.status_code == 200
    creator = creators.json()["creators"][0]
    ai_reasons = [
        r for r in (creator.get("matchReasons") or creator.get("match_reasons") or [])
        if r.get("source") == "discovery_agent_grok" or r.get("key") == "ai_discovery"
    ]
    assert ai_reasons
    assert ai_reasons[0]["weight"] == 92
    assert ai_reasons[0]["label"] == "AI Campaign Fit"


@pytest.mark.asyncio
async def test_discovery_does_not_modify_influencer_metrics(client: AsyncClient):
    auth = await _register(client, "discovery.metrics@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    camp_id = await _create_campaign(client, headers)

    strategy_structured = StrategyAgentOutput.model_validate(SAMPLE_STRATEGY)
    with patch.object(LLMService, "generate_structured_with_meta", new_callable=AsyncMock) as gen:
        gen.return_value = _mock_grok_meta(strategy_structured)
        await client.post(f"/api/v1/campaigns/{camp_id}/agents/strategy", headers=headers)

    influencer_id = await _seed_youtube_candidates(client, headers, camp_id)
    before = await client.get(f"/api/v1/influencers/{influencer_id}", headers=headers)
    assert before.status_code == 200
    before_metrics = {
        "followers": before.json()["followers"],
        "avgViews": before.json().get("avgViews") or before.json().get("avg_views"),
        "engagementRate": before.json().get("engagementRate") or before.json().get("engagement_rate"),
    }

    discovery_payload = dict(SAMPLE_DISCOVERY)
    discovery_payload["recommended_influencers"][0]["influencer_id"] = influencer_id
    discovery_structured = DiscoveryAgentOutput.model_validate(discovery_payload)

    with patch.object(LLMService, "generate_structured_with_meta", new_callable=AsyncMock) as gen:
        gen.return_value = _mock_grok_meta(discovery_structured)
        await client.post(f"/api/v1/campaigns/{camp_id}/agents/discovery", headers=headers)

    after = await client.get(f"/api/v1/influencers/{influencer_id}", headers=headers)
    assert after.status_code == 200
    after_metrics = {
        "followers": after.json()["followers"],
        "avgViews": after.json().get("avgViews") or after.json().get("avg_views"),
        "engagementRate": after.json().get("engagementRate") or after.json().get("engagement_rate"),
    }
    assert before_metrics == after_metrics
