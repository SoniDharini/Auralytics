from typing import List, Optional
from app.integrations.instagram.schemas import InstagramMediaItem, InstagramUserProfile
from app.integrations.social_provider import NormalizedCreator


def map_instagram_profile_to_creator(
    profile: InstagramUserProfile,
    media_items: Optional[List[InstagramMediaItem]] = None,
) -> NormalizedCreator:
    username = f"@{profile.username.lstrip('@')}" if profile.username else "@instagram_creator"
    name = profile.name or profile.username or "Instagram Creator"
    avatar = profile.profile_picture_url
    profile_url = f"https://www.instagram.com/{profile.username.lstrip('@')}" if profile.username else None

    followers = profile.followers_count or 0
    content_count = profile.media_count or 0

    avg_views = 0
    avg_likes = 0
    avg_comments = 0
    engagement_rate = 0.0

    if media_items and len(media_items) > 0:
        n = len(media_items)
        sum_likes = sum(m.like_count or 0 for m in media_items)
        sum_comments = sum(m.comments_count or 0 for m in media_items)

        avg_likes = int(sum_likes / n)
        avg_comments = int(sum_comments / n)

        if followers > 0:
            engagement_rate = round(((avg_likes + avg_comments) / followers) * 100, 2)

    raw_payload = {
        "user_id": profile.id,
        "profile": profile.model_dump(),
        "recent_media_count": len(media_items) if media_items else 0,
    }

    return NormalizedCreator(
        external_id=profile.id,
        platform="instagram",
        username=username,
        name=name,
        description=profile.biography or None,
        avatar=avatar,
        thumbnail_url=avatar,
        profile_url=profile_url,
        country=None,
        location=None,
        verified=False,
        niches=[],
        followers=followers,
        total_views=0,
        content_count=content_count,
        avg_views=avg_views,
        avg_likes=avg_likes,
        avg_comments=avg_comments,
        engagement_rate=engagement_rate,
        data_source="instagram",
        raw_payload=raw_payload,
    )
