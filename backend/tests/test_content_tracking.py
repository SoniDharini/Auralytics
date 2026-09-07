import uuid
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta

from app.core.exceptions import BadRequestException, NotFoundException
from app.integrations.youtube.client import YouTubeAPIError
from app.models.campaign import Campaign
from app.models.campaign_content import CampaignContent, ContentType, TrackingStatus, PerformanceStatus
from app.models.campaign_influencer import CampaignInfluencer
from app.models.contract import Contract
from app.models.influencer import Influencer
from app.models.user import User
from app.services.content_tracking_service import (
    ContentTrackingService,
    calculate_cpm,
    calculate_cost_per_engagement,
    calculate_cost_per_view,
    calculate_engagement_lift,
    calculate_engagement_rate,
    calculate_performance_lift,
    calculate_roas,
    calculate_roi,
    calculate_content_age,
    calculate_momentum,
    classify_performance_status,
    extract_youtube_video_id,
)


@pytest_asyncio.fixture
async def sample_campaign(db_session, test_user):
    camp = Campaign(
        id=f"camp-{uuid.uuid4().hex[:8]}",
        owner_id=test_user.id,
        name="FizzUp Summer Launch",
        brand="FizzUp",
        status="active",
        health="healthy",
        budget=100000.0,
        start_date="2026-09-01",
        end_date="2026-09-30",
        workflow_state="CAMPAIGN_LIVE",
    )
    db_session.add(camp)
    await db_session.commit()
    await db_session.refresh(camp)
    return camp


def test_youtube_url_extraction():
    # Valid watch URL
    vid, canonical, ctype = extract_youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert vid == "dQw4w9WgXcQ"
    assert canonical == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert ctype == ContentType.YOUTUBE_VIDEO

    # Valid short URL
    vid, canonical, ctype = extract_youtube_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ?feature=share")
    assert vid == "dQw4w9WgXcQ"
    assert canonical == "https://www.youtube.com/shorts/dQw4w9WgXcQ"
    assert ctype == ContentType.YOUTUBE_SHORT

    # Valid youtu.be URL
    vid, canonical, ctype = extract_youtube_video_id("https://youtu.be/dQw4w9WgXcQ")
    assert vid == "dQw4w9WgXcQ"
    assert canonical == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    # Direct 11-character video ID
    vid, canonical, ctype = extract_youtube_video_id("dQw4w9WgXcQ")
    assert vid == "dQw4w9WgXcQ"

    # Invalid URL
    with pytest.raises(BadRequestException):
        extract_youtube_video_id("https://example.com/not-youtube")

    with pytest.raises(BadRequestException):
        extract_youtube_video_id("")


def test_deterministic_kpi_calculations():
    # Engagement rate: (likes + comments) / views * 100
    assert calculate_engagement_rate(500000, 35000, 2000) == 7.4
    assert calculate_engagement_rate(0, 10, 5) == 0.0

    # Engagement lift: ((campaign_eng - baseline_eng) / baseline_eng) * 100
    assert calculate_engagement_lift(7.4, 5.0) == 48.0
    assert calculate_engagement_lift(7.4, None) is None

    # Performance lift: ((campaign - baseline) / baseline) * 100
    # 500k vs 300k baseline -> +66.67%
    assert calculate_performance_lift(500000, 300000) == 66.67
    # 180k vs 500k baseline -> -64.0%
    assert calculate_performance_lift(180000, 500000) == -64.0
    assert calculate_performance_lift(500000, None) is None
    assert calculate_performance_lift(500000, 0) is None

    # Cost per view: agreed_cost / views
    # 50,000 / 500,000 = 0.10
    assert calculate_cost_per_view(50000.0, 500000) == 0.10
    # Micro-CPV: 200,000 / 23,400,000 = 0.008547
    assert calculate_cost_per_view(200000.0, 23400000) == 0.008547
    assert calculate_cost_per_view(None, 500000) is None
    assert calculate_cost_per_view(50000.0, 0) is None

    # CPM (Cost per 1,000 views): (agreed_cost / views) * 1000
    # (200,000 / 23,400,000) * 1000 = 8.55
    assert calculate_cpm(200000.0, 23400000) == 8.55
    assert calculate_cpm(50000.0, 500000) == 100.0
    assert calculate_cpm(None, 500000) is None

    # Cost per engagement: agreed_cost / (likes + comments)
    # 50,000 / (35,000 + 2,000) = 50,000 / 37,000 ~ 1.35
    assert calculate_cost_per_engagement(50000.0, 35000, 2000) == 1.35
    assert calculate_cost_per_engagement(None, 35000, 2000) is None

    # Performance classification
    assert classify_performance_status(35.0, 7.0, 5.0) == PerformanceStatus.STRONG
    assert classify_performance_status(10.0, 5.5, 5.0) == PerformanceStatus.ON_TRACK
    assert classify_performance_status(-5.0, 4.8, 5.0) == PerformanceStatus.AVERAGE
    assert classify_performance_status(-25.0, 3.5, 5.0) == PerformanceStatus.NEEDS_ATTENTION
    assert classify_performance_status(-45.0, 2.0, 5.0) == PerformanceStatus.UNDERPERFORMING

    # Recency-aware classification: published 2 days ago with massive traction and good engagement
    published_two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)
    assert (
        classify_performance_status(
            -47.6,
            3.16,
            3.0,
            published_at=published_two_days_ago,
            views=23400000,
            baseline_views=44700000,
        )
        == PerformanceStatus.ON_TRACK
    )


@pytest.mark.asyncio
async def test_track_content_creator_mismatch(db_session, sample_campaign):
    # Influencer with channel UC_EXPECTED
    inf = Influencer(
        id=f"inf-{uuid.uuid4().hex[:8]}",
        platform="youtube",
        external_id="UC_EXPECTED_CHANNEL",
        username="CreatorABC",
        name="Creator ABC",
    )
    db_session.add(inf)
    await db_session.commit()

    # Mock YouTube client returning a video from a DIFFERENT channel UC_WRONG
    mock_yt = AsyncMock()
    mock_yt.is_configured = True
    mock_yt.get_video_details.return_value = {
        "id": "dQw4w9WgXcQ",
        "title": "Unrelated Video",
        "channel_id": "UC_WRONG_CHANNEL",
        "channel_title": "Different Creator",
        "view_count": 10000,
        "like_count": 500,
        "comment_count": 50,
        "is_short": False,
    }

    tracking_svc = ContentTrackingService(db_session, youtube_client=mock_yt)

    with pytest.raises(BadRequestException) as exc_info:
        await tracking_svc.track_content(
            campaign=sample_campaign,
            influencer=inf,
            content_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )

    assert "CREATOR_VIDEO_MISMATCH" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_track_content_success_with_contract_cost(db_session, sample_campaign):
    # Creator with matching channel
    inf = Influencer(
        id=f"inf-{uuid.uuid4().hex[:8]}",
        platform="youtube",
        external_id="UC_CREATOR_MATCH",
        username="CreatorMatch",
        name="Creator Match",
    )
    db_session.add(inf)

    # Approved contract with agreed cost 50,000 INR
    contract = Contract(
        id=f"cntr-{uuid.uuid4().hex[:8]}",
        campaign_id=sample_campaign.id,
        influencer_id=inf.id,
        creator=inf.name,
        username=inf.username,
        campaign=sample_campaign.name,
        value=50000.0,
        currency="INR",
        status="APPROVED",
        start_date="2026-09-01",
        end_date="2026-09-30",
        payment_due="Net 30",
        deliverables=["1 YouTube Short"],
        usage_rights="Digital",
        exclusivity="Non-exclusive",
    )
    db_session.add(contract)
    await db_session.commit()

    # Mock YouTube client returning video and baseline uploads
    mock_yt = AsyncMock()
    mock_yt.is_configured = True
    mock_yt.get_video_details.return_value = {
        "id": "dQw4w9WgXcQ",
        "title": "FizzUp Sponsored Short",
        "channel_id": "UC_CREATOR_MATCH",
        "channel_title": "Creator Match",
        "view_count": 500000,
        "like_count": 35000,
        "comment_count": 2000,
        "published_at": "2026-09-01T12:00:00Z",
        "is_short": True,
    }

    # Mock baseline calculation
    mock_channel_obj = AsyncMock()
    mock_channel_obj.contentDetails.relatedPlaylists.uploads = "UPLOADS_PL"
    mock_yt.get_channels_by_id.return_value = AsyncMock(items=[mock_channel_obj])
    mock_yt.get_playlist_items.return_value = ["vid1", "vid2", "vid3", "vid4", "vid5"]
    mock_yt.get_videos_statistics.return_value = [
        {"id": "vid1", "view_count": 300000, "like_count": 20000, "comment_count": 1000, "is_short": True},
        {"id": "vid2", "view_count": 280000, "like_count": 18000, "comment_count": 900, "is_short": True},
        {"id": "vid3", "view_count": 320000, "like_count": 22000, "comment_count": 1100, "is_short": True},
        {"id": "vid4", "view_count": 290000, "like_count": 19000, "comment_count": 950, "is_short": True},
        {"id": "vid5", "view_count": 310000, "like_count": 21000, "comment_count": 1050, "is_short": True},
    ]

    tracking_svc = ContentTrackingService(db_session, youtube_client=mock_yt)
    content = await tracking_svc.track_content(
        campaign=sample_campaign,
        influencer=inf,
        content_url="https://www.youtube.com/shorts/dQw4w9WgXcQ",
    )

    assert content.external_content_id == "dQw4w9WgXcQ"
    assert content.content_type == ContentType.YOUTUBE_SHORT
    assert content.current_views == 500000
    assert content.current_likes == 35000
    assert content.current_comments == 2000
    assert content.engagement_rate == 7.4
    # Median baseline of [280k, 290k, 300k, 310k, 320k] is 300k
    assert content.baseline_median_views == 300000.0
    # Lift: (500k - 300k) / 300k = +66.67%
    assert content.performance_lift_percent == 66.67
    # Agreed cost 50,000 INR -> CPV = 50,000 / 500,000 = 0.10
    assert content.cost_per_view == 0.10
    # CPE = 50,000 / (35k + 2k) = 1.35
    assert content.cost_per_engagement == 1.35
    assert content.performance_status == PerformanceStatus.STRONG
    assert len(content.snapshots) == 1


@pytest.mark.asyncio
async def test_track_content_without_contract_cost(db_session, sample_campaign):
    # Influencer without contract
    inf = Influencer(
        id=f"inf-{uuid.uuid4().hex[:8]}",
        platform="youtube",
        external_id="UC_NO_COST",
        username="CreatorNoCost",
        name="Creator No Cost",
    )
    db_session.add(inf)
    await db_session.commit()

    mock_yt = AsyncMock()
    mock_yt.is_configured = True
    mock_yt.get_video_details.return_value = {
        "id": "abc123xyz89",
        "title": "Unpaid Sponsored Video",
        "channel_id": "UC_NO_COST",
        "channel_title": "Creator No Cost",
        "view_count": 100000,
        "like_count": 5000,
        "comment_count": 300,
        "is_short": False,
    }
    mock_yt.get_channels_by_id.return_value = AsyncMock(items=[])

    tracking_svc = ContentTrackingService(db_session, youtube_client=mock_yt)
    content = await tracking_svc.track_content(
        campaign=sample_campaign,
        influencer=inf,
        content_url="https://www.youtube.com/watch?v=abc123xyz89",
    )

    # Missing cost must result in None / UNKNOWN cost per view
    assert content.agreed_cost is None
    assert content.cost_per_view is None
    assert content.cost_per_engagement is None


@pytest.mark.asyncio
async def test_refresh_content_metrics_and_momentum(db_session, sample_campaign):
    inf = Influencer(
        id=f"inf-{uuid.uuid4().hex[:8]}",
        platform="youtube",
        external_id="UC_REFRESH_TEST",
        username="CreatorRefresh",
        name="Creator Refresh",
    )
    db_session.add(inf)
    await db_session.commit()

    mock_yt = AsyncMock()
    mock_yt.is_configured = True
    # Initial capture: 100k views
    mock_yt.get_video_details.return_value = {
        "id": "ref12345678",
        "title": "Momentum Test",
        "channel_id": "UC_REFRESH_TEST",
        "view_count": 100000,
        "like_count": 5000,
        "comment_count": 500,
        "is_short": False,
    }
    mock_yt.get_channels_by_id.return_value = AsyncMock(items=[])

    tracking_svc = ContentTrackingService(db_session, youtube_client=mock_yt)
    content = await tracking_svc.track_content(
        campaign=sample_campaign,
        influencer=inf,
        content_url="https://www.youtube.com/watch?v=ref12345678",
    )
    assert content.current_views == 100000

    # Simulate metric refresh: 250k views (+150k growth, +150%)
    mock_yt.get_video_details.return_value = {
        "id": "ref12345678",
        "title": "Momentum Test",
        "channel_id": "UC_REFRESH_TEST",
        "view_count": 250000,
        "like_count": 12000,
        "comment_count": 1000,
        "is_short": False,
    }

    updated = await tracking_svc.refresh_content_metrics(content.id)
    assert updated.current_views == 250000

    # Snapshots should have 2 entries
    assert len(updated.snapshots) == 2
    latest_snap = updated.snapshots[-1]
    assert latest_snap.views == 250000
    assert latest_snap.view_growth_absolute == 150000
    assert latest_snap.view_growth_percentage == 150.0


@pytest.mark.asyncio
async def test_content_tracking_api_and_isolation(client, db_session):
    # 1. Register User A
    user_a_res = await client.post("/api/v1/auth/register", json={
        "full_name": "User Alpha",
        "email": "alpha@example.com",
        "password": "Password123!",
        "company_name": "Brand Alpha",
        "role": "brand_manager",
    })
    token_a = user_a_res.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register User B
    user_b_res = await client.post("/api/v1/auth/register", json={
        "full_name": "User Beta",
        "email": "beta@example.com",
        "password": "Password123!",
        "company_name": "Brand Beta",
        "role": "brand_manager",
    })
    token_b = user_b_res.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. User A creates Campaign
    camp_res = await client.post("/api/v1/campaigns", json={
        "name": "Alpha Live Campaign",
        "brand": "AlphaBrand",
        "budget": 50000.0,
        "start_date": "2026-09-01",
        "end_date": "2026-09-30",
        "objective": "Product Launch",
    }, headers=headers_a)
    assert camp_res.status_code == 201
    camp_id = camp_res.json()["id"]

    # 4. User A tracks content with mock YouTube client
    mock_yt_details = {
        "id": "dQw4w9WgXcQ",
        "title": "Alpha Sponsored Short",
        "channel_id": "UC_ALPHA_CHANNEL",
        "channel_title": "Alpha Creator",
        "view_count": 450000,
        "like_count": 30000,
        "comment_count": 1500,
        "is_short": True,
    }

    # Create creator with matching external_id
    from app.models.influencer import Influencer
    inf = Influencer(
        id="inf-alpha-creator-1",
        platform="youtube",
        external_id="UC_ALPHA_CHANNEL",
        username="AlphaCreator",
        name="Alpha Creator",
    )
    db_session.add(inf)
    await db_session.commit()


    with patch("app.services.content_tracking_service.YouTubeClient.get_video_details", new=AsyncMock(return_value=mock_yt_details)), \
         patch("app.services.content_tracking_service.YouTubeClient.get_channels_by_id", new=AsyncMock(return_value=AsyncMock(items=[]))):

        track_res = await client.post(
            f"/api/v1/campaigns/{camp_id}/content/track",
            json={
                "influencer_id": "inf-alpha-creator-1",
                "content_url": "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            },
            headers=headers_a,
        )
        assert track_res.status_code == 200
        content_data = track_res.json()
        assert content_data["external_content_id"] == "dQw4w9WgXcQ"
        assert content_data["current_views"] == 450000
        content_id = content_data["id"]

        # 5. User A lists content
        list_res = await client.get(f"/api/v1/campaigns/{camp_id}/content", headers=headers_a)
        assert list_res.status_code == 200
        assert len(list_res.json()) == 1

        # 6. User B tries to track or list content on Campaign A -> must fail (isolation)
        user_b_track = await client.post(
            f"/api/v1/campaigns/{camp_id}/content/track",
            json={
                "influencer_id": "inf-alpha-creator-1",
                "content_url": "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            },
            headers=headers_b,
        )
        assert user_b_track.status_code in (404, 403)

        user_b_list = await client.get(f"/api/v1/campaigns/{camp_id}/content", headers=headers_b)
        assert user_b_list.status_code in (404, 403)

        # 7. User A refreshes metrics
        mock_yt_details["view_count"] = 550000
        mock_yt_details["like_count"] = 38000
        mock_yt_details["comment_count"] = 1900
        refresh_res = await client.post(
            f"/api/v1/campaigns/{camp_id}/content/{content_id}/refresh",
            headers=headers_a,
        )
        assert refresh_res.status_code == 200
        refreshed_data = refresh_res.json()
        assert refreshed_data["current_views"] == 550000
        assert len(refreshed_data["snapshots"]) == 2


# =====================================================================
# REQUIRED TESTS (SECTIONS 56 - 63)
# =====================================================================

def test_required_56_roas_calculation():
    """Section 56: Spend 50k, Revenue 180k -> ROAS = 3.6x."""
    spend = 50000.0
    revenue = 180000.0
    roas = calculate_roas(spend, revenue)
    assert roas == 3.6


def test_required_57_roi_calculation():
    """Section 57: Spend 50k, Revenue 180k, Margin 40% (Profit 72k) -> ROI = 44.0%."""
    spend = 50000.0
    revenue = 180000.0
    margin_pct = 40.0
    profit = revenue * (margin_pct / 100.0)  # 72,000
    assert profit == 72000.0
    roi = calculate_roi(spend, profit)
    assert roi == 44.0


def test_required_58_roi_without_margin():
    """Section 58: Spend 50k, Revenue 180k, No margin/profit supplied -> ROAS 3.6x, ROI is None (NOT_AVAILABLE)."""
    spend = 50000.0
    revenue = 180000.0
    roas = calculate_roas(spend, revenue)
    roi = calculate_roi(spend, None)
    assert roas == 3.6
    assert roi is None


def test_required_59_video_age_early_stage():
    """Section 59: Video age 4 hours, views lower than final historical average -> EARLY_STAGE, not UNDERPERFORMING."""
    # Video published 4 hours ago
    four_hours_ago = datetime.now(timezone.utc)
    from datetime import timedelta
    four_hours_ago = four_hours_ago - timedelta(hours=4)

    # 80K views vs 500K baseline (-84% lift)
    status = classify_performance_status(
        lift_percent=-84.0,
        engagement_rate=4.5,
        baseline_engagement_rate=5.0,
        published_at=four_hours_ago,
        views=80000,
        baseline_views=500000,
    )
    assert status == PerformanceStatus.EARLY_STAGE
    assert status != PerformanceStatus.UNDERPERFORMING


def test_required_60_mature_underperformance():
    """Section 60: Video age 10 days, baseline 500K, campaign video 150K, momentum SLOWING -> UNDERPERFORMING."""
    from datetime import timedelta
    ten_days_ago = datetime.now(timezone.utc) - timedelta(days=10)

    # 150K vs 500K baseline -> -70% lift
    status = classify_performance_status(
        lift_percent=-70.0,
        engagement_rate=2.0,
        baseline_engagement_rate=5.0,
        published_at=ten_days_ago,
        views=150000,
        baseline_views=500000,
        momentum="SLOWING",
    )
    assert status == PerformanceStatus.UNDERPERFORMING


def test_required_61_awareness_objective():
    """Section 61: Objective Awareness, views strong, engagement strong, ROAS unknown -> Performance is STRONG."""
    status = classify_performance_status(
        lift_percent=35.0,
        engagement_rate=6.5,
        baseline_engagement_rate=4.0,
        views=600000,
        baseline_views=440000,
        objective="Brand Awareness",
        roas=None,
        momentum="RISING",
    )
    assert status == PerformanceStatus.STRONG


def test_required_62_sales_objective_weak_roas():
    """Section 62: Objective Conversions, views strong, revenue low, ROAS 0.7x -> identifies weak commercial return."""
    from datetime import timedelta
    eight_days_ago = datetime.now(timezone.utc) - timedelta(days=8)
    status = classify_performance_status(
        lift_percent=40.0,
        engagement_rate=5.0,
        baseline_engagement_rate=4.0,
        published_at=eight_days_ago,
        views=500000,
        baseline_views=350000,
        objective="Conversions & Sales",
        roas=0.7,
        momentum="STABLE",
    )
    assert status in (PerformanceStatus.UNDERPERFORMING, PerformanceStatus.NEEDS_ATTENTION)


@pytest.mark.asyncio
async def test_required_63_multiple_content_revenue_aggregation(db_session, test_user, sample_campaign):
    """Section 63: Video A Revenue 100K, Video B Revenue 80K -> Total 180K, no double counting."""
    from app.models.campaign_content import CampaignContent, ContentType, TrackingStatus

    # Video A
    v_a = CampaignContent(
        id=f"ccont-a-{uuid.uuid4().hex[:6]}",
        campaign_id=sample_campaign.id,
        influencer_id=f"inf-a-{uuid.uuid4().hex[:6]}",
        platform="youtube",
        content_type=ContentType.YOUTUBE_VIDEO,
        external_content_id="videoA_id_1",
        content_url="https://www.youtube.com/watch?v=videoA_id_1",
        current_views=200000,
        agreed_cost=50000.0,
        attributed_revenue=100000.0,
        tracking_status=TrackingStatus.ACTIVE,
    )
    # Video B
    v_b = CampaignContent(
        id=f"ccont-b-{uuid.uuid4().hex[:6]}",
        campaign_id=sample_campaign.id,
        influencer_id=f"inf-b-{uuid.uuid4().hex[:6]}",
        platform="youtube",
        content_type=ContentType.YOUTUBE_SHORT,
        external_content_id="videoB_id_2",
        content_url="https://www.youtube.com/shorts/videoB_id_2",
        current_views=300000,
        agreed_cost=50000.0,
        attributed_revenue=80000.0,
        tracking_status=TrackingStatus.ACTIVE,
    )
    db_session.add_all([v_a, v_b])
    await db_session.commit()

    # Reconcile campaign totals
    tracking_svc = ContentTrackingService(db_session)
    await tracking_svc.sync_campaign_metrics(sample_campaign.id)
    await db_session.refresh(sample_campaign)

    # Total spend: 50k + 50k = 100k
    assert sample_campaign.spend == 100000.0
    # Total revenue: 100k + 80k = 180k
    assert sample_campaign.revenue == 180000.0
    # Campaign ROAS: 180k / 100k = 1.8x
    assert sample_campaign.roas == 1.8


@pytest.mark.asyncio
async def test_attribution_endpoint_and_deterministic_storage(client, db_session):
    """Verifies POST /campaigns/{campaign_id}/content/{content_id}/attribution saves data and updates ROAS/ROI."""
    # Register and create campaign
    u_res = await client.post("/api/v1/auth/register", json={
        "full_name": "Revenue Admin",
        "email": "revenue@example.com",
        "password": "Password123!",
        "company_name": "Brand Rev",
        "role": "brand_manager",
    })
    token = u_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    c_res = await client.post("/api/v1/campaigns", json={
        "name": "ROI Verified Campaign",
        "brand": "RevBrand",
        "budget": 100000.0,
        "start_date": "2026-09-01",
        "end_date": "2026-09-30",
        "objective": "Sales",
    }, headers=headers)
    camp_id = c_res.json()["id"]

    # Influencer
    inf = Influencer(
        id=f"inf-{uuid.uuid4().hex[:8]}",
        platform="youtube",
        external_id="UC_ROAS_TEST",
        username="RoasCreator",
        name="ROAS Creator",
    )
    db_session.add(inf)
    await db_session.commit()

    # Track content
    mock_yt = {
        "id": "dQw4w9WgXcQ",
        "title": "ROAS Test Video",
        "channel_id": "UC_ROAS_TEST",
        "view_count": 500000,
        "like_count": 25000,
        "comment_count": 1000,
        "is_short": False,
    }
    with patch("app.services.content_tracking_service.YouTubeClient.get_video_details", new=AsyncMock(return_value=mock_yt)), \
         patch("app.services.content_tracking_service.YouTubeClient.get_channels_by_id", new=AsyncMock(return_value=AsyncMock(items=[]))):
        t_res = await client.post(
            f"/api/v1/campaigns/{camp_id}/content/track",
            json={"influencer_id": inf.id, "content_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            headers=headers,
        )
        assert t_res.status_code == 200
        content_id = t_res.json()["id"]

    # Manually attach agreed_cost 50,000 for deterministic ROAS test
    content_obj = await db_session.get(CampaignContent, content_id)
    content_obj.agreed_cost = 50000.0
    await db_session.commit()

    # Test Option A: Direct Revenue (180,000) with 40% margin (72,000 profit)
    attr_res = await client.post(
        f"/api/v1/campaigns/{camp_id}/content/{content_id}/attribution",
        json={
            "attributed_revenue": 180000.0,
            "gross_margin_percent": 40.0,
            "attribution_source": "Coupon Code",
        },
        headers=headers,
    )
    assert attr_res.status_code == 200
    attr_data = attr_res.json()
    assert attr_data["attributed_revenue"] == 180000.0
    assert attr_data["roas"] == 3.6
    assert attr_data["roi"] == 44.0
    assert attr_data["attribution_source"] == "Coupon Code"

    # Test Option B: Orders (300) x AOV (600) -> 180,000 revenue
    attr_res_b = await client.post(
        f"/api/v1/campaigns/{camp_id}/content/{content_id}/attribution",
        json={
            "attributed_orders": 300,
            "average_order_value": 600.0,
            "gross_margin_percent": 40.0,
            "attribution_source": "Tracking Link",
        },
        headers=headers,
    )
    assert attr_res_b.status_code == 200
    attr_data_b = attr_res_b.json()
    assert attr_data_b["attributed_revenue"] == 180000.0
    assert attr_data_b["roas"] == 3.6
    assert attr_data_b["roi"] == 44.0



