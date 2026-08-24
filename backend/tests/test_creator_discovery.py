"""End-to-end coverage for campaign-scoped real creator discovery.

The YouTube HTTP client is mocked so the suite is deterministic and consumes no
API quota, but every assertion below exercises the real pipeline: query building,
deduplication, enrichment, filtering, scoring, persistence and shortlisting.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.youtube.client import YouTubeAPIError
from app.integrations.youtube.schemas import (
    YouTubeChannelItem,
    YouTubeContentDetails,
    YouTubeRelatedPlaylists,
    YouTubeSnippet,
    YouTubeStatistics,
)
from app.models.campaign import Campaign
from app.services.creator_scoring_service import CreatorScoringService, CreatorSignals

DISCOVERY_PATH = "app.services.creator_discovery_service.YouTubeProvider"


def make_channel(
    channel_id: str,
    title: str,
    description: str,
    subscribers: str = "82000",
    country: str = "IN",
    hidden: bool = False,
) -> YouTubeChannelItem:
    return YouTubeChannelItem(
        id=channel_id,
        snippet=YouTubeSnippet(
            title=title,
            description=description,
            customUrl=f"@{channel_id.lower()}",
            country=country,
            thumbnails={"high": {"url": f"https://yt3.ggpht.com/{channel_id}.jpg"}},
        ),
        statistics=YouTubeStatistics(
            subscriberCount=subscribers,
            viewCount="18000000",
            videoCount="248",
            hiddenSubscriberCount=hidden,
        ),
        contentDetails=YouTubeContentDetails(
            relatedPlaylists=YouTubeRelatedPlaylists(uploads=f"UU{channel_id[2:]}")
        ),
    )


def recent_videos(count: int = 5):
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


async def register(client, email: str) -> dict:
    res = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Discovery User", "email": email, "password": "Password123!"},
    )
    assert res.status_code == 201
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def create_fitness_campaign(client, headers) -> str:
    res = await client.post(
        "/api/v1/campaigns",
        headers=headers,
        json={
            "name": "Summer Fitness Launch",
            "brand": "PulseFit",
            "budget": 100000,
            "objective": "Product Launch",
            "start_date": "2026-09-01",
            "end_date": "2026-10-01",
            "target_locations": "India",
            "interests": ["Fitness"],
            "keywords": ["fitness", "gym", "workout", "nutrition"],
            "min_followers": 10000,
            "max_followers": 500000,
            "platforms": ["youtube"],
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


@pytest.mark.asyncio
async def test_discovery_persists_real_channels_with_derived_metrics(client):
    """Discovery calls YouTube, derives metrics and persists campaign-scoped records."""
    headers = await register(client, "discovery.happy@test.com")
    campaign_id = await create_fitness_campaign(client, headers)

    channels = [
        make_channel("UCfit001", "Fitness With Rahul", "Daily gym and workout routines from India."),
        make_channel("UCfit002", "Nutrition Kitchen", "Nutrition and healthy meal prep.", subscribers="120000"),
    ]

    with patch(f"{DISCOVERY_PATH}.is_configured", return_value=True), patch(
        f"{DISCOVERY_PATH}.search_channel_candidates", new_callable=AsyncMock
    ) as mock_search, patch(
        f"{DISCOVERY_PATH}.fetch_channels", new_callable=AsyncMock
    ) as mock_channels, patch(
        f"{DISCOVERY_PATH}.fetch_recent_video_stats", new_callable=AsyncMock
    ) as mock_videos:
        mock_search.return_value = {"UCfit001": "fitness India", "UCfit002": "nutrition India"}
        mock_channels.return_value = channels
        mock_videos.return_value = recent_videos()

        res = await client.post(
            f"/api/v1/campaigns/{campaign_id}/discover-creators",
            headers=headers,
        )

    assert res.status_code == 200
    data = res.json()
    assert data["campaign_id"] == campaign_id
    assert data["source"] == "youtube"
    assert data["count"] == 2
    assert data["stats"]["unique_channels"] == 2

    creator = data["creators"][0]
    assert creator["status"] == "DISCOVERED"
    assert creator["creator"]["platform"] == "youtube"
    assert creator["creator"]["followers"] > 0
    # Averages are derived from the mocked recent videos, not invented.
    assert creator["creator"]["avgViews"] > 0
    assert creator["creator"]["metricsSource"] == "auralytics_calculated"
    assert creator["creator"]["metricsSampleSize"] == 5
    # Contact data is never fabricated during discovery.
    assert creator["creator"]["businessEmail"] is None
    assert creator["creator"]["emailVerified"] is False
    # Score is explainable
    assert creator["match_score"] is not None
    assert any(r["key"] == "keyword_relevance" for r in creator["match_reasons"])


@pytest.mark.asyncio
async def test_duplicate_channels_create_single_influencer_record(client):
    """The same channel returned by several queries must not be stored twice."""
    headers = await register(client, "discovery.dupe@test.com")
    campaign_id = await create_fitness_campaign(client, headers)

    channel = make_channel("UCdupe01", "Gym Life India", "Gym, fitness and workout coaching.")

    with patch(f"{DISCOVERY_PATH}.is_configured", return_value=True), patch(
        f"{DISCOVERY_PATH}.search_channel_candidates", new_callable=AsyncMock
    ) as mock_search, patch(
        f"{DISCOVERY_PATH}.fetch_channels", new_callable=AsyncMock
    ) as mock_channels, patch(
        f"{DISCOVERY_PATH}.fetch_recent_video_stats", new_callable=AsyncMock
    ) as mock_videos:
        # The provider deduplicates channel IDs across queries into one map entry.
        mock_search.return_value = {"UCdupe01": "gym India"}
        mock_channels.return_value = [channel]
        mock_videos.return_value = recent_videos(3)

        first = await client.post(f"/api/v1/campaigns/{campaign_id}/discover-creators", headers=headers)
        second = await client.post(
            f"/api/v1/campaigns/{campaign_id}/discover-creators?refresh=true", headers=headers
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["stats"]["created"] == 0
    assert second.json()["stats"]["updated"] == 1

    listing = await client.get(f"/api/v1/campaigns/{campaign_id}/influencers", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1


@pytest.mark.asyncio
async def test_results_persist_and_listing_does_not_call_youtube(client):
    """Reloading the page reads PostgreSQL only; no YouTube request is issued."""
    headers = await register(client, "discovery.persist@test.com")
    campaign_id = await create_fitness_campaign(client, headers)

    with patch(f"{DISCOVERY_PATH}.is_configured", return_value=True), patch(
        f"{DISCOVERY_PATH}.search_channel_candidates", new_callable=AsyncMock
    ) as mock_search, patch(
        f"{DISCOVERY_PATH}.fetch_channels", new_callable=AsyncMock
    ) as mock_channels, patch(
        f"{DISCOVERY_PATH}.fetch_recent_video_stats", new_callable=AsyncMock
    ) as mock_videos:
        mock_search.return_value = {"UCpers01": "fitness India"}
        mock_channels.return_value = [make_channel("UCpers01", "Fit Fuel", "Fitness and nutrition.")]
        mock_videos.return_value = recent_videos(4)

        await client.post(f"/api/v1/campaigns/{campaign_id}/discover-creators", headers=headers)
        search_calls_after_discovery = mock_search.await_count

        listing = await client.get(f"/api/v1/campaigns/{campaign_id}/influencers", headers=headers)

        assert listing.status_code == 200
        assert listing.json()["total"] == 1
        # Listing must not have triggered another search.
        assert mock_search.await_count == search_calls_after_discovery


@pytest.mark.asyncio
async def test_shortlist_status_persists_in_database(client):
    headers = await register(client, "discovery.shortlist@test.com")
    campaign_id = await create_fitness_campaign(client, headers)

    with patch(f"{DISCOVERY_PATH}.is_configured", return_value=True), patch(
        f"{DISCOVERY_PATH}.search_channel_candidates", new_callable=AsyncMock
    ) as mock_search, patch(
        f"{DISCOVERY_PATH}.fetch_channels", new_callable=AsyncMock
    ) as mock_channels, patch(
        f"{DISCOVERY_PATH}.fetch_recent_video_stats", new_callable=AsyncMock
    ) as mock_videos:
        mock_search.return_value = {"UCshort01": "workout India"}
        mock_channels.return_value = [make_channel("UCshort01", "Workout Daily", "Workout and gym plans.")]
        mock_videos.return_value = recent_videos(3)

        discover = await client.post(f"/api/v1/campaigns/{campaign_id}/discover-creators", headers=headers)

    influencer_id = discover.json()["creators"][0]["creator"]["id"]

    patch_res = await client.patch(
        f"/api/v1/campaigns/{campaign_id}/influencers/{influencer_id}",
        headers=headers,
        json={"status": "SHORTLISTED"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "SHORTLISTED"

    # Re-read from the database, as a page refresh would.
    reload_res = await client.get(
        f"/api/v1/campaigns/{campaign_id}/influencers?status=SHORTLISTED", headers=headers
    )
    assert reload_res.status_code == 200
    assert reload_res.json()["total"] == 1


@pytest.mark.asyncio
async def test_user_cannot_access_another_users_campaign_creators(client):
    headers_a = await register(client, "isolation.a@test.com")
    headers_b = await register(client, "isolation.b@test.com")
    campaign_a = await create_fitness_campaign(client, headers_a)

    with patch(f"{DISCOVERY_PATH}.is_configured", return_value=True), patch(
        f"{DISCOVERY_PATH}.search_channel_candidates", new_callable=AsyncMock
    ) as mock_search, patch(
        f"{DISCOVERY_PATH}.fetch_channels", new_callable=AsyncMock
    ) as mock_channels, patch(
        f"{DISCOVERY_PATH}.fetch_recent_video_stats", new_callable=AsyncMock
    ) as mock_videos:
        mock_search.return_value = {"UCiso01": "fitness India"}
        mock_channels.return_value = [make_channel("UCiso01", "Private Fit", "Fitness content.")]
        mock_videos.return_value = recent_videos(3)

        await client.post(f"/api/v1/campaigns/{campaign_a}/discover-creators", headers=headers_a)

    # User B cannot read or discover through User A's campaign.
    assert (await client.get(f"/api/v1/campaigns/{campaign_a}/influencers", headers=headers_b)).status_code == 404
    assert (
        await client.post(f"/api/v1/campaigns/{campaign_a}/discover-creators", headers=headers_b)
    ).status_code == 404

    # And the shared influencer table is not readable by User B either.
    b_list = await client.get("/api/v1/influencers", headers=headers_b)
    assert b_list.status_code == 200
    assert b_list.json() == []


@pytest.mark.asyncio
async def test_no_results_returns_clean_empty_state(client):
    headers = await register(client, "discovery.empty@test.com")
    campaign_id = await create_fitness_campaign(client, headers)

    with patch(f"{DISCOVERY_PATH}.is_configured", return_value=True), patch(
        f"{DISCOVERY_PATH}.search_channel_candidates", new_callable=AsyncMock
    ) as mock_search:
        mock_search.return_value = {}

        res = await client.post(f"/api/v1/campaigns/{campaign_id}/discover-creators", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "empty"
    assert data["count"] == 0
    assert data["creators"] == []


@pytest.mark.asyncio
async def test_missing_api_key_returns_controlled_configuration_error(client):
    headers = await register(client, "discovery.nokey@test.com")
    campaign_id = await create_fitness_campaign(client, headers)

    with patch(f"{DISCOVERY_PATH}.is_configured", return_value=False):
        res = await client.post(f"/api/v1/campaigns/{campaign_id}/discover-creators", headers=headers)

    assert res.status_code == 503
    detail = res.json()["detail"]
    assert "YOUTUBE_API_KEY" in detail
    # The error must never leak a key value.
    assert "AIza" not in detail


@pytest.mark.asyncio
async def test_quota_exceeded_surfaces_429_without_dummy_fallback(client):
    headers = await register(client, "discovery.quota@test.com")
    campaign_id = await create_fitness_campaign(client, headers)

    with patch(f"{DISCOVERY_PATH}.is_configured", return_value=True), patch(
        f"{DISCOVERY_PATH}.search_channel_candidates", new_callable=AsyncMock
    ) as mock_search:
        mock_search.side_effect = YouTubeAPIError("quota", status_code=429)

        res = await client.post(f"/api/v1/campaigns/{campaign_id}/discover-creators", headers=headers)

    assert res.status_code == 429

    # No fallback records were invented.
    listing = await client.get(f"/api/v1/campaigns/{campaign_id}/influencers", headers=headers)
    assert listing.json()["total"] == 0


@pytest.mark.asyncio
async def test_scoring_is_explainable_and_skips_unavailable_signals():
    campaign = Campaign(
        id="camp-score",
        owner_id=uuid.uuid4(),
        name="Summer Fitness Launch",
        brand="PulseFit",
        objective="Product Launch",
        target_locations="India",
        interests=["Fitness"],
        keywords=["fitness", "gym", "workout"],
        min_followers=10000,
        max_followers=500000,
        start_date="2026-09-01",
        end_date="2026-10-01",
    )

    complete = CreatorScoringService.score(
        campaign,
        CreatorSignals(
            name="Gym Life India",
            description="Fitness, gym and workout coaching.",
            followers=82000,
            engagement_rate=4.0,
            metrics_sample_size=5,
            last_upload_at=datetime.now(timezone.utc) - timedelta(days=5),
            country="IN",
        ),
    )
    assert complete.score is not None and complete.score > 80
    assert all(f.score is not None for f in complete.factors)

    # A creator with no published country and no video sample is scored on what exists.
    partial = CreatorScoringService.score(
        campaign,
        CreatorSignals(
            name="Gym Life India",
            description="Fitness, gym and workout coaching.",
            followers=82000,
            engagement_rate=None,
            metrics_sample_size=0,
            last_upload_at=None,
            country=None,
        ),
    )
    assert partial.score is not None
    unavailable = {f.key for f in partial.factors if f.score is None}
    assert unavailable == {"engagement", "recent_activity", "location"}
    assert any("Location unavailable" in f.detail for f in partial.factors)
