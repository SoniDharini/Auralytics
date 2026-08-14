import logging
from typing import Any, Dict, List, Optional
from app.integrations.instagram.client import InstagramAPIError, InstagramClient
from app.integrations.instagram.mapper import map_instagram_profile_to_creator
from app.integrations.social_provider import ContentMetrics, NormalizedCreator, SocialProvider

logger = logging.getLogger(__name__)


class InstagramProvider(SocialProvider):
    def __init__(self, client: Optional[InstagramClient] = None):
        self.client = client or InstagramClient()

    @property
    def platform_name(self) -> str:
        return "instagram"

    def is_configured(self) -> bool:
        return self.client.is_configured

    async def search_creators(
        self,
        queries: List[str],
        limit: int = 25,
        target_country: Optional[str] = None,
    ) -> List[NormalizedCreator]:
        if not self.is_configured():
            logger.info("Instagram provider is not configured; skipping Instagram creator discovery.")
            return []

        try:
            profile = await self.client.get_user_profile("me")
            media_resp = await self.client.get_user_media("me", limit=15)
            creator = map_instagram_profile_to_creator(profile, media_items=media_resp.data)
            return [creator]
        except InstagramAPIError as exc:
            logger.warning(f"Instagram search error: {exc}")
            return []
        except Exception as exc:
            logger.error(f"Unexpected error in Instagram provider: {exc}")
            return []

    async def get_creator(self, external_id: str) -> Optional[NormalizedCreator]:
        if not self.is_configured():
            return None

        try:
            profile = await self.client.get_user_profile(external_id)
            media_resp = await self.client.get_user_media(external_id, limit=15)
            return map_instagram_profile_to_creator(profile, media_items=media_resp.data)
        except Exception as exc:
            logger.error(f"Error fetching Instagram creator {external_id}: {exc}")
            return None

    async def get_recent_content_metrics(self, external_id: str) -> Optional[ContentMetrics]:
        if not self.is_configured():
            return None

        try:
            profile = await self.client.get_user_profile(external_id)
            media_resp = await self.client.get_user_media(external_id, limit=15)
            media = media_resp.data
            if not media:
                return None

            n = len(media)
            sum_likes = sum(m.like_count or 0 for m in media)
            sum_comments = sum(m.comments_count or 0 for m in media)

            avg_likes = int(sum_likes / n)
            avg_comments = int(sum_comments / n)
            followers = profile.followers_count or 0
            engagement_rate = round(((avg_likes + avg_comments) / followers) * 100, 2) if followers > 0 else 0.0

            return ContentMetrics(
                avg_views=0,
                avg_likes=avg_likes,
                avg_comments=avg_comments,
                engagement_rate=engagement_rate,
                sample_size=n,
            )
        except Exception as exc:
            logger.error(f"Error calculating Instagram content metrics: {exc}")
            return None
