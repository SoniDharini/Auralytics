import asyncio
import logging
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings
from app.integrations.instagram.schemas import (
    InstagramMediaListResponse,
    InstagramUserProfile,
)

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com"


class InstagramAPIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, error_details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_details = error_details


class InstagramClient:
    def __init__(
        self,
        access_token: Optional[str] = None,
        api_version: Optional[str] = None,
    ):
        self.access_token = access_token or settings.INSTAGRAM_ACCESS_TOKEN
        self.api_version = api_version or settings.INSTAGRAM_API_VERSION or "v19.0"
        self.base_url = f"{GRAPH_API_BASE}/{self.api_version}"
        self.timeout = httpx.Timeout(10.0, connect=4.0)

    @property
    def is_configured(self) -> bool:
        return bool(self.access_token and len(self.access_token.strip()) > 10)

    async def _request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_configured:
            raise InstagramAPIError("Instagram Access Token is not configured.", status_code=401)

        req_params = {**params, "access_token": self.access_token}
        url = f"{self.base_url}/{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, params=req_params)

            if res.status_code == 200:
                return res.json()

            err_msg = f"Instagram Graph API error {res.status_code}"
            try:
                err_data = res.json()
                err_msg = err_data.get("error", {}).get("message", err_msg)
            except Exception:
                err_data = None

            raise InstagramAPIError(err_msg, status_code=res.status_code, error_details=err_data)
        except httpx.TimeoutException:
            raise InstagramAPIError("Instagram API request timed out.", status_code=504)
        except httpx.RequestError as exc:
            raise InstagramAPIError(f"Network error connecting to Instagram API: {exc}", status_code=502)

    async def get_user_profile(self, user_id: str = "me") -> InstagramUserProfile:
        fields = "id,username,account_type,media_count,name,biography,profile_picture_url,followers_count,follows_count,website"
        data = await self._request(user_id, {"fields": fields})
        return InstagramUserProfile.model_validate(data)

    async def get_user_media(self, user_id: str = "me", limit: int = 15) -> InstagramMediaListResponse:
        fields = "id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,like_count,comments_count"
        data = await self._request(f"{user_id}/media", {"fields": fields, "limit": limit})
        return InstagramMediaListResponse.model_validate(data)
