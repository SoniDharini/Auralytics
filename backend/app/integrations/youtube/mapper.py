from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from app.integrations.social_provider import ContentMetrics, NormalizedCreator
from app.integrations.youtube.schemas import YouTubeChannelItem

# Marks averages Auralytics computed itself rather than values reported by YouTube.
DERIVED_METRIC_SOURCE = "auralytics_calculated"


def sanitize_https_media_url(url: Optional[str]) -> Optional[str]:
    """Keep a single absolute https URL. Never prepend the API host or disable TLS."""
    if not url or not isinstance(url, str):
        return None
    text = url.strip()
    if not text:
        return None
    lowered = text.lower()
    if "https://" in lowered[8:]:
        text = text[text.lower().rfind("https://") :]
        lowered = text.lower()
    elif lowered.startswith("http://https://"):
        text = "https://" + text.split("://", 1)[-1]
        lowered = text.lower()
    if lowered.startswith("//"):
        text = "https:" + text
        lowered = text.lower()
    if not lowered.startswith("https://"):
        return None
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    if not host or host in {"localhost", "127.0.0.1"}:
        return None
    return text


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
        avatar = sanitize_https_media_url(
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
        view_counts = []
        for item in video_stats:
            try:
                view_counts.append(int(item.get("view_count") or 0))
            except (TypeError, ValueError):
                view_counts.append(0)
        sum_views = sum(view_counts)
        sum_likes = sum(v.get("like_count", 0) for v in video_stats)
        sum_comments = sum(v.get("comment_count", 0) for v in video_stats)
        ordered = sorted(view_counts)
        if n >= 5:
            trimmed = ordered[1:-1]
            avg_views = int(sum(trimmed) / len(trimmed)) if trimmed else 0
        elif n >= 3:
            avg_views = ordered[n // 2]
        else:
            avg_views = int(sum_views / n) if n else 0
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
    recent_view_counts = []
    for item in video_stats or []:
        try:
            recent_view_counts.append(int(item.get("view_count") or 0))
        except (TypeError, ValueError):
            continue
    raw_payload = {
        "channel_id": channel.id,
        "kind": channel.kind,
        "snippet": snippet.model_dump() if snippet else {},
        "statistics": statistics.model_dump() if statistics else {},
        "recent_video_sample_count": len(video_stats) if video_stats else 0,
        "recent_video_titles": recent_titles[:15],
        "recent_max_views": max(recent_view_counts) if recent_view_counts else 0,
        "recent_view_counts": recent_view_counts[:15],
        "recent_median_views": int(sorted(recent_view_counts)[len(recent_view_counts) // 2]) if recent_view_counts else 0,
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
