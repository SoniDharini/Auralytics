import asyncio
import logging
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings
from app.integrations.youtube.schemas import (
    YouTubeChannelListResponse,
    YouTubeSearchListResponse,
)

logger = logging.getLogger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeAPIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, error_details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_details = error_details


class YouTubeClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.YOUTUBE_API_KEY
        self.base_url = YOUTUBE_API_BASE
        self.timeout = httpx.Timeout(12.0, connect=5.0)

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    async def _request(self, endpoint: str, params: Dict[str, Any], retries: int = 2) -> Dict[str, Any]:
        if not self.is_configured:
            raise YouTubeAPIError("YouTube API key is not configured in backend settings.", status_code=401)

        req_params = {**params, "key": self.api_key}
        url = f"{self.base_url}/{endpoint}"

        for attempt in range(retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    res = await client.get(url, params=req_params)

                if res.status_code == 200:
                    return res.json()

                if res.status_code == 403:
                    # Check quota vs permission
                    err_json = res.json().get("error", {})
                    reasons = [e.get("reason") for e in err_json.get("errors", [])]
                    if "quotaExceeded" in reasons or "dailyLimitExceeded" in reasons:
                        raise YouTubeAPIError("YouTube API quota exceeded for today.", status_code=429, error_details=err_json)
                    raise YouTubeAPIError(f"YouTube API permission error: {err_json.get('message', 'Forbidden')}", status_code=403, error_details=err_json)

                if res.status_code >= 500 and attempt < retries:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue

                error_msg = f"YouTube API error {res.status_code}: {res.text}"
                try:
                    err_data = res.json()
                    error_msg = err_data.get("error", {}).get("message", error_msg)
                except Exception:
                    pass
                raise YouTubeAPIError(error_msg, status_code=res.status_code)

            except httpx.TimeoutException:
                if attempt < retries:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                raise YouTubeAPIError("YouTube API connection timed out.", status_code=504)
            except httpx.RequestError as exc:
                if attempt < retries:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                raise YouTubeAPIError(f"Network error connecting to YouTube API: {exc}", status_code=502)

        raise YouTubeAPIError("Failed to complete YouTube API request after retries.")

    async def search_channels(
        self,
        query: str,
        max_results: int = 15,
        region_code: Optional[str] = None,
    ) -> YouTubeSearchListResponse:
        """Search YouTube for channel entities matching the query."""
        params: Dict[str, Any] = {
            "part": "snippet",
            "type": "channel",
            "q": query,
            "maxResults": min(max_results, 50),
        }
        if region_code:
            params["regionCode"] = region_code

        data = await self._request("search", params)
        return YouTubeSearchListResponse.model_validate(data)

    async def get_channels_by_handle(self, handle: str) -> YouTubeChannelListResponse:
        """Exact channel lookup by @handle. Does not invent a match when YouTube returns none."""
        cleaned = (handle or "").strip().lstrip("@")
        if not cleaned:
            return YouTubeChannelListResponse(items=[])
        params = {
            "part": "snippet,statistics,contentDetails,brandingSettings",
            "forHandle": cleaned,
        }
        data = await self._request("channels", params)
        return YouTubeChannelListResponse.model_validate(data)

    async def get_channels_by_username(self, username: str) -> YouTubeChannelListResponse:
        """Legacy /user/ username lookup."""
        cleaned = (username or "").strip().lstrip("@")
        if not cleaned:
            return YouTubeChannelListResponse(items=[])
        params = {
            "part": "snippet,statistics,contentDetails,brandingSettings",
            "forUsername": cleaned,
        }
        data = await self._request("channels", params)
        return YouTubeChannelListResponse.model_validate(data)

    async def get_channels_by_id(self, channel_ids: List[str]) -> YouTubeChannelListResponse:
        """Batch fetch full channel details and statistics (up to 50 IDs per call)."""
        if not channel_ids:
            return YouTubeChannelListResponse(items=[])

        all_items = []
        # Batch by 50
        for i in range(0, len(channel_ids), 50):
            batch = channel_ids[i : i + 50]
            params = {
                "part": "snippet,statistics,contentDetails,brandingSettings",
                "id": ",".join(batch),
                "maxResults": len(batch),
            }
            data = await self._request("channels", params)
            resp = YouTubeChannelListResponse.model_validate(data)
            all_items.extend(resp.items)

        return YouTubeChannelListResponse(items=all_items)

    async def get_playlist_items(self, playlist_id: str, max_results: int = 15) -> List[str]:
        """Fetch video IDs from a playlist (e.g. channel uploads playlist)."""
        params = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": min(max_results, 50),
        }
        data = await self._request("playlistItems", params)
        items = data.get("items", [])
        video_ids = []
        for it in items:
            vid = it.get("snippet", {}).get("resourceId", {}).get("videoId")
            if vid:
                video_ids.append(vid)
        return video_ids

    async def get_videos_statistics(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """Batch fetch statistics (views, likes, comments) for video IDs."""
        if not video_ids:
            return []

        all_video_stats = []
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i : i + 50]
            params = {
                "part": "snippet,statistics",
                "id": ",".join(batch),
                "maxResults": len(batch),
            }
            data = await self._request("videos", params)
            items = data.get("items", [])
            for it in items:
                stats = it.get("statistics", {})
                snippet = it.get("snippet", {})
                all_video_stats.append({
                    "id": it.get("id"),
                    "title": snippet.get("title", ""),
                    "published_at": snippet.get("publishedAt"),
                    "view_count": int(stats.get("viewCount", 0)),
                    "like_count": int(stats.get("likeCount", 0)),
                    "comment_count": int(stats.get("commentCount", 0)),
                })
        return all_video_stats

    def _classify_error(self, exc: YouTubeAPIError) -> str:
        status = exc.status_code
        message = str(exc).lower()
        if status in (401, 400) and "key" in message:
            return "INVALID_API_KEY"
        if status == 401:
            return "INVALID_API_KEY"
        if "not configured" in message:
            return "INVALID_API_KEY"
        if status == 403 and "not enabled" in message:
            return "API_NOT_ENABLED"
        if status in (403,) and "disabled" in message:
            return "API_NOT_ENABLED"
        if status == 429 or "quota" in message:
            return "QUOTA_EXCEEDED"
        if status == 504 or "timed out" in message:
            return "TIMEOUT"
        if status in (502,):
            return "TIMEOUT"
        if status == 400:
            return "INVALID_RESPONSE"
        return "INVALID_RESPONSE"

    async def healthcheck(self) -> Dict[str, Any]:
        """Minimal live probe: search.list -> channel id -> channels.list statistics.

        Never logs or returns the API key.
        """
        if not self.is_configured:
            logger.warning("YouTube healthcheck failed: API key is not configured")
            return {
                "ok": False,
                "error": "INVALID_API_KEY",
                "detail": "YouTube API key is not configured",
            }
        try:
            search = await self.search_channels("YouTube", max_results=1)
            items = search.items or []
            if not items:
                return {"ok": False, "error": "NO_RESULTS", "detail": "search.list returned no channels"}
            channel_id = None
            first = items[0]
            if getattr(first, "id", None) is not None:
                channel_id = getattr(first.id, "channelId", None) or getattr(first.id, "channel_id", None)
            if not channel_id:
                return {
                    "ok": False,
                    "error": "INVALID_RESPONSE",
                    "detail": "search.list item missing channel id",
                }
            channels = await self.get_channels_by_id([channel_id])
            if not channels.items:
                return {
                    "ok": False,
                    "error": "INVALID_RESPONSE",
                    "detail": "channels.list returned no statistics",
                }
            stats = channels.items[0].statistics
            subscribers = None
            if stats and not stats.hiddenSubscriberCount:
                try:
                    subscribers = int(stats.subscriberCount or 0)
                except (TypeError, ValueError):
                    subscribers = None
            logger.info(
                "YouTube healthcheck succeeded channel_found=%s subscribers_parsed=%s",
                bool(channel_id),
                subscribers is not None,
            )
            return {
                "ok": True,
                "error": None,
                "channel_id_returned": True,
                "subscribers_parsed": subscribers is not None,
            }
        except YouTubeAPIError as exc:
            code = self._classify_error(exc)
            logger.warning(
                "YouTube healthcheck failed error=%s status=%s",
                code,
                exc.status_code,
            )
            return {
                "ok": False,
                "error": code,
                "detail": str(exc),
                "status_code": exc.status_code,
            }
