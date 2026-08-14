from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.integrations.social_provider import NormalizedCreator, SocialProvider
from app.integrations.youtube.service import YouTubeProvider
from app.integrations.instagram.service import InstagramProvider
from app.models.campaign import Campaign
from app.models.campaign_activity import CampaignActivity
from app.models.influencer import Influencer, InfluencerSourceSnapshot
from app.services.query_builder import CampaignQueryBuilder

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

    async def ingest_for_campaign(
        self,
        db: AsyncSession,
        campaign: Campaign,
        user_id: uuid.UUID,
        requested_platforms: Optional[List[str]] = None,
        limit_per_platform: int = 25,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        # 1. Log activity: FETCH STARTED
        start_activity = CampaignActivity(
            id=f"act-{uuid.uuid4().hex[:10]}",
            user_id=user_id,
            campaign_id=campaign.id,
            activity_type="INFLUENCER_FETCH_STARTED",
            title="Creator discovery started",
            description=f"Initiating live platform search for {campaign.name} across target channels.",
            metadata_json={"campaign_id": campaign.id, "requested_platforms": requested_platforms},
        )
        db.add(start_activity)
        await db.commit()

        # 2. Build search queries from campaign brief
        queries = CampaignQueryBuilder.build_queries(campaign)
        logger.info(f"Generated search queries for campaign '{campaign.name}': {queries}")

        platforms_to_search = requested_platforms or campaign.platforms or ["youtube"]
        # Normalize platform names
        platforms_to_search = [p.lower() for p in platforms_to_search]

        provider_results: Dict[str, Any] = {}
        total_discovered_creators: List[Influencer] = []
        cache_ttl = timedelta(hours=settings.INFLUENCER_CACHE_TTL_HOURS)
        now_utc = datetime.now(timezone.utc)

        for plat in platforms_to_search:
            provider = self.get_provider(plat)
            if not provider:
                continue

            if not provider.is_configured():
                provider_results[plat] = {
                    "status": "not_configured",
                    "fetched": 0,
                    "created": 0,
                    "updated": 0,
                    "message": f"{plat.capitalize()} API credentials are not configured in backend.",
                }
                continue

            try:
                raw_creators = await provider.search_creators(
                    queries=queries,
                    limit=limit_per_platform,
                    target_country="IN" if "india" in (campaign.target_locations or "").lower() else None,
                )

                created_count = 0
                updated_count = 0

                for norm in raw_creators:
                    # Deduplication check: (platform, external_id)
                    stmt = select(Influencer).where(
                        Influencer.platform == norm.platform,
                        Influencer.external_id == norm.external_id,
                    )
                    res = await db.execute(stmt)
                    existing = res.scalar_one_or_none()

                    if existing:
                        # Check cache freshness
                        is_stale = (now_utc - existing.source_fetched_at) > cache_ttl
                        if force_refresh or is_stale:
                            existing.name = norm.name
                            existing.username = norm.username
                            existing.description = norm.description
                            existing.avatar = norm.avatar
                            existing.thumbnail_url = norm.thumbnail_url
                            existing.profile_url = norm.profile_url
                            existing.followers = norm.followers
                            existing.total_views = norm.total_views
                            existing.content_count = norm.content_count
                            existing.avg_views = norm.avg_views
                            existing.avg_likes = norm.avg_likes
                            existing.avg_comments = norm.avg_comments
                            existing.engagement_rate = norm.engagement_rate
                            existing.source_fetched_at = now_utc
                            existing.updated_at = now_utc
                            updated_count += 1

                        total_discovered_creators.append(existing)

                        # Save snapshot if raw payload provided
                        if norm.raw_payload:
                            snap = InfluencerSourceSnapshot(
                                id=f"snap-{uuid.uuid4().hex[:10]}",
                                influencer_id=existing.id,
                                platform=norm.platform,
                                raw_payload=norm.raw_payload,
                                fetched_at=now_utc,
                            )
                            db.add(snap)
                    else:
                        new_inf = Influencer(
                            id=f"inf-{uuid.uuid4().hex[:10]}",
                            platform=norm.platform,
                            external_id=norm.external_id,
                            username=norm.username,
                            name=norm.name,
                            description=norm.description,
                            avatar=norm.avatar,
                            thumbnail_url=norm.thumbnail_url,
                            profile_url=norm.profile_url,
                            country=norm.country,
                            location=norm.location,
                            verified=norm.verified,
                            niches=norm.niches or campaign.interests or ["Skincare", "Beauty"],
                            followers=norm.followers,
                            total_views=norm.total_views,
                            content_count=norm.content_count,
                            avg_views=norm.avg_views,
                            avg_likes=norm.avg_likes,
                            avg_comments=norm.avg_comments,
                            engagement_rate=norm.engagement_rate,
                            data_source=norm.data_source,
                            source_fetched_at=now_utc,
                            created_at=now_utc,
                            updated_at=now_utc,
                        )
                        db.add(new_inf)
                        await db.flush()

                        if norm.raw_payload:
                            snap = InfluencerSourceSnapshot(
                                id=f"snap-{uuid.uuid4().hex[:10]}",
                                influencer_id=new_inf.id,
                                platform=norm.platform,
                                raw_payload=norm.raw_payload,
                                fetched_at=now_utc,
                            )
                            db.add(snap)

                        created_count += 1
                        total_discovered_creators.append(new_inf)

                provider_results[plat] = {
                    "status": "success",
                    "fetched": len(raw_creators),
                    "created": created_count,
                    "updated": updated_count,
                }

            except Exception as exc:
                logger.error(f"Provider {plat} search failed: {exc}", exc_info=True)
                provider_results[plat] = {
                    "status": "error",
                    "fetched": 0,
                    "created": 0,
                    "updated": 0,
                    "message": str(exc),
                }

        # 3. Update campaign creator count if new creators found
        if total_discovered_creators:
            campaign.influencers = len(total_discovered_creators)

        # 4. Log activity: FETCH COMPLETED
        total_fetched = sum(v.get("fetched", 0) for v in provider_results.values())
        status_activity = CampaignActivity(
            id=f"act-{uuid.uuid4().hex[:10]}",
            user_id=user_id,
            campaign_id=campaign.id,
            activity_type="INFLUENCER_FETCH_COMPLETED" if total_fetched > 0 else "INFLUENCER_FETCH_FAILED",
            title="Creator discovery completed" if total_fetched > 0 else "Creator discovery finished (0 results)",
            description=f"Discovered {total_fetched} creator profiles from live platforms for {campaign.name}."
            if total_fetched > 0
            else "No creators were returned from configured platforms for this campaign criteria.",
            metadata_json={
                "campaign_id": campaign.id,
                "total_fetched": total_fetched,
                "provider_results": provider_results,
            },
        )
        db.add(status_activity)
        await db.commit()

        return {
            "campaign_id": campaign.id,
            "status": "completed" if total_fetched > 0 else "empty",
            "total_discovered": len(total_discovered_creators),
            "providers": provider_results,
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
                inf.source_fetched_at = datetime.now(timezone.utc)
                inf.updated_at = datetime.now(timezone.utc)
                await db.commit()
                await db.refresh(inf)
        except Exception as exc:
            logger.error(f"Could not refresh influencer {influencer_id}: {exc}")

        return inf
