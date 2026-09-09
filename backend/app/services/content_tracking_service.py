"""Content tracking, validation, YouTube API synchronization, creator baseline, and deterministic KPI engine."""

from __future__ import annotations

import logging
import re
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import BadRequestException, NotFoundException
from app.integrations.youtube.client import YouTubeAPIError, YouTubeClient
from app.models.campaign import Campaign
from app.models.campaign_content import (
    CampaignContent,
    ContentPerformanceSnapshot,
    ContentType,
    PerformanceStatus,
    TrackingStatus,
    ContentStage,
    ViewMomentum,
)
from app.models.campaign_influencer import CampaignInfluencer
from app.models.contract import Contract
from app.models.influencer import Influencer
from app.models.outreach import OutreachMessage
from app.models.user import User

logger = logging.getLogger(__name__)

# Regular expressions for YouTube URLs
# Matches:
# https://www.youtube.com/watch?v=VIDEO_ID
# https://m.youtube.com/watch?v=VIDEO_ID
# https://www.youtube.com/shorts/VIDEO_ID
# https://youtu.be/VIDEO_ID
# https://www.youtube.com/embed/VIDEO_ID
YOUTUBE_URL_PATTERNS = [
    re.compile(r"(?:https?:\/\/)?(?:www\.|m\.)?youtube\.com\/watch\?(?:.*&)?v=([a-zA-Z0-9_-]{11,12})(?:&.*)?$"),
    re.compile(r"(?:https?:\/\/)?(?:www\.|m\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11,12})(?:[/?&].*)?$"),
    re.compile(r"(?:https?:\/\/)?youtu\.be\/([a-zA-Z0-9_-]{11,12})(?:[/?&].*)?$"),
    re.compile(r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11,12})(?:[/?&].*)?$"),
]


def extract_youtube_video_id(url: str) -> Tuple[str, str, str]:
    """Deterministically extracts YouTube video ID, canonical URL, and inferred content type.

    Returns:
        (video_id, canonical_url, inferred_content_type)
    Raises:
        BadRequestException if URL format is invalid.
    """
    cleaned = (url or "").strip()
    if not cleaned:
        raise BadRequestException(detail="Please enter a valid YouTube video or Short URL.")

    is_short = "/shorts/" in cleaned

    for pattern in YOUTUBE_URL_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            video_id = match.group(1)
            content_type = ContentType.YOUTUBE_SHORT if is_short else ContentType.YOUTUBE_VIDEO
            canonical_url = (
                f"https://www.youtube.com/shorts/{video_id}"
                if is_short
                else f"https://www.youtube.com/watch?v={video_id}"
            )
            return video_id, canonical_url, content_type

    # Also check direct 11-12 character video ID
    if re.fullmatch(r"[a-zA-Z0-9_-]{11,12}", cleaned):
        video_id = cleaned
        canonical_url = f"https://www.youtube.com/watch?v={video_id}"
        return video_id, canonical_url, ContentType.YOUTUBE_VIDEO

    raise BadRequestException(
        detail="Please enter a valid YouTube video or Short URL."
    )


def calculate_engagement_rate(views: Optional[int], likes: Optional[int], comments: Optional[int]) -> float:
    """Deterministic engagement rate formula: (likes + comments) / views * 100."""
    if views is None or views <= 0:
        return 0.0
    likes_val = likes or 0
    comments_val = comments or 0
    return round(((likes_val + comments_val) / views) * 100, 2)


def calculate_performance_lift(campaign_views: int, baseline_views: Optional[float]) -> Optional[float]:
    """Deterministic lift formula: ((campaign_views - baseline_views) / baseline_views) * 100."""
    if baseline_views is None or baseline_views <= 0:
        return None
    return round(((campaign_views - baseline_views) / baseline_views) * 100, 2)


def calculate_engagement_lift(
    engagement_rate: float,
    baseline_engagement_rate: Optional[float],
) -> Optional[float]:
    """Deterministic engagement lift formula: ((engagement_rate - baseline_engagement_rate) / baseline_engagement_rate) * 100."""
    if baseline_engagement_rate is None or baseline_engagement_rate <= 0:
        return None
    return round(((engagement_rate - baseline_engagement_rate) / baseline_engagement_rate) * 100, 2)


def calculate_cost_per_view(agreed_cost: Optional[float], views: int) -> Optional[float]:
    """Deterministic CPV formula: agreed_cost / views.

    Kept at 6 decimal places to maintain micro-precision for sub-rupee / viral views.
    """
    if agreed_cost is None or views <= 0:
        return None
    return round(agreed_cost / views, 6)


def calculate_cpm(agreed_cost: Optional[float], views: int) -> Optional[float]:
    """Deterministic CPM formula: (agreed_cost / views) * 1000.

    Industry standard advertising metric for video impressions.
    """
    if agreed_cost is None or views <= 0:
        return None
    return round((agreed_cost / views) * 1000, 2)


def calculate_cost_per_engagement(agreed_cost: Optional[float], likes: int, comments: int) -> Optional[float]:
    """Deterministic CPE formula: agreed_cost / (likes + comments)."""
    engagements = likes + comments
    if agreed_cost is None or engagements <= 0:
        return None
    return round(agreed_cost / engagements, 2)


def calculate_roas(spend: Optional[float], revenue: Optional[float]) -> Optional[float]:
    """Deterministic ROAS: revenue / spend.
    Example: 180,000 / 50,000 = 3.6x.
    """
    if spend is None or spend <= 0 or revenue is None or revenue < 0:
        return None
    return round(revenue / spend, 2)


def calculate_roi(spend: Optional[float], profit: Optional[float]) -> Optional[float]:
    """Deterministic ROI: ((profit - spend) / spend) * 100.
    Example: (72,000 - 50,000) / 50,000 * 100 = 44.0%.
    Strictly returns None if profit is not provided. Never invent ROI.
    """
    if spend is None or spend <= 0 or profit is None:
        return None
    return round(((profit - spend) / spend) * 100.0, 1)


def calculate_content_age(published_at: Optional[datetime]) -> Tuple[Optional[float], Optional[float], str]:
    """Returns (content_age_hours, content_age_days, content_stage)."""
    if not published_at:
        return None, None, ContentStage.MATURE

    now_dt = datetime.now(timezone.utc)
    pub_dt = published_at if published_at.tzinfo is not None else published_at.replace(tzinfo=timezone.utc)
    diff_sec = (now_dt - pub_dt).total_seconds()
    hours = max(0.0, round(diff_sec / 3600.0, 1))
    days = round(hours / 24.0, 1)

    if hours <= 24.0:
        stage = ContentStage.EARLY_STAGE
    elif hours <= 72.0:
        stage = ContentStage.INITIAL_MOMENTUM
    elif hours <= 168.0:
        stage = ContentStage.SHORT_TERM
    elif hours <= 720.0:
        stage = ContentStage.MATURE
    else:
        stage = ContentStage.LONG_TERM

    return hours, days, stage


def calculate_momentum(snapshots: List[ContentPerformanceSnapshot]) -> str:
    """Calculates view momentum across recent snapshots (RISING, STABLE, SLOWING, INSUFFICIENT_DATA)."""
    if not snapshots or len(snapshots) < 2:
        return ViewMomentum.INSUFFICIENT_DATA

    sorted_snaps = sorted(
        snapshots,
        key=lambda s: s.captured_at if s.captured_at else datetime.min.replace(tzinfo=timezone.utc),
    )

    recent = sorted_snaps[-1]
    prev = sorted_snaps[-2]

    dt_sec = 0.0
    if recent.captured_at and prev.captured_at:
        r_dt = recent.captured_at if recent.captured_at.tzinfo else recent.captured_at.replace(tzinfo=timezone.utc)
        p_dt = prev.captured_at if prev.captured_at.tzinfo else prev.captured_at.replace(tzinfo=timezone.utc)
        dt_sec = (r_dt - p_dt).total_seconds()

    hours = max(1.0, dt_sec / 3600.0)
    views_gained = max(0, recent.views - prev.views)
    velocity = views_gained / hours

    if len(sorted_snaps) >= 3:
        prev2 = sorted_snaps[-3]
        dt_sec_prev = 0.0
        if prev.captured_at and prev2.captured_at:
            p_dt = prev.captured_at if prev.captured_at.tzinfo else prev.captured_at.replace(tzinfo=timezone.utc)
            p2_dt = prev2.captured_at if prev2.captured_at.tzinfo else prev2.captured_at.replace(tzinfo=timezone.utc)
            dt_sec_prev = (p_dt - p2_dt).total_seconds()
        hours_prev = max(1.0, dt_sec_prev / 3600.0)
        vel_prev = max(0, prev.views - prev2.views) / hours_prev
        if velocity > vel_prev * 1.15:
            return ViewMomentum.RISING
        elif velocity < vel_prev * 0.75:
            return ViewMomentum.SLOWING
        return ViewMomentum.STABLE

    if velocity > 500:
        return ViewMomentum.RISING
    elif velocity > 50:
        return ViewMomentum.STABLE
    return ViewMomentum.SLOWING


def classify_performance_status(
    lift_percent: Optional[float],
    engagement_rate: float,
    baseline_engagement_rate: Optional[float],
    published_at: Optional[datetime] = None,
    views: int = 0,
    baseline_views: Optional[float] = None,
    objective: Optional[str] = None,
    roas: Optional[float] = None,
    momentum: Optional[str] = None,
) -> str:
    """Deterministic performance classification layer with recency, momentum, baseline, and objective awareness.

    Never prematurely labels new content (< 24h old) as UNDERPERFORMING.
    """
    days_since_publish: Optional[float] = None
    hours_since_publish: Optional[float] = None
    if published_at is not None:
        now_dt = datetime.now(timezone.utc)
        pub_dt = published_at if published_at.tzinfo is not None else published_at.replace(tzinfo=timezone.utc)
        delta_sec = (now_dt - pub_dt).total_seconds()
        hours_since_publish = max(0.0, delta_sec / 3600.0)
        days_since_publish = max(0.0, delta_sec / 86400.0)

    # RULE 1: Under 24 hours is EARLY_STAGE. Do not penalize against mature historical baselines.
    if hours_since_publish is not None and hours_since_publish <= 24.0:
        if lift_percent is not None and lift_percent >= 50.0:
            return PerformanceStatus.STRONG
        return PerformanceStatus.EARLY_STAGE

    is_early_pacing = days_since_publish is not None and days_since_publish <= 7.0

    obj_str = (objective or "").strip().lower()
    is_conversions_obj = any(k in obj_str for k in ("conversion", "sale", "lead", "revenue"))
    is_awareness_obj = any(k in obj_str for k in ("awareness", "reach", "launch", "brand", "view"))

    # RULE 2: Objective Awareness - Commercial Campaigns (Conversions / Sales)
    if is_conversions_obj and roas is not None:
        if roas >= 3.0:
            return PerformanceStatus.STRONG
        elif roas >= 1.5:
            return PerformanceStatus.ON_TRACK
        elif roas >= 1.0:
            return PerformanceStatus.AVERAGE
        else:  # roas < 1.0
            if days_since_publish is not None and days_since_publish >= 7.0:
                return PerformanceStatus.UNDERPERFORMING
            return PerformanceStatus.NEEDS_ATTENTION

    # RULE 3: Objective Awareness - Awareness Campaigns
    if is_awareness_obj:
        if lift_percent is not None and lift_percent >= 25.0:
            return PerformanceStatus.STRONG
        if (views >= 100_000 or (lift_percent is not None and lift_percent >= 0.0)) and (
            momentum in ("RISING", "STABLE") or engagement_rate >= 3.0
        ):
            return PerformanceStatus.STRONG

    # RULE 4: General Lift & Baseline Evaluation
    if lift_percent is not None:
        if lift_percent >= 30.0:
            return PerformanceStatus.STRONG
        if lift_percent >= 5.0:
            return PerformanceStatus.ON_TRACK
        if lift_percent >= -15.0:
            return PerformanceStatus.AVERAGE
        if lift_percent >= -35.0:
            if is_early_pacing:
                return PerformanceStatus.ON_TRACK
            return PerformanceStatus.NEEDS_ATTENTION

        # lift_percent < -35.0 (significant lag vs normal baseline)
        if is_early_pacing:
            has_strong_eng = (
                baseline_engagement_rate is not None
                and engagement_rate >= (baseline_engagement_rate * 0.85)
            ) or engagement_rate >= 2.5
            if days_since_publish is not None and days_since_publish <= 3.0 and has_strong_eng:
                return PerformanceStatus.ON_TRACK
            if views >= 100_000 or has_strong_eng:
                return PerformanceStatus.AVERAGE
            if momentum == "RISING":
                return PerformanceStatus.AVERAGE

        return PerformanceStatus.UNDERPERFORMING

    if baseline_engagement_rate is not None and baseline_engagement_rate > 0:
        rel_eng = (engagement_rate - baseline_engagement_rate) / baseline_engagement_rate
        if rel_eng >= 0.25:
            return PerformanceStatus.STRONG
        if rel_eng >= 0.0:
            return PerformanceStatus.ON_TRACK
        if rel_eng >= -0.2:
            return PerformanceStatus.AVERAGE
        return PerformanceStatus.UNDERPERFORMING

    return PerformanceStatus.ON_TRACK


class ContentTrackingService:
    def __init__(self, db: AsyncSession, youtube_client: Optional[YouTubeClient] = None) -> None:
        self.db = db
        self.yt = youtube_client or YouTubeClient()

    async def get_agreed_creator_cost(self, campaign_id: str, influencer_id: str) -> Optional[float]:
        """Resolves real creator agreed cost from Contract or negotiated outreach terms.

        Does NOT invent cost. Returns None if unprovided.
        """
        contract_stmt = (
            select(Contract)
            .where(
                Contract.campaign_id == campaign_id,
                Contract.influencer_id == influencer_id,
            )
            .order_by(
                # Prefer approved or signed contracts first
                Contract.status.in_(["APPROVED", "signed"]).desc(),
                Contract.updated_at.desc(),
            )
        )
        c_res = await self.db.execute(contract_stmt)
        contract = c_res.scalars().first()
        if contract and contract.value and contract.value > 0:
            return float(contract.value)

        # Fallback to accepted outreach agreed_terms
        outreach_stmt = (
            select(OutreachMessage)
            .where(
                OutreachMessage.campaign_id == campaign_id,
                OutreachMessage.influencer_id == influencer_id,
            )
            .order_by(OutreachMessage.updated_at.desc())
        )
        o_res = await self.db.execute(outreach_stmt)
        outreach = o_res.scalars().first()
        if outreach and outreach.extracted_terms:
            terms = outreach.extracted_terms
            fee = terms.get("fee") or terms.get("agreed_fee") or terms.get("price") or terms.get("rate")
            if fee is not None:
                try:
                    num_val = float(re.sub(r"[^\d.]", "", str(fee)))
                    if num_val > 0:
                        return num_val
                except (ValueError, TypeError):
                    pass

        return None

    async def calculate_creator_baseline(
        self,
        influencer: Optional[Influencer] = None,
        exclude_video_id: str = "",
        is_short: bool = False,
        channel_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetches 5–10 recent uploads before/around campaign content and calculates median & average baseline.

        Excludes the tracked video itself. Where practical, compares Short vs Shorts and Video vs Videos.
        """
        target_channel_id = channel_id or (influencer.external_id if influencer else None)
        if not target_channel_id or not self.yt.is_configured:
            return {
                "median_views": None,
                "avg_views": None,
                "avg_likes": None,
                "avg_comments": None,
                "engagement_rate": None,
                "sample_size": 0,
                "video_ids": [],
            }

        try:
            channels_res = await self.yt.get_channels_by_id([target_channel_id])
            if not channels_res.items:
                return {
                    "median_views": None,
                    "avg_views": None,
                    "avg_likes": None,
                    "avg_comments": None,
                    "engagement_rate": None,
                    "sample_size": 0,
                    "video_ids": [],
                }

            channel_item = channels_res.items[0]
            uploads_playlist = (
                channel_item.contentDetails.relatedPlaylists.uploads
                if channel_item.contentDetails and channel_item.contentDetails.relatedPlaylists
                else None
            )
            if not uploads_playlist:
                return {
                    "median_views": None,
                    "avg_views": None,
                    "avg_likes": None,
                    "avg_comments": None,
                    "engagement_rate": None,
                    "sample_size": 0,
                    "video_ids": [],
                }

            # Fetch up to 20 recent playlist items to allow filtering by content type and excluding current video
            recent_ids = await self.yt.get_playlist_items(uploads_playlist, max_results=20)
            candidate_ids = [vid for vid in recent_ids if vid != exclude_video_id]

            if not candidate_ids:
                return {
                    "median_views": None,
                    "avg_views": None,
                    "avg_likes": None,
                    "avg_comments": None,
                    "engagement_rate": None,
                    "sample_size": 0,
                    "video_ids": [],
                }

            video_stats = await self.yt.get_videos_statistics(candidate_ids)

            # Exclude immature uploads published in the last 48 hours to avoid skewing baseline with incomplete views
            now_dt = datetime.now(timezone.utc)
            mature_stats = []
            for v in video_stats:
                pub_str = v.get("published_at")
                if pub_str:
                    try:
                        pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                        if (now_dt - pub_dt).total_seconds() < 48 * 3600:
                            continue
                    except Exception:
                        pass
                mature_stats.append(v)

            usable_stats = mature_stats if len(mature_stats) >= 3 else video_stats

            # Content type filtering: if tracked is Short, prefer comparable Shorts (<= 60s)
            comparable_stats = []
            if is_short:
                shorts = [v for v in usable_stats if v.get("is_short")]
                comparable_stats = shorts if len(shorts) >= 3 else usable_stats
            else:
                longform = [v for v in usable_stats if not v.get("is_short")]
                comparable_stats = longform if len(longform) >= 3 else usable_stats

            sample = comparable_stats[:10]
            if not sample:
                sample = usable_stats[:10]

            if not sample:
                return {
                    "median_views": None,
                    "avg_views": None,
                    "avg_likes": None,
                    "avg_comments": None,
                    "engagement_rate": None,
                    "sample_size": 0,
                    "video_ids": [],
                }

            views_list = [v.get("view_count", 0) for v in sample]
            likes_list = [v.get("like_count", 0) for v in sample]
            comments_list = [v.get("comment_count", 0) for v in sample]

            n = len(sample)
            med_views = float(statistics.median(views_list))
            avg_views = float(sum(views_list) / n)
            avg_likes = float(sum(likes_list) / n)
            avg_comments = float(sum(comments_list) / n)
            total_views = sum(views_list)
            total_eng = sum(likes_list) + sum(comments_list)
            avg_eng_rate = round((total_eng / total_views * 100), 2) if total_views > 0 else 0.0

            return {
                "median_views": med_views,
                "avg_views": avg_views,
                "avg_likes": avg_likes,
                "avg_comments": avg_comments,
                "engagement_rate": avg_eng_rate,
                "sample_size": n,
                "video_ids": [v.get("id") for v in sample if v.get("id")],
            }

        except Exception as exc:
            logger.warning("Could not calculate creator baseline for channel %s: %s", target_channel_id, exc)
            return {
                "median_views": None,
                "avg_views": None,
                "avg_likes": None,
                "avg_comments": None,
                "engagement_rate": None,
                "sample_size": 0,
                "video_ids": [],
            }

    async def track_content(
        self,
        *,
        campaign: Campaign,
        influencer: Influencer,
        content_url: str,
        content_type_override: Optional[str] = None,
    ) -> CampaignContent:
        """Validates YouTube URL, verifies creator ownership, fetches real public metrics,

        computes baseline, calculates deterministic KPIs, and stores initial snapshot.
        """
        video_id, canonical_url, inferred_type = extract_youtube_video_id(content_url)
        content_type = content_type_override or inferred_type

        # 1. Fetch real YouTube video details
        try:
            video_data = await self.yt.get_video_details(video_id)
        except YouTubeAPIError as exc:
            raise BadRequestException(detail=f"YouTube Data API error: {exc}")

        if not video_data:
            raise NotFoundException(detail="This YouTube video is private or unavailable.")

        # 2. Creator channel mismatch verification & Demo Mode
        video_channel_id = video_data.get("channel_id")
        video_channel_title = video_data.get("channel_title") or "Unknown"
        expected_channel_id = influencer.external_id if influencer else None

        # Resolve expected channel ID if stored as a handle or username instead of UC...
        if expected_channel_id and not expected_channel_id.startswith("UC"):
            try:
                ch_resp = await self.yt.get_channels_by_handle(expected_channel_id)
                if ch_resp.items:
                    expected_channel_id = ch_resp.items[0].id
            except Exception as exc:
                logger.warning("Could not resolve channel handle %s: %s", expected_channel_id, exc)

        if (not expected_channel_id or not expected_channel_id.startswith("UC")) and influencer and influencer.username:
            try:
                ch_resp = await self.yt.get_channels_by_handle(influencer.username)
                if ch_resp.items:
                    expected_channel_id = ch_resp.items[0].id
            except Exception as exc:
                logger.warning("Could not resolve channel username %s: %s", influencer.username, exc)

        is_demo = bool(settings.PERFORMANCE_DEMO_MODE)

        if not is_demo:
            if not video_channel_id or not expected_channel_id or video_channel_id.strip().lower() != expected_channel_id.strip().lower():
                raise BadRequestException(
                    detail="This video does not belong to the selected shortlisted creator. Please provide a video or Short published by this creator."
                )

        # Determine if short from duration or URL
        is_short = video_data.get("is_short") or (content_type == ContentType.YOUTUBE_SHORT)
        if is_short:
            content_type = ContentType.YOUTUBE_SHORT

        # 3. Calculate creator baseline (use the real channel of the video)
        baseline_channel_id = video_channel_id or expected_channel_id
        baseline = await self.calculate_creator_baseline(
            influencer=influencer,
            exclude_video_id=video_id,
            is_short=is_short,
            channel_id=baseline_channel_id,
        )

        # 4. Resolve agreed creator cost
        agreed_cost = await self.get_agreed_creator_cost(campaign.id, influencer.id)

        published_at_dt = None
        if video_data.get("published_at"):
            try:
                published_at_dt = datetime.fromisoformat(video_data["published_at"].replace("Z", "+00:00"))
            except Exception:
                published_at_dt = None

        # 5. Calculate factual KPIs
        views = video_data.get("view_count", 0)
        likes = video_data.get("like_count", 0)
        comments = video_data.get("comment_count", 0)

        eng_rate = calculate_engagement_rate(views, likes, comments)
        perf_lift = calculate_performance_lift(views, baseline.get("median_views"))
        cpv = calculate_cost_per_view(agreed_cost, views)
        cpe = calculate_cost_per_engagement(agreed_cost, likes, comments)
        status = classify_performance_status(
            perf_lift,
            eng_rate,
            baseline.get("engagement_rate"),
            published_at=published_at_dt,
            views=views,
            baseline_views=baseline.get("median_views"),
        )

        # Check if this content is already registered for this campaign
        existing_stmt = select(CampaignContent).where(
            CampaignContent.campaign_id == campaign.id,
            CampaignContent.external_content_id == video_id,
        )
        existing_res = await self.db.execute(existing_stmt)
        content = existing_res.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if not content:
            content = CampaignContent(
                user_id=campaign.owner_id,
                campaign_id=campaign.id,
                influencer_id=influencer.id,
                platform="youtube",
                content_type=content_type,
                external_content_id=video_id,
                content_url=canonical_url,
                is_demo=is_demo,
                title=video_data.get("title"),
                thumbnail_url=video_data.get("thumbnail_url"),
                channel_id=video_channel_id,
                channel_title=video_channel_title,
                published_at=published_at_dt,
                duration_seconds=video_data.get("duration_seconds"),
                tracking_status=TrackingStatus.ACTIVE,
                agreed_cost=agreed_cost,
                currency="INR",
                last_sync_at=now,
                sync_error=None,
                baseline_median_views=baseline.get("median_views"),
                baseline_avg_views=baseline.get("avg_views"),
                baseline_avg_likes=baseline.get("avg_likes"),
                baseline_avg_comments=baseline.get("avg_comments"),
                baseline_engagement_rate=baseline.get("engagement_rate"),
                baseline_sample_size=baseline.get("sample_size"),
                baseline_video_ids=baseline.get("video_ids"),
                current_views=views,
                current_likes=likes,
                current_comments=comments,
                engagement_rate=eng_rate,
                performance_lift_percent=perf_lift,
                cost_per_view=cpv,
                cost_per_engagement=cpe,
                performance_status=status,
            )
            self.db.add(content)
            await self.db.flush()
        else:
            content.user_id = campaign.owner_id
            content.is_demo = is_demo
            content.content_type = content_type
            content.title = video_data.get("title") or content.title
            content.thumbnail_url = video_data.get("thumbnail_url") or content.thumbnail_url
            content.channel_id = video_channel_id or content.channel_id
            content.channel_title = video_channel_title or content.channel_title
            content.duration_seconds = video_data.get("duration_seconds") or content.duration_seconds
            content.tracking_status = TrackingStatus.ACTIVE
            content.agreed_cost = agreed_cost if agreed_cost is not None else content.agreed_cost
            content.last_sync_at = now
            content.sync_error = None
            content.baseline_median_views = baseline.get("median_views") or content.baseline_median_views
            content.baseline_avg_views = baseline.get("avg_views") or content.baseline_avg_views
            content.baseline_avg_likes = baseline.get("avg_likes") or content.baseline_avg_likes
            content.baseline_avg_comments = baseline.get("avg_comments") or content.baseline_avg_comments
            content.baseline_engagement_rate = baseline.get("engagement_rate") or content.baseline_engagement_rate
            content.baseline_sample_size = baseline.get("sample_size") or content.baseline_sample_size
            content.baseline_video_ids = baseline.get("video_ids") or content.baseline_video_ids
            content.current_views = views
            content.current_likes = likes
            content.current_comments = comments
            content.engagement_rate = eng_rate
            content.performance_lift_percent = perf_lift
            content.cost_per_view = cpv
            content.cost_per_engagement = cpe
            content.performance_status = status
            await self.db.flush()

        # Save initial or updated snapshot
        snapshot = ContentPerformanceSnapshot(
            campaign_content_id=content.id,
            views=views,
            likes=likes,
            comments=comments,
            view_growth_absolute=0,
            view_growth_percentage=0.0,
            engagement_growth=0,
            captured_at=now,
        )
        self.db.add(snapshot)
        await self.db.flush()

        # Update campaign status to active if live tracking begins
        if campaign.status in ("planning", "ready"):
            campaign.status = "active"
        if campaign.workflow_state in ("CAMPAIGN_LIVE", "CONTRACT_COMPLETED"):
            campaign.workflow_state = "PERFORMANCE_MONITORING"
        await self.db.flush()

        # Reconcile and persist campaign aggregates (spend, reach, influencers, ROAS)
        await self.sync_campaign_metrics(campaign.id)

        await self.db.commit()
        await self.db.refresh(content)
        return content

    async def refresh_content_metrics(self, content_id: str) -> CampaignContent:
        """Fetches latest real YouTube metrics for a tracked content item,

        creates a timestamped snapshot, calculates momentum, and recalculates KPIs.
        """
        content_stmt = select(CampaignContent).where(CampaignContent.id == content_id)
        c_res = await self.db.execute(content_stmt)
        content = c_res.scalar_one_or_none()
        if not content:
            raise NotFoundException(detail=f"Tracked content '{content_id}' not found.")

        now = datetime.now(timezone.utc)

        try:
            video_data = await self.yt.get_video_details(content.external_content_id)
            if not video_data:
                content.tracking_status = TrackingStatus.SYNC_FAILED
                content.sync_error = "This YouTube video is private or unavailable."
                await self.db.commit()
                await self.db.refresh(content)
                return content
        except YouTubeAPIError as exc:
            if exc.status_code == 429 or "quota" in str(exc).lower():
                logger.warning("YouTube API quota exceeded during refresh: %s", exc)
                content.sync_error = "YouTube API quota exceeded for today. Displaying last stored PostgreSQL snapshot."
                await self.db.commit()
                await self.db.refresh(content)
                return content
            content.tracking_status = TrackingStatus.SYNC_FAILED
            content.sync_error = str(exc)[:500]
            await self.db.commit()
            await self.db.refresh(content)
            return content
        except Exception as exc:
            content.tracking_status = TrackingStatus.SYNC_FAILED
            content.sync_error = str(exc)[:500]
            await self.db.commit()
            await self.db.refresh(content)
            return content

        new_views = video_data.get("view_count", 0)
        new_likes = video_data.get("like_count", 0)
        new_comments = video_data.get("comment_count", 0)

        # Get latest previous snapshot to compute momentum
        snap_stmt = (
            select(ContentPerformanceSnapshot)
            .where(ContentPerformanceSnapshot.campaign_content_id == content.id)
            .order_by(desc(ContentPerformanceSnapshot.captured_at))
            .limit(1)
        )
        s_res = await self.db.execute(snap_stmt)
        prev_snapshot = s_res.scalar_one_or_none()

        growth_abs = 0
        growth_pct = 0.0
        eng_growth = 0

        if prev_snapshot:
            growth_abs = new_views - prev_snapshot.views
            growth_pct = (
                round(((new_views - prev_snapshot.views) / prev_snapshot.views) * 100, 2)
                if prev_snapshot.views > 0
                else 0.0
            )
            eng_growth = (new_likes + new_comments) - (prev_snapshot.likes + prev_snapshot.comments)

        # Record new snapshot
        new_snapshot = ContentPerformanceSnapshot(
            campaign_content_id=content.id,
            views=new_views,
            likes=new_likes,
            comments=new_comments,
            view_growth_absolute=growth_abs,
            view_growth_percentage=growth_pct,
            engagement_growth=eng_growth,
            captured_at=now,
        )
        self.db.add(new_snapshot)

        # Recalculate KPIs with recency awareness
        eng_rate = calculate_engagement_rate(new_views, new_likes, new_comments)
        perf_lift = calculate_performance_lift(new_views, content.baseline_median_views)
        cpv = calculate_cost_per_view(content.agreed_cost, new_views)
        cpe = calculate_cost_per_engagement(content.agreed_cost, new_likes, new_comments)
        status = classify_performance_status(
            perf_lift,
            eng_rate,
            content.baseline_engagement_rate,
            published_at=content.published_at,
            views=new_views,
            baseline_views=content.baseline_median_views,
        )

        content.current_views = new_views
        content.current_likes = new_likes
        content.current_comments = new_comments
        content.engagement_rate = eng_rate
        content.performance_lift_percent = perf_lift
        content.cost_per_view = cpv
        content.cost_per_engagement = cpe
        content.performance_status = status
        content.last_sync_at = now
        content.tracking_status = TrackingStatus.ACTIVE
        content.sync_error = None
        if video_data.get("title"):
            content.title = video_data["title"]
        if video_data.get("thumbnail_url"):
            content.thumbnail_url = video_data["thumbnail_url"]

        await self.db.flush()

        # Reconcile and persist campaign aggregates (spend, reach, influencers, ROAS)
        await self.sync_campaign_metrics(content.campaign_id)

        await self.db.commit()
        await self.db.refresh(content)
        return content

    async def sync_campaign_metrics(self, campaign_id: str) -> None:
        """Recalculates and persists ground-truth aggregates (spend, reach, influencers, ROAS) on the Campaign entity."""
        camp_stmt = select(Campaign).where(Campaign.id == campaign_id)
        camp_res = await self.db.execute(camp_stmt)
        campaign = camp_res.scalar_one_or_none()
        if not campaign:
            return

        # 1. Total tracked content spend and reach
        content_stmt = select(
            func.coalesce(func.sum(CampaignContent.agreed_cost), 0.0),
            func.coalesce(func.sum(CampaignContent.current_views), 0),
            func.count(func.distinct(CampaignContent.influencer_id)),
        ).where(
            CampaignContent.campaign_id == campaign_id,
            CampaignContent.tracking_status.in_([TrackingStatus.ACTIVE, TrackingStatus.TRACKING]),
        )
        c_res = await self.db.execute(content_stmt)
        row = c_res.first()
        tracked_spend = float(row[0]) if row and row[0] is not None else 0.0
        tracked_reach = int(row[1]) if row and row[1] is not None else 0
        tracked_creators = int(row[2]) if row and row[2] is not None else 0

        # 2. Approved/signed contracts spend
        contract_stmt = select(
            func.coalesce(func.sum(Contract.value), 0.0),
            func.count(func.distinct(Contract.influencer_id)),
        ).where(
            Contract.campaign_id == campaign_id,
            Contract.status.in_(["APPROVED", "signed"]),
        )
        cntr_res = await self.db.execute(contract_stmt)
        cntr_row = cntr_res.first()
        contract_spend = float(cntr_row[0]) if cntr_row and cntr_row[0] is not None else 0.0
        contracted_creators = int(cntr_row[1]) if cntr_row and cntr_row[1] is not None else 0

        # 3. Sum attributed revenue from all campaign contents
        rev_stmt = select(
            func.coalesce(func.sum(CampaignContent.attributed_revenue), 0.0),
        ).where(
            CampaignContent.campaign_id == campaign_id,
        )
        rev_res = await self.db.execute(rev_stmt)
        rev_row = rev_res.first()
        total_attributed_revenue = float(rev_row[0]) if rev_row and rev_row[0] is not None else 0.0

        effective_spend = max(tracked_spend, contract_spend, campaign.spend or 0.0)
        effective_reach = max(tracked_reach, campaign.reach or 0)
        effective_creators = max(tracked_creators, contracted_creators, campaign.influencers or 0)

        campaign.spend = effective_spend
        campaign.reach = effective_reach
        campaign.influencers = effective_creators
        if total_attributed_revenue > 0:
            campaign.revenue = total_attributed_revenue

        if campaign.revenue and campaign.revenue > 0 and effective_spend > 0:
            campaign.roas = round(campaign.revenue / effective_spend, 2)
        elif effective_spend > 0 and (not campaign.revenue or campaign.revenue <= 0):
            campaign.roas = 0.0

        await self.db.flush()

    async def update_content_attribution(
        self,
        *,
        content_id: str,
        attributed_revenue: Optional[float] = None,
        attributed_orders: Optional[int] = None,
        average_order_value: Optional[float] = None,
        gross_margin_percent: Optional[float] = None,
        attributed_profit: Optional[float] = None,
        attribution_source: Optional[str] = None,
    ) -> CampaignContent:
        """Saves business attribution results deterministically in database and updates KPIs."""
        c_stmt = (
            select(CampaignContent)
            .options(selectinload(CampaignContent.snapshots), selectinload(CampaignContent.influencer))
            .where(CampaignContent.id == content_id)
        )
        res = await self.db.execute(c_stmt)
        content = res.scalar_one_or_none()
        if not content:
            raise NotFoundException(detail=f"Tracked content '{content_id}' not found.")

        # Determine revenue: Option A (direct revenue) vs Option B (orders * AOV)
        final_revenue = attributed_revenue
        if final_revenue is None or final_revenue < 0:
            if (
                attributed_orders is not None
                and attributed_orders >= 0
                and average_order_value is not None
                and average_order_value >= 0
            ):
                final_revenue = round(float(attributed_orders) * float(average_order_value), 2)

        # Determine profit: direct profit vs margin %
        final_profit = attributed_profit
        if final_profit is None:
            if (
                gross_margin_percent is not None
                and 0.0 <= gross_margin_percent <= 100.0
                and final_revenue is not None
            ):
                final_profit = round(final_revenue * (gross_margin_percent / 100.0), 2)

        content.attributed_revenue = final_revenue
        content.attributed_orders = attributed_orders
        content.average_order_value = average_order_value
        content.gross_margin_percent = gross_margin_percent
        content.attributed_profit = final_profit
        if attribution_source:
            content.attribution_source = attribution_source
        content.attribution_updated_at = datetime.now(timezone.utc)

        # Recalculate status with campaign objective, roas, and momentum
        camp_stmt = select(Campaign).where(Campaign.id == content.campaign_id)
        camp_res = await self.db.execute(camp_stmt)
        campaign = camp_res.scalar_one_or_none()
        objective = campaign.objective if campaign else None

        content.performance_status = classify_performance_status(
            content.performance_lift_percent,
            content.engagement_rate or 0.0,
            content.baseline_engagement_rate,
            published_at=content.published_at,
            views=content.current_views,
            baseline_views=content.baseline_median_views,
            objective=objective,
            roas=content.roas,
            momentum=content.momentum,
        )

        await self.db.flush()
        await self.sync_campaign_metrics(content.campaign_id)
        await self.db.commit()
        await self.db.refresh(content)
        return content
