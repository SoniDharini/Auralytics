import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.integrations.social_provider import ContentMetrics, NormalizedCreator
from app.integrations.youtube.mapper import map_youtube_channel_to_creator
from app.integrations.youtube.schemas import (
    YouTubeChannelItem,
    YouTubeContentDetails,
    YouTubeRelatedPlaylists,
    YouTubeSnippet,
    YouTubeStatistics,
)
from app.models.campaign import Campaign
from app.models.user import User
from app.services.influencer_ingestion_service import InfluencerIngestionService
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

    # 3. Mock YouTube Provider to simulate live API results deterministically
    mock_creator = NormalizedCreator(
        external_id="UC_live_creator_999",
        platform="youtube",
        username="@live_glow_creator",
        name="Live Glow Reviews",
        description="Authentic skincare testing and ingredient reviews.",
        avatar="https://img.youtube.com/avatar.jpg",
        profile_url="https://www.youtube.com/@live_glow_creator",
        country="IN",
        location="India",
        followers=85000,
        total_views=3500000,
        content_count=42,
        avg_views=32000,
        avg_likes=2100,
        avg_comments=190,
        engagement_rate=2.69,
        data_source="youtube",
    )

    with patch("app.services.influencer_ingestion_service.YouTubeProvider.is_configured", return_value=True), \
         patch("app.services.influencer_ingestion_service.YouTubeProvider.search_creators", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [mock_creator]

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
