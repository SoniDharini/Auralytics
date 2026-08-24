from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ContentMetrics(BaseModel):
    avg_views: int = 0
    avg_likes: int = 0
    avg_comments: int = 0
    engagement_rate: float = 0.0
    sample_size: int = 0


class NormalizedCreator(BaseModel):
    external_id: str
    platform: str
    username: str
    name: str
    description: Optional[str] = None
    avatar: Optional[str] = None
    profile_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    country: Optional[str] = None
    location: Optional[str] = None
    verified: bool = False
    niches: List[str] = Field(default_factory=list)
    followers: int = 0
    total_views: int = 0
    content_count: int = 0
    avg_views: int = 0
    avg_likes: int = 0
    avg_comments: int = 0
    engagement_rate: float = 0.0
    data_source: str
    raw_payload: Optional[Dict[str, Any]] = None

    # Provenance of the averages above. None when no derived metric could be computed.
    metrics_source: Optional[str] = None
    metrics_sample_size: int = 0
    last_upload_at: Optional[datetime] = None
    # Search term that surfaced this creator, for discovery traceability.
    discovery_query: Optional[str] = None


class SocialProvider(ABC):
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Name of the platform, e.g. 'youtube', 'instagram'."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if API credentials and requirements are set up."""
        pass

    @abstractmethod
    async def search_creators(
        self,
        queries: List[str],
        limit: int = 25,
        target_country: Optional[str] = None,
    ) -> List[NormalizedCreator]:
        """Search and return normalized creators based on queries."""
        pass

    @abstractmethod
    async def get_creator(self, external_id: str) -> Optional[NormalizedCreator]:
        """Fetch creator details by external platform ID."""
        pass

    @abstractmethod
    async def get_recent_content_metrics(self, external_id: str) -> Optional[ContentMetrics]:
        """Calculate creator-level metrics from recent published content."""
        pass
