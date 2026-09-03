"""Factual recent-performance signals from YouTube-derived metrics.

Never invent views. High subscriber count alone is not a trend.
Auralytics Trend Score is an internal ranking signal, not a YouTube metric.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def compute_trend_signals(
    *,
    followers: int,
    avg_views: int,
    engagement_rate: float = 0.0,
    recent_max_views: int = 0,
    recent_median_views: int = 0,
    last_upload_at: Optional[datetime] = None,
    metrics_sample_size: int = 0,
) -> Dict[str, Any]:
    """Backend-only momentum from stored YouTube stats."""
    followers = max(0, _as_int(followers))
    avg_views = max(0, _as_int(avg_views))
    recent_max_views = max(0, _as_int(recent_max_views))
    recent_median_views = max(0, _as_int(recent_median_views))
    sample = _as_int(metrics_sample_size)
    current_views = recent_median_views or avg_views
    if sample <= 0:
        current_views = 0
    ratio = (current_views / followers) if followers > 0 and current_views > 0 else 0.0
    recency_days: Optional[int] = None
    if last_upload_at is not None:
        now = datetime.now(timezone.utc)
        stamp = last_upload_at if last_upload_at.tzinfo else last_upload_at.replace(tzinfo=timezone.utc)
        recency_days = max(0, int((now - stamp).total_seconds() // 86400))

    recent_view_score = 0.0
    if sample > 0 and current_views > 0:
        recent_view_score = min(35.0, (current_views / 15000.0) * 3.5)
        if followers > 0:
            recent_view_score += min(15.0, ratio * 40.0)

    views_to_subscribers_score = min(20.0, ratio * 50.0) if followers > 0 else 0.0
    recent_engagement_score = min(15.0, _as_float(engagement_rate) * 2.0)
    upload_recency_score = 0.0
    if recency_days is not None:
        if recency_days <= 14:
            upload_recency_score = 15.0
        elif recency_days <= 45:
            upload_recency_score = 8.0
        elif recency_days > 180:
            upload_recency_score = -10.0
    consistency_score = 10.0 if sample >= 5 else (5.0 if sample > 0 else 0.0)
    momentum_bonus = 0.0
    if recent_max_views > 0 and followers > 0:
        momentum_bonus = min(15.0, (recent_max_views / followers) * 20.0)

    trend_score = (
        recent_view_score
        + views_to_subscribers_score * 0.5
        + recent_engagement_score
        + upload_recency_score
        + consistency_score
        + momentum_bonus
    )
    trend_score = round(max(0.0, min(100.0, trend_score)), 2)

    if trend_score >= 55 or ratio >= 0.4:
        label = "HIGH"
    elif trend_score >= 28 or ratio >= 0.12:
        label = "MEDIUM"
    elif sample <= 0 or current_views <= 0:
        label = "UNKNOWN"
    else:
        label = "LOW"

    return {
        "recent_avg_views": avg_views if sample > 0 else 0,
        "recent_median_views": recent_median_views,
        "recent_max_views": recent_max_views,
        "views_to_subscriber_ratio": round(ratio, 4),
        "recent_engagement": round(_as_float(engagement_rate), 4),
        "upload_recency_days": recency_days,
        "posting_consistency": "KNOWN" if sample >= 5 else ("PARTIAL" if sample > 0 else "UNKNOWN"),
        "recent_view_score": round(max(0.0, recent_view_score), 2),
        "recent_engagement_score": round(max(0.0, recent_engagement_score), 2),
        "views_to_subscribers_score": round(max(0.0, views_to_subscribers_score), 2),
        "upload_recency_score": round(upload_recency_score, 2),
        "consistency_score": round(consistency_score, 2),
        "recent_momentum_score": trend_score,
        "auralytics_trend_score": trend_score,
        "recent_momentum": label,
    }
