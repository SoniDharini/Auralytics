from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.integrations.social_provider import ContentMetrics, NormalizedCreator
from app.integrations.youtube.schemas import YouTubeChannelItem

# Marks averages Auralytics computed itself rather than values reported by YouTube.
DERIVED_METRIC_SOURCE = "auralytics_calculated"


def _parse_published_at(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def map_youtube_channel_to_creator(
    channel: YouTubeChannelItem,
    video_stats: Optional[List[Dict[str, Any]]] = None,
    derived_niches: Optional[List[str]] = None,
) -> NormalizedCreator:
    snippet = channel.snippet
    statistics = channel.statistics

    name = snippet.title if snippet else "YouTube Channel"
    description = snippet.description if snippet else ""
    custom_url = snippet.customUrl if snippet and snippet.customUrl else None
    username = custom_url if custom_url else f"@{name.replace(' ', '').lower()}"

    avatar = None
    if snippet and snippet.thumbnails:
        thumbnails = snippet.thumbnails
        avatar = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
        )

    profile_url = (
        f"https://www.youtube.com/{custom_url}"
        if custom_url
        else f"https://www.youtube.com/channel/{channel.id}"
    )

    country = snippet.country if snippet and snippet.country else None
    location = country

    followers = 0
    total_views = 0
    content_count = 0
    if statistics:
        try:
            followers = int(statistics.subscriberCount) if not statistics.hiddenSubscriberCount else 0
        except (ValueError, TypeError):
            followers = 0
        try:
            total_views = int(statistics.viewCount)
        except (ValueError, TypeError):
            total_views = 0
        try:
            content_count = int(statistics.videoCount)
        except (ValueError, TypeError):
            content_count = 0

    avg_views = 0
    avg_likes = 0
    avg_comments = 0
    engagement_rate = 0.0
    metrics_source: Optional[str] = None
    metrics_sample_size = 0
    last_upload_at: Optional[datetime] = None

    if video_stats and len(video_stats) > 0:
        n = len(video_stats)
        sum_views = sum(v.get("view_count", 0) for v in video_stats)
        sum_likes = sum(v.get("like_count", 0) for v in video_stats)
        sum_comments = sum(v.get("comment_count", 0) for v in video_stats)

        avg_views = int(sum_views / n)
        avg_likes = int(sum_likes / n)
        avg_comments = int(sum_comments / n)
        metrics_sample_size = n
        metrics_source = DERIVED_METRIC_SOURCE

        published_dates = [d for d in (_parse_published_at(v.get("published_at")) for v in video_stats) if d]
        if published_dates:
            last_upload_at = max(published_dates)

        if followers > 0:
            engagement_rate = round(((avg_likes + avg_comments) / followers) * 100, 2)
    elif content_count > 0 and total_views > 0:
        # Lifetime average across all uploads; weaker than a recent-video sample but still real.
        avg_views = int(total_views / content_count)
        metrics_source = DERIVED_METRIC_SOURCE

    recent_titles = [
        str(v.get("title")).strip()
        for v in (video_stats or [])
        if v.get("title") and str(v.get("title")).strip()
    ]
    raw_payload = {
        "channel_id": channel.id,
        "kind": channel.kind,
        "snippet": snippet.model_dump() if snippet else {},
        "statistics": statistics.model_dump() if statistics else {},
        "recent_video_sample_count": len(video_stats) if video_stats else 0,
        "recent_video_titles": recent_titles[:15],
    }

    return NormalizedCreator(
        external_id=channel.id,
        platform="youtube",
        username=username,
        name=name,
        description=description or None,
        avatar=avatar,
        thumbnail_url=avatar,
        profile_url=profile_url,
        country=country,
        location=location,
        verified=False,
        niches=derived_niches or [],
        followers=followers,
        total_views=total_views,
        content_count=content_count,
        avg_views=avg_views,
        avg_likes=avg_likes,
        avg_comments=avg_comments,
        engagement_rate=engagement_rate,
        data_source="youtube",
        raw_payload=raw_payload,
        metrics_source=metrics_source,
        metrics_sample_size=metrics_sample_size,
        last_upload_at=last_upload_at,
    )
