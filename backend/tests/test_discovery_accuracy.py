"""Discovery Agent requirement handling: hard user constraints vs Strategy preferences."""

from __future__ import annotations

from types import SimpleNamespace

import json
import pytest

from app.ai.agents.base import AgentContext
from app.ai.agents.discovery import DiscoveryAgent
from app.ai.audience_profile import PERSONA_ADULT, PERSONA_GEN_Z, build_audience_profile
from app.ai.creator_entity import (
    COMPANY,
    INDIVIDUAL_CREATOR,
    MUSIC_LABEL,
    SHOW,
    TEAM_CREATOR_CHANNEL,
    classify_creator_entity,
)
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
    assert "NO_STRONG_MATCHES" in str(exc.value.detail) or "hard" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_missing_location_is_not_a_primary_recommendation():
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
    with pytest.raises(AgentValidationException):
        await agent.validate_output(ctx, result, context)


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
        description="Only smartphone influencers",
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


def _genz_soft_drink(**kwargs):
    defaults = dict(
        name="Soft Drink Launch",
        objective="Awareness",
        description="Fun mass-consumer drink for youth, college events and entertainment. Gen Z.",
        interests=["Lifestyle"],
        keywords=["soft drink"],
        creator_tiers=["macro"],
        min_followers=500000,
        max_followers=1000000,
        target_locations="India",
        target_age_min=18,
        target_age_max=24,
        campaign_types=["Awareness"],
    )
    defaults.update(kwargs)
    return _campaign(**defaults)


def _yt_candidate(influencer_id: str, **kwargs):
    row = {
        "influencer_id": influencer_id,
        "platform": "youtube",
        "followers": 720000,
        "country": "IN",
        "location": "India",
        "deterministic_match_score": 70,
        "creator_entity_type": INDIVIDUAL_CREATOR,
        "rural_mismatch": 0,
        "avg_views": 400000,
        "recent_avg_views": 400000,
        "metrics_sample_size": 8,
        "engagement_rate": 3.5,
        "recent_momentum": "HIGH",
    }
    row.update(kwargs)
    if "recent_avg_views" not in kwargs and "avg_views" in kwargs:
        row["recent_avg_views"] = row.get("avg_views")
    return row


def test_audience_profile_named_genz_wins_default_youth_copy():
    profile = build_audience_profile(
        description="Gen Z college audience for a fun soft drink",
        target_age_min=22,
        target_age_max=34,
    )
    assert profile.persona == PERSONA_GEN_Z


def test_audience_profile_explicit_adult_age_outranks_genz_term():
    profile = build_audience_profile(
        description="Mentions Gen Z once",
        target_age_min=35,
        target_age_max=50,
    )
    assert profile.persona == PERSONA_ADULT


def test_entity_classifier_rejects_company_show_and_label_without_name_blacklist():
    company, _ = classify_creator_entity(
        name="Harvest Kitchen Media",
        description="Official brand channel of Harvest Foods Pvt Ltd. This corporation publishes product films.",
    )
    show, _ = classify_creator_entity(
        name="Boardroom Pitch",
        description="Watch full episodes of this television show. Reality show recaps every week.",
    )
    label, _ = classify_creator_entity(
        name="National Beats",
        description="Official music label. Record label releasing film songs.",
    )
    person, _ = classify_creator_entity(
        name="Aarav Comedy",
        description="I am a comedy creator. Subscribe to me for daily vlogs.",
        recent_titles=["College roast", "Meme review"],
    )
    assert company == COMPANY
    assert show == SHOW
    assert label == MUSIC_LABEL
    assert person == INDIVIDUAL_CREATOR


def test_query_builder_adds_persona_pool_for_genz():
    campaign = Campaign(
        id="camp-q-genz",
        owner_id=__import__("uuid").uuid4(),
        name="Soft Drink Launch",
        brand="Fizz",
        objective="Awareness",
        target_locations="India",
        interests=["Lifestyle"],
        keywords=["soft drink"],
        description="Fun mass-consumer drink for youth, college events and entertainment. Gen Z.",
        target_age_min=18,
        target_age_max=24,
    )
    queries = CampaignQueryBuilder.build_queries(campaign, max_queries=4)
    blob = " ".join(queries).lower()
    assert any("soft drink" in q.lower() for q in queries)
    assert "india" in blob
    assert any(token in blob for token in ("youth", "entertainment", "comedy", "gaming", "lifestyle"))


@pytest.mark.asyncio
async def test_genz_macro_india_keeps_individual_creators_only():
    agent = DiscoveryAgent()
    camp = _genz_soft_drink()
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-org",
                "ai_fit_score": 99,
                "eligibility": "ELIGIBLE",
                "creator_entity_type": COMPANY,
                "persona_relevance": {"level": "HIGH"},
            },
            {
                "influencer_id": "inf-good",
                "ai_fit_score": 82,
                "eligibility": "ELIGIBLE",
                "creator_entity_type": INDIVIDUAL_CREATOR,
                "collaboration_suitability": "HIGH",
                "persona_relevance": {"level": "HIGH", "reason": "Youth entertainment"},
                "classification": {
                    "gen_z_relevance": "HIGH",
                    "trend_relevance": "HIGH",
                    "product_relevance": "MEDIUM",
                },
            },
        ]
    )
    context = {
        "candidate_ids": ["inf-org", "inf-good"],
        "candidates": [
            _yt_candidate("inf-org", followers=800000, creator_entity_type=COMPANY),
            _yt_candidate("inf-good", followers=650000, avg_views=430000),
        ],
    }
    validated = await agent.validate_output(ctx, result, context)
    ids = [r["influencer_id"] for r in validated.recommendations]
    assert ids == ["inf-good"]
    rec = validated.recommendations[0]
    assert rec["creator_entity_type"] == INDIVIDUAL_CREATOR
    assert rec["requirement_match"]["location"] == "MATCH"
    assert rec["persona_relevance"]["target"] == PERSONA_GEN_Z
    assert rec["persona_relevance"]["source"] == "AI_INFERRED"
    assert rec["eligibility"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_company_channel_is_not_eligible():
    agent = DiscoveryAgent()
    camp = _genz_soft_drink()
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-co",
                "ai_fit_score": 99,
                "eligibility": "ELIGIBLE",
                "creator_entity_type": COMPANY,
            }
        ]
    )
    context = {
        "candidate_ids": ["inf-co"],
        "candidates": [_yt_candidate("inf-co", followers=800000, creator_entity_type=COMPANY)],
    }
    with pytest.raises(AgentValidationException) as exc:
        await agent.validate_output(ctx, result, context)
    assert "NO_STRONG_MATCHES" in str(exc.value.detail) or "hard" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_show_channel_is_not_eligible():
    agent = DiscoveryAgent()
    camp = _genz_soft_drink()
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-show",
                "ai_fit_score": 97,
                "eligibility": "ELIGIBLE",
                "creator_entity_type": SHOW,
            }
        ]
    )
    context = {
        "candidate_ids": ["inf-show"],
        "candidates": [_yt_candidate("inf-show", followers=700000, creator_entity_type=SHOW)],
    }
    with pytest.raises(AgentValidationException):
        await agent.validate_output(ctx, result, context)


@pytest.mark.asyncio
async def test_music_label_channel_is_not_eligible():
    agent = DiscoveryAgent()
    camp = _genz_soft_drink()
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-label",
                "ai_fit_score": 98,
                "eligibility": "ELIGIBLE",
                "creator_entity_type": MUSIC_LABEL,
            }
        ]
    )
    context = {
        "candidate_ids": ["inf-label"],
        "candidates": [_yt_candidate("inf-label", followers=900000, creator_entity_type=MUSIC_LABEL)],
    }
    with pytest.raises(AgentValidationException):
        await agent.validate_output(ctx, result, context)


@pytest.mark.asyncio
async def test_us_creator_not_eligible_for_india_only():
    agent = DiscoveryAgent()
    camp = _genz_soft_drink()
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-us",
                "ai_fit_score": 95,
                "eligibility": "ELIGIBLE",
                "creator_entity_type": INDIVIDUAL_CREATOR,
            }
        ]
    )
    context = {
        "candidate_ids": ["inf-us"],
        "candidates": [_yt_candidate("inf-us", followers=800000, country="US", location="United States")],
    }
    with pytest.raises(AgentValidationException):
        await agent.validate_output(ctx, result, context)


@pytest.mark.asyncio
async def test_follower_range_not_overridden_by_trend():
    agent = DiscoveryAgent()
    camp = _genz_soft_drink()
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-huge",
                "ai_fit_score": 99,
                "eligibility": "ELIGIBLE",
                "classification": {"trend_relevance": "HIGH", "gen_z_relevance": "HIGH"},
            }
        ]
    )
    context = {
        "candidate_ids": ["inf-huge"],
        "candidates": [
            _yt_candidate("inf-huge", followers=2_000_000, avg_views=5_000_000, recent_momentum="HIGH")
        ],
    }
    with pytest.raises(AgentValidationException):
        await agent.validate_output(ctx, result, context)


@pytest.mark.asyncio
async def test_genz_rural_traditional_creator_is_not_recommended():
    agent = DiscoveryAgent()
    camp = _genz_soft_drink()
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-rural",
                "ai_fit_score": 88,
                "eligibility": "ELIGIBLE",
                "persona_relevance": {"level": "LOW"},
                "classification": {"gen_z_relevance": "LOW", "product_relevance": "HIGH"},
            },
            {
                "influencer_id": "inf-youth",
                "ai_fit_score": 80,
                "eligibility": "ELIGIBLE",
                "collaboration_suitability": "HIGH",
                "persona_relevance": {"level": "HIGH"},
                "classification": {"gen_z_relevance": "HIGH", "trend_relevance": "HIGH", "product_relevance": "LOW"},
            },
        ]
    )
    context = {
        "candidate_ids": ["inf-rural", "inf-youth"],
        "candidates": [
            _yt_candidate(
                "inf-rural",
                followers=700000,
                avg_views=80000,
                rural_mismatch=3,
                recent_momentum="LOW",
            ),
            _yt_candidate("inf-youth", followers=650000, avg_views=450000, recent_momentum="HIGH"),
        ],
    }
    validated = await agent.validate_output(ctx, result, context)
    ids = [r["influencer_id"] for r in validated.recommendations]
    assert "inf-rural" not in ids
    assert ids[0] == "inf-youth"


@pytest.mark.asyncio
async def test_rural_creator_kept_when_campaign_targets_rural_audience():
    agent = DiscoveryAgent()
    camp = _genz_soft_drink(
        description="Rural agriculture and village lifestyle campaign for farming families.",
        interests=["Agriculture"],
        keywords=["farming"],
        target_age_min=18,
        target_age_max=24,
    )
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-farm",
                "ai_fit_score": 90,
                "eligibility": "ELIGIBLE",
                "persona_relevance": {"level": "HIGH"},
            }
        ]
    )
    context = {
        "candidate_ids": ["inf-farm"],
        "candidates": [_yt_candidate("inf-farm", rural_mismatch=3, avg_views=120000)],
    }
    validated = await agent.validate_output(ctx, result, context)
    assert [r["influencer_id"] for r in validated.recommendations] == ["inf-farm"]


@pytest.mark.asyncio
async def test_good_genz_entertainment_creator_is_high():
    agent = DiscoveryAgent()
    camp = _genz_soft_drink()
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-ent",
                "ai_fit_score": 94,
                "eligibility": "ELIGIBLE",
                "collaboration_suitability": "HIGH",
                "persona_relevance": {"level": "HIGH", "reason": "Comedy and campus culture"},
                "classification": {
                    "gen_z_relevance": "HIGH",
                    "trend_relevance": "HIGH",
                    "cultural_relevance": "HIGH",
                    "product_relevance": "MEDIUM",
                },
            }
        ]
    )
    context = {
        "candidate_ids": ["inf-ent"],
        "candidates": [_yt_candidate("inf-ent", followers=650000, avg_views=430000, recent_momentum="HIGH")],
    }
    validated = await agent.validate_output(ctx, result, context)
    rec = validated.recommendations[0]
    assert rec["eligibility"] == "ELIGIBLE"
    assert rec["persona_relevance"]["level"] == "HIGH"
    assert rec["recommendation_type"] == "TRENDING_PERSONA_MATCH"
    assert "82%" not in (rec["persona_relevance"]["reason"] or "")


@pytest.mark.asyncio
async def test_adult_campaign_ranks_adult_creator_above_youth_viral():
    agent = DiscoveryAgent()
    camp = _campaign(
        name="Financial Product",
        objective="Conversions",
        description="Working professionals and parents aged 35-50 looking for practical finance advice.",
        interests=["Finance"],
        keywords=["finance"],
        creator_tiers=["mid", "mid-tier"],
        min_followers=100000,
        max_followers=500000,
        target_locations="India",
        target_age_min=35,
        target_age_max=50,
    )
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-comedy",
                "ai_fit_score": 96,
                "eligibility": "ELIGIBLE",
                "collaboration_suitability": "HIGH",
                "persona_relevance": {"level": "LOW"},
                "classification": {
                    "adult_relevance": "LOW",
                    "gen_z_relevance": "HIGH",
                    "trend_relevance": "HIGH",
                    "product_relevance": "LOW",
                    "campaign_objective_fit": "LOW",
                },
            },
            {
                "influencer_id": "inf-finance",
                "ai_fit_score": 78,
                "eligibility": "ELIGIBLE",
                "collaboration_suitability": "HIGH",
                "persona_relevance": {"level": "HIGH"},
                "classification": {
                    "adult_relevance": "HIGH",
                    "trend_relevance": "MEDIUM",
                    "product_relevance": "HIGH",
                    "campaign_objective_fit": "HIGH",
                },
            },
        ]
    )
    context = {
        "candidate_ids": ["inf-comedy", "inf-finance"],
        "candidates": [
            _yt_candidate(
                "inf-comedy",
                followers=300000,
                avg_views=900000,
                recent_momentum="HIGH",
            ),
            _yt_candidate(
                "inf-finance",
                followers=250000,
                avg_views=80000,
                recent_momentum="MEDIUM",
                niche_keyword_hit=True,
            ),
        ],
    }
    validated = await agent.validate_output(ctx, result, context)
    ids = [r["influencer_id"] for r in validated.recommendations]
    assert ids[0] == "inf-finance"
    assert "inf-comedy" in ids
    assert validated.recommendations[0]["persona_relevance"]["target"] == PERSONA_ADULT


@pytest.mark.asyncio
async def test_awareness_does_not_drop_persona_match_without_product_keyword():
    agent = DiscoveryAgent()
    camp = _genz_soft_drink()
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-game",
                "ai_fit_score": 90,
                "eligibility": "ELIGIBLE",
                "collaboration_suitability": "HIGH",
                "persona_relevance": {"level": "HIGH"},
                "classification": {"gen_z_relevance": "HIGH", "product_relevance": "LOW", "trend_relevance": "HIGH"},
            }
        ]
    )
    context = {
        "candidate_ids": ["inf-game"],
        "candidates": [
            _yt_candidate("inf-game", followers=680000, niche_keyword_hit=False, avg_views=500000)
        ],
    }
    validated = await agent.validate_output(ctx, result, context)
    assert [r["influencer_id"] for r in validated.recommendations] == ["inf-game"]


@pytest.mark.asyncio
async def test_fabricated_demographic_percentages_are_stripped():
    agent = DiscoveryAgent()
    camp = _genz_soft_drink()
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-ent",
                "ai_fit_score": 90,
                "eligibility": "ELIGIBLE",
                "persona_relevance": {
                    "level": "HIGH",
                    "reason": "82% of viewers are Gen Z based on guesswork",
                },
            }
        ]
    )
    context = {
        "candidate_ids": ["inf-ent"],
        "candidates": [_yt_candidate("inf-ent")],
    }
    validated = await agent.validate_output(ctx, result, context)
    reason = validated.recommendations[0]["persona_relevance"]["reason"]
    assert "82%" not in reason
    assert validated.recommendations[0]["persona_relevance"]["source"] == "AI_INFERRED"


def test_exclusive_niche_and_view_requirement_are_parsed_from_copy():
    reqs = build_discovery_requirements(
        _campaign(
            description="Only fitness influencers. Minimum recent views 300K. Gen Z.",
            keywords=["protein"],
            interests=["Fitness"],
        ),
        {},
    )
    assert reqs.explicit_niche_required is True
    assert reqs.hard_niches == ["fitness"]
    assert reqs.hard_recent_views_min == 300000
    assert reqs.product_terms == ["Fitness"]


def test_strategy_view_preference_is_not_hard():
    reqs = build_discovery_requirements(
        _campaign(description="Youth lifestyle campaign"),
        {"creator_strategy": {"preferred_min_avg_views": 250000}},
    )
    assert reqs.hard_recent_views_min is None
    assert reqs.preferred_recent_views_min == 250000
    assert reqs.hard_views_ok(80000) is True
    assert reqs.view_match_label(80000) == "PARTIAL"


def test_team_food_channel_is_classified_without_name_blacklist():
    entity, hits = classify_creator_entity(
        name="Village Kitchen Daily",
        description="Our team of chefs runs this recipe network. New recipes from our kitchen team every day.",
        recent_titles=["Team recipe 1", "Team recipe 2"],
    )
    assert entity == TEAM_CREATOR_CHANNEL
    assert hits >= 1


@pytest.mark.asyncio
async def test_team_creator_channel_is_not_eligible():
    agent = DiscoveryAgent()
    camp = _genz_soft_drink()
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-team",
                "ai_fit_score": 99,
                "eligibility": "ELIGIBLE",
                "creator_entity_type": TEAM_CREATOR_CHANNEL,
            }
        ]
    )
    context = {
        "candidate_ids": ["inf-team"],
        "candidates": [
            _yt_candidate("inf-team", followers=800000, creator_entity_type=TEAM_CREATOR_CHANNEL)
        ],
    }
    with pytest.raises(AgentValidationException):
        await agent.validate_output(ctx, result, context)


@pytest.mark.asyncio
async def test_hard_view_requirement_excludes_low_recent_views():
    agent = DiscoveryAgent()
    camp = _genz_soft_drink(
        description="Fun mass-consumer drink for youth. Gen Z. Minimum recent views 300K",
    )
    ctx = _ctx(camp)
    result = _envelope(
        [
            {"influencer_id": "inf-low-views", "ai_fit_score": 99, "eligibility": "ELIGIBLE"},
            {
                "influencer_id": "inf-high-views",
                "ai_fit_score": 80,
                "eligibility": "ELIGIBLE",
                "persona_relevance": {"level": "HIGH"},
            },
        ]
    )
    context = {
        "candidate_ids": ["inf-low-views", "inf-high-views"],
        "candidates": [
            _yt_candidate("inf-low-views", avg_views=80000, recent_avg_views=80000),
            _yt_candidate("inf-high-views", avg_views=450000, recent_avg_views=450000),
        ],
    }
    validated = await agent.validate_output(ctx, result, context)
    ids = [r["influencer_id"] for r in validated.recommendations]
    assert ids == ["inf-high-views"]
    assert validated.recommendations[0]["requirement_match"]["view_requirement"] == "MATCH"


@pytest.mark.asyncio
async def test_genz_awareness_ranks_persona_over_product_category():
    agent = DiscoveryAgent()
    camp = _genz_soft_drink()
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-food",
                "ai_fit_score": 92,
                "eligibility": "ELIGIBLE",
                "collaboration_suitability": "HIGH",
                "persona_relevance": {"level": "LOW"},
                "classification": {
                    "gen_z_relevance": "LOW",
                    "product_relevance": "HIGH",
                    "trend_relevance": "LOW",
                },
            },
            {
                "influencer_id": "inf-ent",
                "ai_fit_score": 78,
                "eligibility": "ELIGIBLE",
                "collaboration_suitability": "HIGH",
                "persona_relevance": {"level": "HIGH"},
                "classification": {
                    "gen_z_relevance": "HIGH",
                    "product_relevance": "LOW",
                    "trend_relevance": "HIGH",
                    "cultural_relevance": "HIGH",
                },
            },
        ]
    )
    context = {
        "candidate_ids": ["inf-food", "inf-ent"],
        "candidates": [
            _yt_candidate("inf-food", avg_views=40000, recent_avg_views=40000, recent_momentum="LOW"),
            _yt_candidate("inf-ent", avg_views=450000, recent_avg_views=450000, recent_momentum="HIGH"),
        ],
    }
    validated = await agent.validate_output(ctx, result, context)
    ids = [r["influencer_id"] for r in validated.recommendations]
    assert ids[0] == "inf-ent"


@pytest.mark.asyncio
async def test_explicit_fitness_niche_excludes_unrelated_creators():
    agent = DiscoveryAgent()
    camp = _campaign(
        name="Fitness Launch",
        description="Only fitness influencers. Adults 35-50.",
        objective="Conversions",
        interests=["Fitness"],
        keywords=["fitness"],
        creator_tiers=["mid-tier"],
        min_followers=100000,
        max_followers=500000,
        target_locations="India",
        target_age_min=35,
        target_age_max=50,
    )
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-comedy",
                "ai_fit_score": 99,
                "eligibility": "ELIGIBLE",
                "classification": {"niche_match": "HIGH"},
            },
            {
                "influencer_id": "inf-fit",
                "ai_fit_score": 70,
                "eligibility": "ELIGIBLE",
                "classification": {"niche_match": "HIGH"},
            },
        ]
    )
    context = {
        "candidate_ids": ["inf-comedy", "inf-fit"],
        "candidates": [
            _yt_candidate(
                "inf-comedy",
                followers=300000,
                niche_keyword_hit=False,
            ),
            _yt_candidate(
                "inf-fit",
                followers=280000,
                niche_keyword_hit=True,
            ),
        ],
    }
    validated = await agent.validate_output(ctx, result, context)
    assert [r["influencer_id"] for r in validated.recommendations] == ["inf-fit"]


@pytest.mark.asyncio
async def test_missing_metrics_are_insufficient_data_not_ranked():
    agent = DiscoveryAgent()
    camp = _genz_soft_drink()
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-na",
                "ai_fit_score": 91,
                "eligibility": "ELIGIBLE",
                "persona_relevance": {"level": "HIGH"},
            }
        ]
    )
    context = {
        "candidate_ids": ["inf-na"],
        "candidates": [
            _yt_candidate(
                "inf-na",
                followers=0,
                avg_views=0,
                recent_avg_views=0,
                metrics_sample_size=0,
                name="Village Vibe",
            )
        ],
    }
    with pytest.raises(AgentValidationException) as exc:
        await agent.validate_output(ctx, result, context)
    assert "NO_STRONG_MATCHES" in str(exc.value.detail)


def test_team_cooking_property_is_not_name_blacklisted():
    entity, hits = classify_creator_entity(
        name="Sunrise Village Kitchen",
        description="Village kitchen recipes cooked by our community every day.",
        recent_titles=["Village recipe 12", "Community kitchen lunch"],
    )
    assert entity == TEAM_CREATOR_CHANNEL
    assert hits >= 1


@pytest.mark.asyncio
async def test_team_cooking_channel_excluded_even_with_huge_reach():
    agent = DiscoveryAgent()
    camp = _genz_soft_drink()
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-team-cook",
                "ai_fit_score": 99,
                "eligibility": "ELIGIBLE",
                "creator_entity_type": TEAM_CREATOR_CHANNEL,
                "persona_relevance": {"level": "HIGH"},
            }
        ]
    )
    context = {
        "candidate_ids": ["inf-team-cook"],
        "candidates": [
            _yt_candidate(
                "inf-team-cook",
                followers=30_000_000,
                avg_views=8_000_000,
                creator_entity_type=TEAM_CREATOR_CHANNEL,
            )
        ],
    }
    with pytest.raises(AgentValidationException):
        await agent.validate_output(ctx, result, context)


@pytest.mark.asyncio
async def test_awareness_ranks_current_views_over_larger_subscriber_count():
    agent = DiscoveryAgent()
    camp = _genz_soft_drink(
        creator_tiers=["celebrity"],
        min_followers=1_000_000,
        max_followers=None,
    )
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-stale",
                "ai_fit_score": 90,
                "eligibility": "ELIGIBLE",
                "collaboration_suitability": "HIGH",
                "persona_relevance": {"level": "HIGH"},
                "classification": {
                    "gen_z_relevance": "HIGH",
                    "trend_relevance": "LOW",
                    "cultural_relevance": "MEDIUM",
                    "product_relevance": "LOW",
                },
            },
            {
                "influencer_id": "inf-hot",
                "ai_fit_score": 78,
                "eligibility": "ELIGIBLE",
                "collaboration_suitability": "HIGH",
                "persona_relevance": {"level": "HIGH"},
                "classification": {
                    "gen_z_relevance": "HIGH",
                    "trend_relevance": "HIGH",
                    "cultural_relevance": "HIGH",
                    "product_relevance": "LOW",
                },
            },
        ]
    )
    context = {
        "candidate_ids": ["inf-stale", "inf-hot"],
        "candidates": [
            _yt_candidate(
                "inf-stale",
                followers=3_200_000,
                avg_views=41000,
                recent_avg_views=41000,
                recent_momentum="LOW",
                auralytics_trend_score=18,
            ),
            _yt_candidate(
                "inf-hot",
                followers=2_500_000,
                avg_views=700000,
                recent_avg_views=700000,
                recent_momentum="HIGH",
                auralytics_trend_score=82,
            ),
        ],
    }
    validated = await agent.validate_output(ctx, result, context)
    ids = [r["influencer_id"] for r in validated.recommendations]
    assert ids[0] == "inf-hot"
    assert "inf-stale" in ids
    assert validated.recommendations[0]["ranking_score"] > validated.recommendations[1]["ranking_score"]


@pytest.mark.asyncio
async def test_hard_follower_max_excludes_even_high_persona_match():
    agent = DiscoveryAgent()
    camp = _genz_soft_drink(
        creator_tiers=["celebrity"],
        min_followers=1_000_000,
        max_followers=5_000_000,
    )
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-over",
                "ai_fit_score": 99,
                "eligibility": "ELIGIBLE",
                "collaboration_suitability": "HIGH",
                "persona_relevance": {"level": "HIGH"},
                "classification": {"gen_z_relevance": "HIGH"},
            }
        ]
    )
    context = {
        "candidate_ids": ["inf-over"],
        "candidates": [
            _yt_candidate("inf-over", followers=9_600_000, avg_views=6_100_000)
        ],
    }
    with pytest.raises(AgentValidationException):
        await agent.validate_output(ctx, result, context)


@pytest.mark.asyncio
async def test_hard_min_views_500k_excludes_469k():
    agent = DiscoveryAgent()
    camp = _genz_soft_drink(
        description="Fun mass-consumer drink for youth. Gen Z. Minimum recent views 500K",
        creator_tiers=["celebrity"],
        min_followers=1_000_000,
        max_followers=None,
    )
    ctx = _ctx(camp)
    result = _envelope(
        [
            {
                "influencer_id": "inf-under",
                "ai_fit_score": 96,
                "eligibility": "ELIGIBLE",
                "collaboration_suitability": "HIGH",
                "persona_relevance": {"level": "HIGH"},
            }
        ]
    )
    context = {
        "candidate_ids": ["inf-under"],
        "candidates": [
            _yt_candidate(
                "inf-under",
                followers=3_200_000,
                avg_views=469000,
                recent_avg_views=469000,
            )
        ],
    }
    with pytest.raises(AgentValidationException):
        await agent.validate_output(ctx, result, context)
