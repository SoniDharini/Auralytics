"""Provider registry and single-creator statistics refresh.

Campaign-wide discovery lives in `creator_discovery_service.CreatorDiscoveryService`.
This module keeps the platform provider lookup and the targeted "refresh one creator"
operation used by the influencer detail view.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.integrations.social_provider import SocialProvider
from app.integrations.youtube.service import YouTubeProvider
from app.integrations.instagram.service import InstagramProvider
from app.integrations.youtube.mapper import DERIVED_METRIC_SOURCE
from app.models.influencer import Influencer

logger = logging.getLogger(__name__)


class InfluencerIngestionService:
    def __init__(
        self,
        youtube_provider: Optional[YouTubeProvider] = None,
        instagram_provider: Optional[InstagramProvider] = None,
    ):
        self.youtube_provider = youtube_provider or YouTubeProvider()
        self.instagram_provider = instagram_provider or InstagramProvider()

    def get_provider(self, platform_name: str) -> Optional[SocialProvider]:
        if platform_name.lower() == "youtube":
            return self.youtube_provider
        if platform_name.lower() == "instagram":
            return self.instagram_provider
        return None

    def get_providers_status(self) -> Dict[str, Any]:
        return {
            "youtube": {
                "configured": self.youtube_provider.is_configured(),
                "max_creators": settings.YOUTUBE_DISCOVERY_MAX_CREATORS,
            },
            "instagram": {
                "configured": self.instagram_provider.is_configured(),
                "api_version": settings.INSTAGRAM_API_VERSION,
            },
        }

    async def refresh_influencer(
        self,
        db: AsyncSession,
        influencer_id: str,
    ) -> Optional[Influencer]:
        stmt = select(Influencer).where(Influencer.id == influencer_id)
        res = await db.execute(stmt)
        inf = res.scalar_one_or_none()
        if not inf:
            return None

        provider = self.get_provider(inf.platform)
        if not provider or not provider.is_configured():
            return inf

        try:
            metrics = await provider.get_recent_content_metrics(inf.external_id)
            if metrics:
                if metrics.avg_views > 0:
                    inf.avg_views = metrics.avg_views
                inf.avg_likes = metrics.avg_likes
                inf.avg_comments = metrics.avg_comments
                inf.engagement_rate = metrics.engagement_rate
                inf.metrics_sample_size = metrics.sample_size
                inf.metrics_source = DERIVED_METRIC_SOURCE if metrics.sample_size else inf.metrics_source
                inf.source_fetched_at = datetime.now(timezone.utc)
                inf.updated_at = datetime.now(timezone.utc)
                await db.commit()
                await db.refresh(inf)
        except Exception as exc:
            logger.error(f"Could not refresh influencer {influencer_id}: {exc}")

        return inf
