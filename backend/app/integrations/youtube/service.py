import logging
from typing import Any, Dict, List, Optional
from app.integrations.social_provider import ContentMetrics, NormalizedCreator, SocialProvider
from app.integrations.youtube.client import YouTubeClient, YouTubeAPIError
from app.integrations.youtube.mapper import map_youtube_channel_to_creator
from app.integrations.youtube.schemas import YouTubeChannelItem

logger = logging.getLogger(__name__)


class YouTubeProvider(SocialProvider):
    def __init__(self, client: Optional[YouTubeClient] = None):
        self.client = client or YouTubeClient()

    @property
    def platform_name(self) -> str:
        return "youtube"

    def is_configured(self) -> bool:
        return self.client.is_configured

    async def healthcheck(self) -> Dict[str, Any]:
        return await self.client.healthcheck()

    async def search_creators(
        self,
        queries: List[str],
        limit: int = 25,
        target_country: Optional[str] = None,
    ) -> List[NormalizedCreator]:
        if not self.is_configured():
            logger.warning("YouTube API is not configured; skipping YouTube creator search.")
            return []

        channel_ids_set = set()
        channel_id_to_query_map = {}

        # Search for each query
        per_query_limit = max(5, limit // max(1, len(queries)))
        for q in queries:
            if len(channel_ids_set) >= limit:
                break
            try:
                search_res = await self.client.search_channels(
                    query=q,
                    max_results=per_query_limit,
                    region_code=target_country if target_country and len(target_country) == 2 else None,
                )
                for item in search_res.items:
                    cid = item.id.channelId
                    if cid and cid not in channel_ids_set:
                        channel_ids_set.add(cid)
                        channel_id_to_query_map[cid] = q
            except YouTubeAPIError as exc:
                logger.error(f"Error searching YouTube for query '{q}': {exc}")
                # If quota exceeded, stop searching further queries
                if exc.status_code == 429:
                    break

        if not channel_ids_set:
            return []

        channel_ids = list(channel_ids_set)[:limit]

        # Batch fetch channel details
        try:
            channels_res = await self.client.get_channels_by_id(channel_ids)
        except YouTubeAPIError as exc:
            logger.error(f"Error batch-fetching YouTube channels: {exc}")
            return []

        normalized_creators = []
        for channel in channels_res.items:
            # Derive recent video metrics for enhanced creator profile
            video_stats = None
            uploads_playlist = (
                channel.contentDetails.relatedPlaylists.uploads
                if channel.contentDetails and channel.contentDetails.relatedPlaylists
                else None
            )

            if uploads_playlist:
                try:
                    video_ids = await self.client.get_playlist_items(uploads_playlist, max_results=10)
                    if video_ids:
                        video_stats = await self.client.get_videos_statistics(video_ids)
                except Exception as exc:
                    logger.debug(f"Could not fetch recent video statistics for channel {channel.id}: {exc}")

            creator = map_youtube_channel_to_creator(channel, video_stats=video_stats)
            normalized_creators.append(creator)

        return normalized_creators

    # --- Staged discovery API -------------------------------------------------
    # search.list costs 100 quota units per call while channels/playlistItems/videos
    # cost 1 each. Splitting discovery into stages lets the caller drop candidates
    # against campaign rules before spending quota on per-channel video lookups.

    async def search_channel_candidates(
        self,
        queries: List[str],
        max_per_query: int = 15,
        region_code: Optional[str] = None,
    ) -> Dict[str, str]:
        """Stage one. Returns a channel_id -> originating search query map."""
        candidates: Dict[str, str] = {}

        for q in queries:
            try:
                search_res = await self.client.search_channels(
                    query=q,
                    max_results=max_per_query,
                    region_code=region_code if region_code and len(region_code) == 2 else None,
                )
            except YouTubeAPIError as exc:
                logger.error("YouTube search failed for query '%s': %s", q, exc)
                # Quota exhaustion will affect every remaining query, so stop early.
                if exc.status_code == 429:
                    raise
                continue

            for item in search_res.items:
                cid = item.id.channelId
                if cid and cid not in candidates:
                    candidates[cid] = q

        return candidates

    async def fetch_channels(self, channel_ids: List[str]) -> List[YouTubeChannelItem]:
        """Stage two. Batched channel enrichment (up to 50 IDs per API call)."""
        if not channel_ids:
            return []
        response = await self.client.get_channels_by_id(channel_ids)
        return response.items

    async def fetch_recent_video_stats(
        self,
        channel: YouTubeChannelItem,
        max_videos: int = 8,
    ) -> List[Dict[str, Any]]:
        """Stage three. A small sample of recent uploads for derived metrics."""
        uploads_playlist = (
            channel.contentDetails.relatedPlaylists.uploads
            if channel.contentDetails and channel.contentDetails.relatedPlaylists
            else None
        )
        if not uploads_playlist:
            return []

        try:
            video_ids = await self.client.get_playlist_items(uploads_playlist, max_results=max_videos)
            if not video_ids:
                return []
            return await self.client.get_videos_statistics(video_ids[:max_videos])
        except YouTubeAPIError as exc:
            if exc.status_code == 429:
                raise
            logger.debug("Recent video statistics unavailable for channel %s: %s", channel.id, exc)
            return []
        except Exception as exc:
            logger.debug("Recent video statistics unavailable for channel %s: %s", channel.id, exc)
            return []

    async def get_creator(self, external_id: str) -> Optional[NormalizedCreator]:
        if not self.is_configured():
            return None

        try:
            channels_res = await self.client.get_channels_by_id([external_id])
            if not channels_res.items:
                return None
            channel = channels_res.items[0]

            video_stats = None
            uploads_playlist = (
                channel.contentDetails.relatedPlaylists.uploads
                if channel.contentDetails and channel.contentDetails.relatedPlaylists
                else None
            )
            if uploads_playlist:
                try:
                    video_ids = await self.client.get_playlist_items(uploads_playlist, max_results=10)
                    if video_ids:
                        video_stats = await self.client.get_videos_statistics(video_ids)
                except Exception:
                    pass

            return map_youtube_channel_to_creator(channel, video_stats=video_stats)
        except Exception as exc:
            logger.error(f"Error fetching YouTube creator {external_id}: {exc}")
            return None

    async def get_recent_content_metrics(self, external_id: str) -> Optional[ContentMetrics]:
        if not self.is_configured():
            return None

        try:
            channels_res = await self.client.get_channels_by_id([external_id])
            if not channels_res.items:
                return None
            channel = channels_res.items[0]
            uploads_playlist = (
                channel.contentDetails.relatedPlaylists.uploads
                if channel.contentDetails and channel.contentDetails.relatedPlaylists
                else None
            )
            if not uploads_playlist:
                return None

            video_ids = await self.client.get_playlist_items(uploads_playlist, max_results=15)
            if not video_ids:
                return None

            video_stats = await self.client.get_videos_statistics(video_ids)
            if not video_stats:
                return None

            n = len(video_stats)
            sum_views = sum(v.get("view_count", 0) for v in video_stats)
            sum_likes = sum(v.get("like_count", 0) for v in video_stats)
            sum_comments = sum(v.get("comment_count", 0) for v in video_stats)

            avg_views = int(sum_views / n)
            avg_likes = int(sum_likes / n)
            avg_comments = int(sum_comments / n)

            subscribers = int(channel.statistics.subscriberCount) if channel.statistics and not channel.statistics.hiddenSubscriberCount else 0
            engagement_rate = round(((avg_likes + avg_comments) / subscribers) * 100, 2) if subscribers > 0 else 0.0

            return ContentMetrics(
                avg_views=avg_views,
                avg_likes=avg_likes,
                avg_comments=avg_comments,
                engagement_rate=engagement_rate,
                sample_size=n,
            )
        except Exception as exc:
            logger.error(f"Error calculating content metrics for {external_id}: {exc}")
            return None
