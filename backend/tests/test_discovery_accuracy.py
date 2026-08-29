"""Discovery Agent requirement handling: hard user constraints vs Strategy preferences."""

from __future__ import annotations

from types import SimpleNamespace

import json
import pytest

from app.ai.agents.base import AgentContext
from app.ai.agents.discovery import DiscoveryAgent
from app.ai.discovery_requirements import build_discovery_requirements
from app.ai.schemas import AgentResultEnvelope
from app.core.exceptions import AgentValidationException
from app.models.campaign import Campaign
from app.services.query_builder import CampaignQueryBuilder


def _campaign(**kwargs):
    defaults = dict(
        id="camp-disc-1",
        owner_id="user-1",
        name="Vitamin C Serum Launch",
        brand="GlowNaturals",
        objective="Conversions",
        budget=300000,
        platforms=["youtube"],
        interests=["Skincare"],
        keywords=["vitamin c serum"],
        campaign_types=["Product Review"],
        target_locations="India",
        min_followers=None,
        max_followers=None,
        creator_tiers=None,
        description="Vitamin C serum for Indian skin",
        primary_kpi="ROAS",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _ctx(campaign):
    user = SimpleNamespace(id=getattr(campaign, "owner_id", "user-1"))
    return AgentContext(user=user, campaign=campaign, db=None)  # type: ignore[arg-type]


def _envelope(recs):
    return AgentResultEnvelope(
        status="COMPLETED",
        summary="ok",
        confidence=0.9,
        recommendations=recs,
        data={},
    )


@pytest.mark.asyncio
async def test_user_subscriber_range_is_hard_constraint():
    agent = DiscoveryAgent()
    camp = _campaign(min_followers=50000, max_followers=150000)
    ctx = _ctx(camp)
    result = _envelope(
        [
            {"influencer_id": "inf-low", "ai_fit_score": 99, "rank": 1, "confidence": 0.9},
            {"influencer_id": "inf-ok", "ai_fit_score": 80, "rank": 2, "confidence": 0.8},
            {"influencer_id": "inf-high", "ai_fit_score": 97, "rank": 3, "confidence": 0.9},
        ]
    )
    context = {
        "candidate_ids": ["inf-low", "inf-ok", "inf-high"],
        "candidates": [
            {"influencer_id": "inf-low", "followers": 20000, "platform": "youtube", "deterministic_match_score": 70},
            {"influencer_id": "inf-ok", "followers": 75000, "platform": "youtube", "deterministic_match_score": 70},
            {"influencer_id": "inf-high", "followers": 400000, "platform": "youtube", "deterministic_match_score": 70},
        ],
    }
    validated = await agent.validate_output(ctx, result, context)
    ids = [r["influencer_id"] for r in validated.recommendations]
    assert ids == ["inf-ok"]
    assert validated.recommendations[0]["eligibility"] == "ELIGIBLE"
    assert validated.data["ineligible_count"] == 2


@pytest.mark.asyncio
async def test_hard_subscriber_max_overrides_grok_eligible():
    agent = DiscoveryAgent()
    camp = _campaign(min_followers=10000, max_followers=100000)
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-macro",
                "ai_fit_score": 99,
                "rank": 1,
                "confidence": 0.99,
                "eligibility": "ELIGIBLE",
            }
        ]
    )
    context = {
        "candidate_ids": ["inf-macro"],
        "candidates": [
            {"influencer_id": "inf-macro", "followers": 900000, "platform": "youtube", "deterministic_match_score": 50},
        ],
    }
    with pytest.raises(AgentValidationException) as exc:
        await agent.validate_output(ctx, result, context)
    assert "hard requirements" in str(exc.value.detail).lower() or "hard" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_missing_location_stays_unknown():
    agent = DiscoveryAgent()
    camp = _campaign(target_locations="India")
    ctx = _ctx(camp)
    result = _envelope(
        [
            {"influencer_id": "inf-loc", "ai_fit_score": 88, "rank": 1, "confidence": 0.8},
        ]
    )
    context = {
        "candidate_ids": ["inf-loc"],
        "candidates": [
            {
                "influencer_id": "inf-loc",
                "followers": 72000,
                "platform": "youtube",
                "country": "DATA_UNAVAILABLE",
                "location": "DATA_UNAVAILABLE",
                "deterministic_match_score": 80,
            }
        ],
    }
    validated = await agent.validate_output(ctx, result, context)
    rec = validated.recommendations[0]
    assert rec["requirement_match"]["location"] == "UNKNOWN"
    assert rec["requirements_match"]["location"] == "UNKNOWN"


@pytest.mark.asyncio
async def test_too_few_matches_are_not_padded():
    agent = DiscoveryAgent()
    camp = _campaign(min_followers=10000, max_followers=100000)
    ctx = _ctx(camp)
    result = _envelope(
        [
            {"influencer_id": "inf-1", "ai_fit_score": 90, "rank": 1, "confidence": 0.9},
            {"influencer_id": "inf-2", "ai_fit_score": 88, "rank": 2, "confidence": 0.8},
            {"influencer_id": "inf-3", "ai_fit_score": 85, "rank": 3, "confidence": 0.8},
        ]
    )
    context = {
        "candidate_ids": ["inf-1", "inf-2", "inf-3"],
        "candidates": [
            {"influencer_id": "inf-1", "followers": 40000, "platform": "youtube", "deterministic_match_score": 70},
            {"influencer_id": "inf-2", "followers": 55000, "platform": "youtube", "deterministic_match_score": 70},
            {"influencer_id": "inf-3", "followers": 80000, "platform": "youtube", "deterministic_match_score": 70},
        ],
    }
    validated = await agent.validate_output(ctx, result, context)
    assert len(validated.recommendations) == 3


@pytest.mark.asyncio
async def test_strategy_range_is_preference_not_hard_exclusion():
    reqs = build_discovery_requirements(
        _campaign(min_followers=None, max_followers=None),
        {
            "creator_strategy": {
                "preferred_creator_tiers": [{"tier": "micro"}],
                "recommended_subscriber_range": {"minimum": 10000, "maximum": 100000},
            }
        },
    )
    assert reqs.hard_subscriber_min is None
    assert reqs.hard_subscriber_max is None
    assert reqs.preferred_subscriber_min == 10000
    assert reqs.preferred_subscriber_max == 100000
    assert reqs.hard_subscriber_ok(250000) is True
    assert reqs.preferred_subscriber_ok(250000) is False


@pytest.mark.asyncio
async def test_user_platform_requirement_wins():
    reqs = build_discovery_requirements(_campaign(platforms=["youtube"]), {})
    assert reqs.hard_platform_ok("youtube") is True
    assert reqs.hard_platform_ok("instagram") is False


def test_query_builder_uses_campaign_then_content_intent():
    campaign = Campaign(
        id="camp-q-1",
        owner_id=__import__("uuid").uuid4(),
        name="Serum Launch",
        brand="GlowNaturals",
        objective="Conversions",
        target_locations="India",
        interests=["Skincare"],
        keywords=["vitamin c serum"],
        campaign_types=["Product Review", "Tutorial"],
    )
    queries = CampaignQueryBuilder.build_queries(
        campaign,
        max_queries=6,
        strategy={"creator_strategy": {"preferred_niches": ["Skincare"]}},
    )
    blob = " ".join(queries).lower()
    assert any("skincare" in q.lower() for q in queries)
    assert any("vitamin c serum" in q.lower() for q in queries)
    assert "india" in blob
    assert "review" in blob or "tutorial" in blob


@pytest.mark.asyncio
async def test_user_selected_macro_is_hard_filter():
    agent = DiscoveryAgent()
    camp = _campaign(creator_tiers=["macro"], min_followers=10000, max_followers=500000)
    ctx = _ctx(camp)
    result = _envelope(
        [
            {"influencer_id": "inf-micro", "ai_fit_score": 99, "rank": 1, "confidence": 0.9},
            {"influencer_id": "inf-macro", "ai_fit_score": 80, "rank": 2, "confidence": 0.8},
            {"influencer_id": "inf-celeb", "ai_fit_score": 97, "rank": 3, "confidence": 0.9},
        ]
    )
    context = {
        "candidate_ids": ["inf-micro", "inf-macro", "inf-celeb"],
        "candidates": [
            {"influencer_id": "inf-micro", "followers": 75000, "platform": "youtube", "deterministic_match_score": 70},
            {"influencer_id": "inf-macro", "followers": 700000, "platform": "youtube", "deterministic_match_score": 70},
            {"influencer_id": "inf-celeb", "followers": 2_500_000, "platform": "youtube", "deterministic_match_score": 70},
        ],
    }
    validated = await agent.validate_output(ctx, result, context)
    ids = [r["influencer_id"] for r in validated.recommendations]
    assert ids == ["inf-macro"]
    assert validated.recommendations[0]["creator_tier"] == "macro"
    assert validated.recommendations[0]["tier_match"] == "MATCH"


@pytest.mark.asyncio
async def test_user_selected_celebrity_only():
    agent = DiscoveryAgent()
    camp = _campaign(creator_tiers=["celebrity"])
    ctx = _ctx(camp)
    result = _envelope(
        [
            {"influencer_id": "inf-macro", "ai_fit_score": 99, "rank": 1, "confidence": 0.9},
            {"influencer_id": "inf-celeb", "ai_fit_score": 80, "rank": 2, "confidence": 0.8},
        ]
    )
    context = {
        "candidate_ids": ["inf-macro", "inf-celeb"],
        "candidates": [
            {"influencer_id": "inf-macro", "followers": 700000, "platform": "youtube", "deterministic_match_score": 50},
            {"influencer_id": "inf-celeb", "followers": 2_500_000, "platform": "youtube", "deterministic_match_score": 50},
        ],
    }
    validated = await agent.validate_output(ctx, result, context)
    assert [r["influencer_id"] for r in validated.recommendations] == ["inf-celeb"]


@pytest.mark.asyncio
async def test_macro_plus_celebrity_excludes_micro():
    agent = DiscoveryAgent()
    camp = _campaign(creator_tiers=["macro", "celebrity"])
    ctx = _ctx(camp)
    result = _envelope(
        [
            {"influencer_id": "inf-micro", "ai_fit_score": 99, "rank": 1, "confidence": 0.9},
            {"influencer_id": "inf-macro", "ai_fit_score": 80, "rank": 2, "confidence": 0.8},
            {"influencer_id": "inf-celeb", "ai_fit_score": 85, "rank": 3, "confidence": 0.8},
        ]
    )
    context = {
        "candidate_ids": ["inf-micro", "inf-macro", "inf-celeb"],
        "candidates": [
            {"influencer_id": "inf-micro", "followers": 50000, "platform": "youtube", "deterministic_match_score": 90},
            {"influencer_id": "inf-macro", "followers": 700000, "platform": "youtube", "deterministic_match_score": 70},
            {"influencer_id": "inf-celeb", "followers": 2_500_000, "platform": "youtube", "deterministic_match_score": 70},
        ],
    }
    validated = await agent.validate_output(ctx, result, context)
    ids = [r["influencer_id"] for r in validated.recommendations]
    assert "inf-micro" not in ids
    assert set(ids) == {"inf-macro", "inf-celeb"}


@pytest.mark.asyncio
async def test_micro_plus_macro_excludes_mid_gap():
    agent = DiscoveryAgent()
    camp = _campaign(creator_tiers=["micro", "macro"])
    ctx = _ctx(camp)
    result = _envelope(
        [
            {"influencer_id": "inf-micro", "ai_fit_score": 80, "rank": 1, "confidence": 0.8},
            {"influencer_id": "inf-mid", "ai_fit_score": 99, "rank": 2, "confidence": 0.9},
            {"influencer_id": "inf-macro", "ai_fit_score": 85, "rank": 3, "confidence": 0.8},
        ]
    )
    context = {
        "candidate_ids": ["inf-micro", "inf-mid", "inf-macro"],
        "candidates": [
            {"influencer_id": "inf-micro", "followers": 40000, "platform": "youtube", "deterministic_match_score": 70},
            {"influencer_id": "inf-mid", "followers": 200000, "platform": "youtube", "deterministic_match_score": 70},
            {"influencer_id": "inf-macro", "followers": 700000, "platform": "youtube", "deterministic_match_score": 70},
        ],
    }
    validated = await agent.validate_output(ctx, result, context)
    ids = [r["influencer_id"] for r in validated.recommendations]
    assert "inf-mid" not in ids
    assert set(ids) == {"inf-micro", "inf-macro"}


def test_user_selected_tiers_outrank_strategy_micro():
    reqs = build_discovery_requirements(
        _campaign(creator_tiers=["macro", "celebrity"], min_followers=10000, max_followers=500000),
        {
            "creator_strategy": {
                "preferred_creator_tiers": [{"tier": "micro"}],
                "recommended_subscriber_range": {"minimum": 10000, "maximum": 100000},
            }
        },
    )
    assert reqs.hard_creator_tiers == ["macro", "celebrity"]
    assert reqs.hard_subscriber_ok(75000) is False
    assert reqs.hard_subscriber_ok(700000) is True
    assert reqs.hard_subscriber_ok(2_500_000) is True
    assert reqs.preferred_creator_tiers == ["macro", "celebrity"]


@pytest.mark.asyncio
async def test_youtube_healthcheck_reports_missing_key():
    from app.integrations.youtube.client import YouTubeClient

    client = YouTubeClient(api_key="x")
    result = await client.healthcheck()
    assert result["ok"] is False
    assert result["error"] == "INVALID_API_KEY"
    assert "AIza" not in json.dumps(result)


@pytest.mark.asyncio
async def test_grok_cannot_override_missing_niche_evidence():
    agent = DiscoveryAgent()
    camp = _campaign(
        name="Smartphone Launch",
        interests=["Technology"],
        keywords=["smartphone"],
        creator_tiers=["macro"],
        min_followers=None,
        max_followers=None,
    )
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-game",
                "ai_fit_score": 95,
                "rank": 1,
                "confidence": 0.95,
                "classification": {"niche_match": "HIGH", "content_relevance": "HIGH"},
            },
            {
                "influencer_id": "inf-phone",
                "ai_fit_score": 70,
                "rank": 2,
                "confidence": 0.8,
                "classification": {"niche_match": "MEDIUM", "content_relevance": "HIGH"},
            },
        ]
    )
    context = {
        "candidate_ids": ["inf-game", "inf-phone"],
        "candidates": [
            {
                "influencer_id": "inf-game",
                "followers": 720000,
                "platform": "youtube",
                "deterministic_match_score": 55,
                "niche_keyword_hit": False,
                "engagement_rate": 4.0,
            },
            {
                "influencer_id": "inf-phone",
                "followers": 700000,
                "platform": "youtube",
                "deterministic_match_score": 82,
                "niche_keyword_hit": True,
                "engagement_rate": 3.5,
            },
        ],
    }
    validated = await agent.validate_output(ctx, result, context)
    ids = [r["influencer_id"] for r in validated.recommendations]
    assert ids == ["inf-phone"]
    assert validated.recommendations[0]["requirement_match"]["niche"] == "MATCH"
    assert validated.recommendations[0]["eligibility"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_macro_90k_is_not_eligible_even_with_high_ai_fit():
    agent = DiscoveryAgent()
    camp = _campaign(creator_tiers=["macro"], min_followers=None, max_followers=None)
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-micro",
                "ai_fit_score": 95,
                "rank": 1,
                "confidence": 0.95,
                "classification": {"niche_match": "HIGH"},
            },
        ]
    )
    context = {
        "candidate_ids": ["inf-micro"],
        "candidates": [
            {
                "influencer_id": "inf-micro",
                "followers": 90000,
                "platform": "youtube",
                "deterministic_match_score": 90,
                "niche_keyword_hit": True,
            },
        ],
    }
    with pytest.raises(AgentValidationException):
        await agent.validate_output(ctx, result, context)
