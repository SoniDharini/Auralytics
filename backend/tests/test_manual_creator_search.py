"""Manual YouTube creator search on the existing Discovery campaign routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.youtube.client import YouTubeAPIError
from app.services.youtube_query import parse_manual_creator_query

from tests.test_creator_discovery import (
    DISCOVERY_PATH,
    create_fitness_campaign,
    make_channel,
    recent_videos,
    register,
)

SEARCH_PROVIDER = "app.services.creator_discovery_service.YouTubeProvider"


def test_parse_name_handle_url_and_channel_id():
    name = parse_manual_creator_query("CarryMinati")
    assert name.kind == "name"
    assert name.value == "CarryMinati"

    handle = parse_manual_creator_query("@carryminati")
    assert handle.kind == "handle"
    assert handle.value == "carryminati"

    url = parse_manual_creator_query("https://www.youtube.com/@carryminati")
    assert url.kind == "handle"
    assert url.value == "carryminati"

    channel = parse_manual_creator_query("https://www.youtube.com/channel/UCj22tfcQrWG7EMEKS0qHdDg")
    assert channel.kind == "channel_id"
    assert channel.value.startswith("UC")

    raw_id = parse_manual_creator_query("UCj22tfcQrWG7EMEKS0qHdDg")
    assert raw_id.kind == "channel_id"


def test_parse_rejects_video_url_and_short_name():
    with pytest.raises(ValueError):
        parse_manual_creator_query("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    with pytest.raises(ValueError):
        parse_manual_creator_query("x")


@pytest.mark.asyncio
async def test_manual_search_by_name_returns_real_channels(client):
    headers = await register(client, "manual.name@test.com")
    campaign_id = await create_fitness_campaign(client, headers)
    channels = [
        make_channel("UCname001", "ABC Creator", "I am a comedy creator. Subscribe to me for daily vlogs.", subscribers="2300000"),
        make_channel("UCname002", "ABC Creator Clips", "Clip compilations from ABC Creator.", subscribers="320000"),
    ]

    with patch(f"{SEARCH_PROVIDER}.is_configured", return_value=True), patch(
        f"{SEARCH_PROVIDER}.resolve_manual_query", new_callable=AsyncMock
    ) as mock_resolve, patch(
        f"{SEARCH_PROVIDER}.fetch_recent_video_stats", new_callable=AsyncMock
    ) as mock_videos:
        mock_resolve.return_value = channels
        mock_videos.return_value = recent_videos()
        res = await client.get(
            f"/api/v1/campaigns/{campaign_id}/influencers/search",
            headers=headers,
            params={"q": "ABC Creator"},
        )

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["count"] == 2
    assert data["query_kind"] == "name"
    ids = {row["channel_id"] for row in data["results"]}
    assert ids == {"UCname001", "UCname002"}
    assert all(row["creator"]["followers"] > 0 for row in data["results"])
    assert all(row["selection_source"] == "MANUAL_SEARCH" for row in data["results"])


@pytest.mark.asyncio
async def test_manual_search_by_handle_and_url(client):
    headers = await register(client, "manual.handle@test.com")
    campaign_id = await create_fitness_campaign(client, headers)
    channel = make_channel(
        "UChandle01",
        "CarryMinati",
        "I am a comedy creator. Subscribe to me for daily vlogs.",
        subscribers="20000000",
    )

    with patch(f"{SEARCH_PROVIDER}.is_configured", return_value=True), patch(
        f"{SEARCH_PROVIDER}.resolve_manual_query", new_callable=AsyncMock
    ) as mock_resolve, patch(
        f"{SEARCH_PROVIDER}.fetch_recent_video_stats", new_callable=AsyncMock
    ) as mock_videos:
        mock_resolve.return_value = [channel]
        mock_videos.return_value = recent_videos()

        handle_res = await client.get(
            f"/api/v1/campaigns/{campaign_id}/influencers/search",
            headers=headers,
            params={"q": "@carryminati"},
        )
        url_res = await client.get(
            f"/api/v1/campaigns/{campaign_id}/influencers/search",
            headers=headers,
            params={"q": "https://www.youtube.com/@carryminati"},
        )

    assert handle_res.status_code == 200
    assert handle_res.json()["query_kind"] == "handle"
    assert handle_res.json()["results"][0]["channel_id"] == "UChandle01"
    assert url_res.status_code == 200
    assert url_res.json()["query_kind"] == "handle"


@pytest.mark.asyncio
async def test_manual_search_does_not_auto_shortlist(client):
    headers = await register(client, "manual.mult@test.com")
    campaign_id = await create_fitness_campaign(client, headers)
    channels = [
        make_channel("UCauto001", "Creator One", "I am a fitness creator. Subscribe to me.", subscribers="80000"),
        make_channel("UCauto002", "Creator Two", "I am a gym creator. Daily vlog.", subscribers="90000"),
    ]
    with patch(f"{SEARCH_PROVIDER}.is_configured", return_value=True), patch(
        f"{SEARCH_PROVIDER}.resolve_manual_query", new_callable=AsyncMock, return_value=channels
    ), patch(
        f"{SEARCH_PROVIDER}.fetch_recent_video_stats", new_callable=AsyncMock, return_value=recent_videos()
    ):
        res = await client.get(
            f"/api/v1/campaigns/{campaign_id}/influencers/search",
            headers=headers,
            params={"q": "Creator"},
        )
    assert res.status_code == 200
    assert res.json()["count"] == 2
    listing = await client.get(f"/api/v1/campaigns/{campaign_id}/influencers", headers=headers)
    assert listing.json()["total"] == 0


@pytest.mark.asyncio
async def test_manual_shortlist_persists_and_dedupes(client):
    headers = await register(client, "manual.short@test.com")
    campaign_id = await create_fitness_campaign(client, headers)
    channel = make_channel(
        "UCshort99",
        "Workout Daily",
        "I am a fitness creator. Subscribe to me for daily vlogs.",
        subscribers="82000",
    )
    with patch(f"{SEARCH_PROVIDER}.is_configured", return_value=True), patch(
        f"{SEARCH_PROVIDER}.resolve_manual_query", new_callable=AsyncMock, return_value=[channel]
    ), patch(
        f"{SEARCH_PROVIDER}.fetch_channels", new_callable=AsyncMock, return_value=[channel]
    ), patch(
        f"{SEARCH_PROVIDER}.fetch_recent_video_stats", new_callable=AsyncMock, return_value=recent_videos()
    ):
        search = await client.get(
            f"/api/v1/campaigns/{campaign_id}/influencers/search",
            headers=headers,
            params={"q": "Workout Daily"},
        )
        assert search.status_code == 200
        first = await client.post(
            f"/api/v1/campaigns/{campaign_id}/influencers/manual-shortlist",
            headers=headers,
            json={"channel_id": "UCshort99", "query": "Workout Daily"},
        )
        second = await client.post(
            f"/api/v1/campaigns/{campaign_id}/influencers/manual-shortlist",
            headers=headers,
            json={"channel_id": "UCshort99", "query": "Workout Daily"},
        )

    assert first.status_code == 200, first.text
    assert first.json()["status"] == "SHORTLISTED"
    assert second.status_code == 200
    assert second.json()["creator"]["id"] == first.json()["creator"]["id"]

    reload_res = await client.get(
        f"/api/v1/campaigns/{campaign_id}/influencers?status=SHORTLISTED", headers=headers
    )
    assert reload_res.status_code == 200
    assert reload_res.json()["total"] == 1
    assert reload_res.json()["creators"][0]["status"] == "SHORTLISTED"


@pytest.mark.asyncio
async def test_manual_search_duplicate_of_discovery_result(client):
    headers = await register(client, "manual.dup@test.com")
    campaign_id = await create_fitness_campaign(client, headers)
    channel = make_channel(
        "UCdup001",
        "Fitness With Rahul",
        "I am a fitness creator. Subscribe to me for daily vlogs.",
        subscribers="82000",
    )
    with patch(f"{DISCOVERY_PATH}.is_configured", return_value=True), patch(
        f"{DISCOVERY_PATH}.search_channel_candidates", new_callable=AsyncMock, return_value={"UCdup001": "fitness"}
    ), patch(
        f"{DISCOVERY_PATH}.fetch_channels", new_callable=AsyncMock, return_value=[channel]
    ), patch(
        f"{DISCOVERY_PATH}.fetch_recent_video_stats", new_callable=AsyncMock, return_value=recent_videos()
    ):
        discovered = await client.post(f"/api/v1/campaigns/{campaign_id}/discover-creators", headers=headers)
    assert discovered.status_code == 200
    influencer_id = discovered.json()["creators"][0]["creator"]["id"]

    with patch(f"{SEARCH_PROVIDER}.is_configured", return_value=True), patch(
        f"{SEARCH_PROVIDER}.resolve_manual_query", new_callable=AsyncMock, return_value=[channel]
    ), patch(
        f"{SEARCH_PROVIDER}.fetch_recent_video_stats", new_callable=AsyncMock, return_value=recent_videos()
    ):
        search = await client.get(
            f"/api/v1/campaigns/{campaign_id}/influencers/search",
            headers=headers,
            params={"q": "Fitness With Rahul"},
        )
    assert search.status_code == 200
    row = search.json()["results"][0]
    assert row["already_in_campaign"] is True
    assert row["already_recommended"] is True
    assert row["influencer_id"] == influencer_id


@pytest.mark.asyncio
async def test_manual_search_range_mismatch_requires_override(client):
    headers = await register(client, "manual.range@test.com")
    campaign_id = await create_fitness_campaign(client, headers)
    channel = make_channel(
        "UChuge001",
        "Huge Fit",
        "I am a fitness creator. Subscribe to me for daily vlogs.",
        subscribers="5000000",
    )
    with patch(f"{SEARCH_PROVIDER}.is_configured", return_value=True), patch(
        f"{SEARCH_PROVIDER}.resolve_manual_query", new_callable=AsyncMock, return_value=[channel]
    ), patch(
        f"{SEARCH_PROVIDER}.fetch_channels", new_callable=AsyncMock, return_value=[channel]
    ), patch(
        f"{SEARCH_PROVIDER}.fetch_recent_video_stats", new_callable=AsyncMock, return_value=recent_videos()
    ):
        search = await client.get(
            f"/api/v1/campaigns/{campaign_id}/influencers/search",
            headers=headers,
            params={"q": "Huge Fit"},
        )
        assert search.status_code == 200
        row = search.json()["results"][0]
        assert row["manual_override_required"] is True
        assert any(m["code"] == "FOLLOWER_RANGE" for m in row["mismatches"])
        assert row["requirement_match"]["subscriber_range"] == "FAIL"

        denied = await client.post(
            f"/api/v1/campaigns/{campaign_id}/influencers/manual-shortlist",
            headers=headers,
            json={"channel_id": "UChuge001", "confirm_override": False},
        )
        assert denied.status_code == 409

        confirmed = await client.post(
            f"/api/v1/campaigns/{campaign_id}/influencers/manual-shortlist",
            headers=headers,
            json={"channel_id": "UChuge001", "confirm_override": True, "query": "Huge Fit"},
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "SHORTLISTED"
        reasons = confirmed.json()["match_reasons"] or []
        assert any(r.get("selection_source") == "MANUAL_SEARCH" for r in reasons)


@pytest.mark.asyncio
async def test_manual_search_foreign_creator_is_not_marked_indian(client):
    headers = await register(client, "manual.us@test.com")
    campaign_id = await create_fitness_campaign(client, headers)
    channel = make_channel(
        "UCus0001",
        "US Fitness",
        "I am a fitness creator. Subscribe to me.",
        subscribers="80000",
        country="US",
    )
    with patch(f"{SEARCH_PROVIDER}.is_configured", return_value=True), patch(
        f"{SEARCH_PROVIDER}.resolve_manual_query", new_callable=AsyncMock, return_value=[channel]
    ), patch(
        f"{SEARCH_PROVIDER}.fetch_recent_video_stats", new_callable=AsyncMock, return_value=recent_videos()
    ):
        res = await client.get(
            f"/api/v1/campaigns/{campaign_id}/influencers/search",
            headers=headers,
            params={"q": "US Fitness"},
        )
    row = res.json()["results"][0]
    assert row["creator"]["country"] == "US"
    assert row["requirement_match"]["location"] == "FAIL"
    assert row["meets_requirements"] is False


@pytest.mark.asyncio
async def test_manual_search_organization_cannot_be_shortlisted(client):
    headers = await register(client, "manual.org@test.com")
    campaign_id = await create_fitness_campaign(client, headers)
    channel = make_channel(
        "UCorg001",
        "Harvest Kitchen Media",
        "Official brand channel of Harvest Foods Pvt Ltd. This corporation publishes product films.",
        subscribers="800000",
    )
    with patch(f"{SEARCH_PROVIDER}.is_configured", return_value=True), patch(
        f"{SEARCH_PROVIDER}.resolve_manual_query", new_callable=AsyncMock, return_value=[channel]
    ), patch(
        f"{SEARCH_PROVIDER}.fetch_channels", new_callable=AsyncMock, return_value=[channel]
    ), patch(
        f"{SEARCH_PROVIDER}.fetch_recent_video_stats", new_callable=AsyncMock, return_value=recent_videos()
    ):
        search = await client.get(
            f"/api/v1/campaigns/{campaign_id}/influencers/search",
            headers=headers,
            params={"q": "Harvest Kitchen Media"},
        )
        assert search.json()["results"][0]["shortlist_allowed"] is False
        blocked = await client.post(
            f"/api/v1/campaigns/{campaign_id}/influencers/manual-shortlist",
            headers=headers,
            json={"channel_id": "UCorg001", "confirm_override": True},
        )
    assert blocked.status_code == 422


@pytest.mark.asyncio
async def test_manual_search_youtube_failure_does_not_invent_creators(client):
    headers = await register(client, "manual.fail@test.com")
    campaign_id = await create_fitness_campaign(client, headers)
    with patch(f"{SEARCH_PROVIDER}.is_configured", return_value=True), patch(
        f"{SEARCH_PROVIDER}.resolve_manual_query",
        new_callable=AsyncMock,
        side_effect=YouTubeAPIError("boom", status_code=502),
    ):
        res = await client.get(
            f"/api/v1/campaigns/{campaign_id}/influencers/search",
            headers=headers,
            params={"q": "CarryMinati"},
        )
    assert res.status_code in (502, 503, 429)
    listing = await client.get(f"/api/v1/campaigns/{campaign_id}/influencers", headers=headers)
    assert listing.json()["total"] == 0


@pytest.mark.asyncio
async def test_manual_search_requires_campaign_ownership(client):
    owner = await register(client, "manual.owner@test.com")
    other = await register(client, "manual.other@test.com")
    campaign_id = await create_fitness_campaign(client, owner)
    res = await client.get(
        f"/api/v1/campaigns/{campaign_id}/influencers/search",
        headers=other,
        params={"q": "CarryMinati"},
    )
    assert res.status_code == 404
