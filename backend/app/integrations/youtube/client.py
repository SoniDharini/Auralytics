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
