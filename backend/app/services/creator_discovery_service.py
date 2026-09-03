"""Campaign-scoped creator discovery against real platform APIs.

Pipeline: campaign brief -> search queries -> channel search -> dedupe -> batched
channel enrichment -> campaign filters -> recent video sample -> derived metrics ->
explainable match score -> UPSERT influencer -> UPSERT campaign/influencer link.

Nothing in this module invents creator data. Fields the platform does not return are
persisted as NULL.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    InvalidRequestException,
    ProviderNotConfiguredException,
    ProviderQuotaExceededException,
    ProviderUnavailableException,
)
from app.integrations.social_provider import NormalizedCreator
from app.integrations.youtube.client import YouTubeAPIError
from app.integrations.youtube.mapper import map_youtube_channel_to_creator
from app.integrations.youtube.service import YouTubeProvider
from app.models.campaign import Campaign
from app.models.campaign_activity import CampaignActivity
from app.models.campaign_influencer import CampaignInfluencer, CampaignInfluencerStatus
from app.models.campaign_strategy import CampaignStrategy
from app.models.influencer import Influencer, InfluencerSourceSnapshot
from app.ai.creator_entity import classify_creator_entity, is_collaborable_entity
from app.ai.discovery_requirements import build_discovery_requirements
from app.services.creator_scoring_service import (
    CreatorScoringService,
    CreatorSignals,
    build_campaign_terms,
    resolve_target_country,
)
from app.services.query_builder import CampaignQueryBuilder

logger = logging.getLogger(__name__)

PLATFORM_YOUTUBE = "youtube"


@dataclass
class DiscoveryStats:
    """Observable counters for one discovery run."""

    queries: List[str] = field(default_factory=list)
    raw_candidates: int = 0
    unique_channels: int = 0
    enriched_channels: int = 0
    passed_filters: int = 0
    filtered_out: int = 0
    created: int = 0
    updated: int = 0
    reused_from_cache: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "queries": self.queries,
            "raw_candidates": self.raw_candidates,
            "unique_channels": self.unique_channels,
            "enriched_channels": self.enriched_channels,
            "passed_filters": self.passed_filters,
            "filtered_out": self.filtered_out,
            "created": self.created,
            "updated": self.updated,
            "reused_from_cache": self.reused_from_cache,
        }


class CreatorDiscoveryService:
    def __init__(self, youtube_provider: Optional[YouTubeProvider] = None):
        self.youtube = youtube_provider or YouTubeProvider()

    # -- filtering -----------------------------------------------------------

    @staticmethod
    def _passes_subscriber_filter(
        campaign: Campaign,
        followers: int,
        hidden: bool,
        strategy_json: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        """User-selected creator tiers and explicit follower ranges are hard filters.

        Missing or hidden subscriber counts cannot satisfy those filters.
        Strategy ranges are ranking preferences, not YouTube exclusions.
        """
        reqs = build_discovery_requirements(campaign, strategy_json)
        if hidden or followers <= 0:
            if reqs.requires_subscriber_facts():
                return False, "insufficient_subscriber_data"
            return True, "subscriber_count_hidden"

        if reqs.hard_subscriber_ok(followers, hidden=False):
            if reqs.hard_creator_tiers:
                return True, "selected_tier"
            return True, "within_range"
        if reqs.hard_creator_tiers:
            return False, "outside_selected_tiers"
        return False, "outside_campaign_subscriber_range"

    # -- persistence ---------------------------------------------------------

    async def _upsert_influencer(
        self,
        db: AsyncSession,
        norm: NormalizedCreator,
        now: datetime,
        stats: DiscoveryStats,
    ) -> Influencer:
        """Insert or refresh the globally shared creator record, keyed by platform + external id."""
        result = await db.execute(
            select(Influencer).where(
                Influencer.platform == norm.platform,
                Influencer.external_id == norm.external_id,
            )
        )
        influencer = result.scalar_one_or_none()

        if influencer is None:
            influencer = Influencer(
                id=f"inf-{uuid.uuid4().hex[:10]}",
                platform=norm.platform,
                external_id=norm.external_id,
                created_at=now,
                # Contact details are never fabricated; a later phase populates these.
                business_email=None,
                email_source=None,
                email_verified=False,
            )
            db.add(influencer)
            stats.created += 1
        else:
            stats.updated += 1

        influencer.username = norm.username
        influencer.name = norm.name
        influencer.description = norm.description
        influencer.avatar = norm.avatar
        influencer.thumbnail_url = norm.thumbnail_url
        influencer.profile_url = norm.profile_url
        influencer.country = norm.country
        influencer.location = norm.location
        influencer.verified = norm.verified
        # Only real, provider-derived topics. Empty stays empty.
        influencer.niches = norm.niches or []
        influencer.followers = norm.followers
        influencer.total_views = norm.total_views
        influencer.content_count = norm.content_count
        influencer.avg_views = norm.avg_views
        influencer.avg_likes = norm.avg_likes
        influencer.avg_comments = norm.avg_comments
        influencer.engagement_rate = norm.engagement_rate
        influencer.last_upload_at = norm.last_upload_at
        influencer.metrics_sample_size = norm.metrics_sample_size
        influencer.metrics_source = norm.metrics_source
        influencer.data_source = norm.data_source
        influencer.source_fetched_at = now
        influencer.updated_at = now

        if norm.raw_payload:
            db.add(
                InfluencerSourceSnapshot(
                    id=f"snap-{uuid.uuid4().hex[:10]}",
                    influencer_id=influencer.id,
                    platform=norm.platform,
                    raw_payload=norm.raw_payload,
                    fetched_at=now,
                )
            )

        return influencer

    async def _upsert_campaign_link(
        self,
        db: AsyncSession,
        campaign: Campaign,
        influencer: Influencer,
        match_score: Optional[int],
        match_reasons: List[Dict[str, Any]],
        discovery_query: Optional[str],
        now: datetime,
    ) -> CampaignInfluencer:
        result = await db.execute(
            select(CampaignInfluencer).where(
                CampaignInfluencer.campaign_id == campaign.id,
                CampaignInfluencer.influencer_id == influencer.id,
            )
        )
        link = result.scalar_one_or_none()

        if link is None:
            link = CampaignInfluencer(
                id=f"cinf-{uuid.uuid4().hex[:10]}",
                campaign_id=campaign.id,
                influencer_id=influencer.id,
                status=CampaignInfluencerStatus.DISCOVERED,
                discovered_at=now,
            )
            db.add(link)

        # Re-running discovery refreshes the score but must never undo a user decision.
        link.match_score = match_score
        link.match_reasons = match_reasons
        if discovery_query:
            link.discovery_query = discovery_query
        link.updated_at = now

        return link

    # -- pipeline ------------------------------------------------------------

    async def discover_for_campaign(
        self,
        db: AsyncSession,
        campaign: Campaign,
        user_id: uuid.UUID,
        limit: int = 25,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        stats = DiscoveryStats()
        now = datetime.now(timezone.utc)

        if not self.youtube.is_configured():
            logger.error("Discovery aborted for campaign %s: YouTube API key is not configured.", campaign.id)
            raise ProviderNotConfiguredException(
                "YouTube Data API is not configured on the server. Add YOUTUBE_API_KEY to the backend environment."
            )

        strategy_json = await self._load_strategy_json(db, campaign.id)
        queries = CampaignQueryBuilder.build_queries(
            campaign,
            max_queries=settings.YOUTUBE_MAX_SEARCH_QUERIES,
            strategy=strategy_json,
        )
        if not queries:
            raise InvalidRequestException(
                "This campaign has no keywords, interests, campaign types, or strategy niches to search with. "
                "Add discovery keywords to the campaign (or generate a strategy) and try again."
            )
        stats.queries = queries
        logger.info("Campaign %s discovery started. Generated %d search queries.", campaign.id, len(queries))

        await self._log_activity(
            db,
            campaign,
            user_id,
            activity_type="INFLUENCER_FETCH_STARTED",
            title="Creator discovery started",
            description=f"Searching YouTube for creators matching '{campaign.name}'.",
            metadata={"queries": queries},
        )

        target_country = resolve_target_country(campaign)
        campaign_terms = build_campaign_terms(campaign)
        creator_strategy = (strategy_json or {}).get("creator_strategy") or {}
        for niche in creator_strategy.get("preferred_niches") or []:
            token = str(niche).strip().lower()
            if token and token not in campaign_terms:
                campaign_terms.append(token)

        # Stage one: channel search (100 quota units per query).
        per_query = int(getattr(settings, "YOUTUBE_SEARCH_RESULTS_PER_QUERY", 15) or 15)
        try:
            candidate_map = await self.youtube.search_channel_candidates(
                queries=queries,
                max_per_query=max(10, min(20, per_query)),
                region_code=target_country,
            )
        except YouTubeAPIError as exc:
            raise self._translate_provider_error(exc) from exc

        stats.raw_candidates = len(candidate_map)
        stats.unique_channels = len(candidate_map)
        logger.info(
            "Campaign %s: YouTube returned %d unique channel candidates.", campaign.id, stats.unique_channels
        )

        if not candidate_map:
            await self._finalize(db, campaign, user_id, stats, now, matched=0)
            return {"status": "empty", "stats": stats.as_dict(), "links": []}

        # Stage two: batched enrichment (1 quota unit per 50 channels).
        channel_ids = list(candidate_map.keys())
        try:
            channels = await self.youtube.fetch_channels(channel_ids)
        except YouTubeAPIError as exc:
            raise self._translate_provider_error(exc) from exc

        stats.enriched_channels = len(channels)

        # Apply campaign rules before spending quota on per-channel video lookups.
        survivors = []
        drop_entity = 0
        drop_location = 0
        drop_followers = 0
        reqs = build_discovery_requirements(campaign, strategy_json)
        for channel in channels:
            statistics = channel.statistics
            hidden = bool(statistics.hiddenSubscriberCount) if statistics else False
            try:
                followers = int(statistics.subscriberCount) if statistics and not hidden else 0
            except (TypeError, ValueError):
                followers = 0

            keep, reason = self._passes_subscriber_filter(
                campaign, followers, hidden, strategy_json=strategy_json
            )
            if not keep:
                drop_followers += 1
                stats.filtered_out += 1
                continue

            snippet = channel.snippet
            country = snippet.country if snippet else None
            loc_label = reqs.location_match(country, country)
            if loc_label == "FAIL" or (reqs.hard_location and loc_label == "UNKNOWN"):
                drop_location += 1
                stats.filtered_out += 1
                continue

            entity, _hits = classify_creator_entity(
                name=snippet.title if snippet else None,
                description=snippet.description if snippet else None,
            )
            if not is_collaborable_entity(entity):
                drop_entity += 1
                stats.filtered_out += 1
                continue

            survivors.append(channel)

        # Keep YouTube's relevance ordering, then cap so quota stays predictable.
        max_enriched = int(getattr(settings, "YOUTUBE_DISCOVERY_MAX_CREATORS", 50) or 50)
        if limit and limit > max_enriched:
            max_enriched = min(int(limit), 80)
        survivors = survivors[:max_enriched]
        # Lock influencer rows in a stable order to avoid cross-request deadlocks.
        survivors.sort(key=lambda ch: ch.id)
        stats.passed_filters = len(survivors)
        logger.info(
            "Campaign %s discovery filters: raw=%s dropped_followers=%s dropped_location=%s dropped_entity=%s passed=%s",
            campaign.id,
            stats.unique_channels,
            drop_followers,
            drop_location,
            drop_entity,
            len(survivors),
        )

        cache_ttl = timedelta(hours=settings.INFLUENCER_CACHE_TTL_HOURS)
        persisted_links: List[CampaignInfluencer] = []

        for channel in survivors:
            discovery_query = candidate_map.get(channel.id)

            # Stage three: a small recent-video sample, skipped when a fresh record exists.
            video_stats: List[Dict[str, Any]] = []
            existing = await self._get_existing(db, PLATFORM_YOUTUBE, channel.id)
            is_fresh = (
                existing is not None
                and existing.source_fetched_at is not None
                and (now - self._as_utc(existing.source_fetched_at)) < cache_ttl
            )

            if force_refresh or not is_fresh:
                try:
                    video_stats = await self.youtube.fetch_recent_video_stats(
                        channel,
                        max_videos=settings.YOUTUBE_RECENT_VIDEO_SAMPLE,
                    )
                except YouTubeAPIError as exc:
                    raise self._translate_provider_error(exc) from exc
            else:
                stats.reused_from_cache += 1

            norm = map_youtube_channel_to_creator(channel, video_stats=video_stats or None)
            norm.discovery_query = discovery_query

            # Keep previously derived metrics when this run intentionally skipped video calls.
            if not video_stats and existing is not None:
                norm.avg_views = existing.avg_views or norm.avg_views
                norm.avg_likes = existing.avg_likes or norm.avg_likes
                norm.avg_comments = existing.avg_comments or norm.avg_comments
                norm.engagement_rate = existing.engagement_rate or norm.engagement_rate
                norm.metrics_sample_size = existing.metrics_sample_size or 0
                norm.metrics_source = existing.metrics_source or norm.metrics_source
                norm.last_upload_at = existing.last_upload_at or norm.last_upload_at

            influencer = await self._upsert_influencer(db, norm, now, stats)

            extra_titles = " ".join(
                str(v.get("title") or "")
                for v in (video_stats or [])
                if v.get("title")
            )
            match = CreatorScoringService.score(
                campaign,
                CreatorSignals(
                    name=norm.name,
                    description=norm.description,
                    followers=norm.followers or None,
                    engagement_rate=norm.engagement_rate if norm.metrics_sample_size > 0 else None,
                    metrics_sample_size=norm.metrics_sample_size,
                    last_upload_at=norm.last_upload_at,
                    country=norm.country,
                    extra_text=extra_titles or None,
                ),
                campaign_terms=campaign_terms,
                target_country=target_country,
            )

            link = await self._upsert_campaign_link(
                db,
                campaign,
                influencer,
                match_score=match.score,
                match_reasons=match.to_payload(),
                discovery_query=discovery_query,
                now=now,
            )
            persisted_links.append(link)

        await db.flush()
        await self._finalize(db, campaign, user_id, stats, now, matched=len(persisted_links))

        logger.info(
            "Campaign %s discovery completed: %d persisted (%d created, %d updated).",
            campaign.id,
            len(persisted_links),
            stats.created,
            stats.updated,
        )

        return {
            "status": "completed" if persisted_links else "empty",
            "stats": stats.as_dict(),
            "links": persisted_links,
        }

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    @staticmethod
    async def _get_existing(db: AsyncSession, platform: str, external_id: str) -> Optional[Influencer]:
        result = await db.execute(
            select(Influencer).where(
                Influencer.platform == platform,
                Influencer.external_id == external_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _translate_provider_error(exc: YouTubeAPIError):
        """Map provider failures onto safe, user-readable HTTP errors."""
        logger.error("YouTube API failure (status=%s): %s", exc.status_code, exc)

        if exc.status_code == 429:
            return ProviderQuotaExceededException(
                "The daily YouTube Data API quota has been exhausted. Discovery will be available again "
                "after the quota resets."
            )
        if exc.status_code in (401, 403):
            return ProviderNotConfiguredException(
                "The configured YouTube API key was rejected. Verify the key and that YouTube Data API v3 is enabled."
            )
        return ProviderUnavailableException(
            "We couldn't fetch YouTube creators right now. Please try again."
        )

    @staticmethod
    async def _log_activity(
        db: AsyncSession,
        campaign: Campaign,
        user_id: uuid.UUID,
        activity_type: str,
        title: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        db.add(
            CampaignActivity(
                id=f"act-{uuid.uuid4().hex[:10]}",
                user_id=user_id,
                campaign_id=campaign.id,
                activity_type=activity_type,
                title=title,
                description=description,
                metadata_json=metadata or {},
            )
        )

    async def _finalize(
        self,
        db: AsyncSession,
        campaign: Campaign,
        user_id: uuid.UUID,
        stats: DiscoveryStats,
        now: datetime,
        matched: int,
    ) -> None:
        campaign.last_discovery_at = now

        total_linked = await db.execute(
            select(CampaignInfluencer.id).where(CampaignInfluencer.campaign_id == campaign.id)
        )
        campaign.influencers = len(total_linked.scalars().all())

        await self._log_activity(
            db,
            campaign,
            user_id,
            activity_type="INFLUENCER_FETCH_COMPLETED" if matched else "INFLUENCER_FETCH_EMPTY",
            title="Creator discovery completed" if matched else "Creator discovery finished with no matches",
            description=(
                f"Persisted {matched} YouTube creator(s) matching '{campaign.name}'."
                if matched
                else "No YouTube creators matched the current campaign criteria."
            ),
            metadata=stats.as_dict(),
        )

    async def _load_strategy_json(self, db: AsyncSession, campaign_id: str) -> Optional[Dict[str, Any]]:
        result = await db.execute(
            select(CampaignStrategy)
            .where(CampaignStrategy.campaign_id == campaign_id)
            .order_by(CampaignStrategy.version.desc(), CampaignStrategy.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row.strategy_json if row else None


async def discover_for_campaign_with_retry(
    db: AsyncSession,
    service: CreatorDiscoveryService,
    *,
    campaign: Campaign,
    user_id: uuid.UUID,
    limit: int = 25,
    force_refresh: bool = False,
    max_attempts: int = 3,
) -> Dict[str, Any]:
    """Run discovery with short retries when PostgreSQL detects a deadlock."""
    campaign_id = campaign.id
    for attempt in range(max_attempts):
        try:
            return await service.discover_for_campaign(
                db=db,
                campaign=campaign,
                user_id=user_id,
                limit=limit,
                force_refresh=force_refresh,
            )
        except DBAPIError as exc:
            orig = getattr(exc, "orig", None)
            if orig and "deadlock" in str(orig).lower() and attempt < max_attempts - 1:
                await db.rollback()
                logger.warning(
                    "Discovery deadlock for campaign %s (attempt %d/%d); retrying.",
                    campaign_id,
                    attempt + 1,
                    max_attempts,
                )
                await asyncio.sleep(0.05 * (2**attempt))
                result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
                campaign = result.scalar_one()
                continue
            raise
    raise RuntimeError("Discovery retry loop exited unexpectedly")
