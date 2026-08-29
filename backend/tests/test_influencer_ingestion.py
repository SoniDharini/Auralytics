import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.integrations.social_provider import ContentMetrics, NormalizedCreator
from app.integrations.youtube.mapper import map_youtube_channel_to_creator, sanitize_https_media_url
from app.integrations.youtube.schemas import (
    YouTubeChannelItem,
    YouTubeContentDetails,
    YouTubeRelatedPlaylists,
    YouTubeSnippet,
    YouTubeStatistics,
)
from app.models.campaign import Campaign
from app.models.user import User
from app.services.query_builder import CampaignQueryBuilder


@pytest.mark.asyncio
async def test_campaign_query_builder():
    """Test that CampaignQueryBuilder constructs high-affinity search queries from campaign brief."""
    campaign = Campaign(
        id="camp-test-1",
        owner_id=uuid.uuid4(),
        name="HydraGlow Monsoon Launch",
        brand="GlowNaturals",
        objective="Conversions",
        target_locations="India, Mumbai",
        interests=["Skincare", "Clean Beauty", "Dermatology"],
    )

    queries = CampaignQueryBuilder.build_queries(campaign)
    assert len(queries) > 0
    assert any("Skincare India" in q for q in queries)
    assert any("Clean Beauty India" in q for q in queries)


@pytest.mark.asyncio
async def test_campaign_query_builder_uses_saved_strategy_niches():
    """Discovery search terms must come from persisted strategy when the brief is thin."""
    campaign = Campaign(
        id="camp-test-strategy-1",
        owner_id=uuid.uuid4(),
        name="Launch",
        brand="Acme Tech",
        objective="Awareness",
        target_locations="India",
        keywords=[],
        interests=[],
        campaign_types=[],
    )
    strategy = {
        "creator_strategy": {
            "preferred_niches": ["Technology", "Gadgets"],
            "preferred_locations": ["India"],
        },
        "discovery_priorities": [
            {"factor": "Niche match", "priority": 1},
            {"factor": "Audience alignment", "priority": 2},
        ],
    }

    queries = CampaignQueryBuilder.build_queries(campaign, strategy=strategy)
    assert any("Technology" in q for q in queries)
    assert any("Gadgets" in q for q in queries)
    assert all("Niche match" not in q for q in queries)


@pytest.mark.asyncio
async def test_youtube_mapper_metric_calculations():
    """Test that YouTube channel mapping calculates derived metrics correctly and leaves missing fields as None."""
    channel = YouTubeChannelItem(
        id="UC_test_channel_123",
        snippet=YouTubeSnippet(
            title="Dr. Shalini Skin Clinic",
            description="Expert dermatology and skincare routines.",
            customUrl="@shaliniderm",
            country="IN",
            thumbnails={"high": {"url": "https://img.youtube.com/thumb.jpg"}},
        ),
        statistics=YouTubeStatistics(
            subscriberCount="100000",
            viewCount="5000000",
            videoCount="50",
            hiddenSubscriberCount=False,
        ),
    )

    sample_videos = [
        {"view_count": 20000, "like_count": 1000, "comment_count": 100},
        {"view_count": 30000, "like_count": 1400, "comment_count": 140},
    ]

    norm = map_youtube_channel_to_creator(channel, video_stats=sample_videos)

    assert norm.external_id == "UC_test_channel_123"
    assert norm.platform == "youtube"
    assert norm.username == "@shaliniderm"
    assert norm.name == "Dr. Shalini Skin Clinic"
    assert norm.followers == 100000
    assert norm.avg_views == 25000
    assert norm.avg_likes == 1200
    assert norm.avg_comments == 120
    # engagement_rate = ((1200 + 120) / 100000) * 100 = 1.32%
    assert norm.engagement_rate == 1.32
    assert norm.profile_url == "https://www.youtube.com/@shaliniderm"
    assert norm.avatar == "https://img.youtube.com/thumb.jpg"
    assert norm.thumbnail_url == "https://img.youtube.com/thumb.jpg"


def test_sanitize_https_media_url_strips_malformed_prefixes():
    assert sanitize_https_media_url("https://yt3.ggpht.com/abc.jpg") == "https://yt3.ggpht.com/abc.jpg"
    assert sanitize_https_media_url("https://https://yt3.ggpht.com/abc.jpg") == "https://yt3.ggpht.com/abc.jpg"
    assert (
        sanitize_https_media_url("https://localhost:8000/https://yt3.ggpht.com/abc.jpg")
        == "https://yt3.ggpht.com/abc.jpg"
    )
    assert sanitize_https_media_url("http://yt3.ggpht.com/abc.jpg") is None
    assert sanitize_https_media_url("https://localhost/photo.jpg") is None
    assert sanitize_https_media_url("") is None


def test_invalid_thumbnail_does_not_drop_creator():
    channel = YouTubeChannelItem(
        id="UC_bad_thumb",
        snippet=YouTubeSnippet(
            title="Phone Reviews India",
            description="Smartphone comparisons",
            customUrl="@phones",
            country="IN",
            thumbnails={"high": {"url": "not-a-valid-url"}},
        ),
        statistics=YouTubeStatistics(
            subscriberCount="700000",
            viewCount="1000000",
            videoCount="40",
            hiddenSubscriberCount=False,
        ),
    )
    norm = map_youtube_channel_to_creator(channel)
    assert norm.name == "Phone Reviews India"
    assert norm.followers == 700000
    assert norm.avatar is None
    assert norm.thumbnail_url is None


@pytest.mark.asyncio
async def test_integrations_status_endpoint(client):
    """Test that /api/v1/integrations/status returns provider health without exposing secrets."""
    # Register and login a test user
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Ingestion User",
            "email": "ingestion@test.com",
            "password": "Password123!",
        },
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get("/api/v1/integrations/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "youtube" in data
    assert "configured" in data["youtube"]
    assert "instagram" in data
    assert "configured" in data["instagram"]
    # Secrets should not be present
    assert "api_key" not in str(data).lower()
    assert "access_token" not in str(data).lower()


@pytest.mark.asyncio
async def test_influencer_fetch_for_campaign(client):
    """Test the campaign fetch-influencers endpoint with mock-free ingestion flow."""
    # 1. Register & Login
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Discovery Tester",
            "email": "discovery_tester@test.com",
            "password": "Password123!",
        },
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Campaign
    camp_res = await client.post(
        "/api/v1/campaigns",
        headers=headers,
        json={
            "name": "Summer Glow Campaign",
            "brand": "GlowNaturals",
            "budget": 150000,
            "objective": "Product Launch",
            "start_date": "2026-08-20",
            "end_date": "2026-09-20",
            "target_locations": "India",
            "interests": ["Skincare", "Clean Beauty"],
            "platforms": ["youtube"],
        },
    )
    assert camp_res.status_code == 201
    camp_id = camp_res.json()["id"]

    # 3. Mock the YouTube provider stages to simulate live API results deterministically
    mock_channel = YouTubeChannelItem(
        id="UC_live_creator_999",
        snippet=YouTubeSnippet(
            title="Live Glow Reviews",
            description="Authentic skincare testing and clean beauty ingredient reviews.",
            customUrl="@live_glow_creator",
            country="IN",
            thumbnails={"high": {"url": "https://img.youtube.com/avatar.jpg"}},
        ),
        statistics=YouTubeStatistics(
            subscriberCount="85000",
            viewCount="3500000",
            videoCount="42",
            hiddenSubscriberCount=False,
        ),
        contentDetails=YouTubeContentDetails(
            relatedPlaylists=YouTubeRelatedPlaylists(uploads="UU_live_creator_999")
        ),
    )

    provider_path = "app.services.creator_discovery_service.YouTubeProvider"
    with patch(f"{provider_path}.is_configured", return_value=True), \
         patch(f"{provider_path}.search_channel_candidates", new_callable=AsyncMock) as mock_search, \
         patch(f"{provider_path}.fetch_channels", new_callable=AsyncMock) as mock_channels, \
         patch(f"{provider_path}.fetch_recent_video_stats", new_callable=AsyncMock) as mock_videos:
        mock_search.return_value = {"UC_live_creator_999": "Skincare India"}
        mock_channels.return_value = [mock_channel]
        mock_videos.return_value = [
            {"view_count": 30000, "like_count": 2000, "comment_count": 180, "published_at": "2026-08-01T10:00:00Z"},
        ]

        fetch_res = await client.post(
            f"/api/v1/campaigns/{camp_id}/fetch-influencers",
            headers=headers,
            json={"limit": 10, "force_refresh": True},
        )
        assert fetch_res.status_code == 200
        fetch_data = fetch_res.json()

        assert fetch_data["status"] == "completed"
        assert fetch_data["total_discovered"] == 1
        assert fetch_data["providers"]["youtube"]["fetched"] == 1
        assert fetch_data["providers"]["youtube"]["created"] == 1

    # 4. Verify Influencer exists in DB list
    inf_res = await client.get("/api/v1/influencers", headers=headers)
    assert inf_res.status_code == 200
    influencers = inf_res.json()
    assert len(influencers) >= 1
    found = next((i for i in influencers if i["external_id"] == "UC_live_creator_999"), None)
    assert found is not None
    assert found.get("estimated_cost") is None or found.get("estimatedCost") is None  # Unprovided values MUST be None

    # 5. Verify Campaign Activities logged the discovery event
    act_res = await client.get(f"/api/v1/campaigns/{camp_id}/activities", headers=headers)
    assert act_res.status_code == 200
    activities = act_res.json()
    activity_types = [a["activity_type"] for a in activities]
    assert "INFLUENCER_FETCH_STARTED" in activity_types
    assert "INFLUENCER_FETCH_COMPLETED" in activity_types

    # 6. Verify Toggle Shortlist
    short_res = await client.post(f"/api/v1/influencers/{found['id']}/shortlist", headers=headers)
    assert short_res.status_code == 200
    assert short_res.json()["shortlisted"] is True
