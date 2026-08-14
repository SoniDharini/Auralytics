from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class YouTubeSnippet(BaseModel):
    title: str = ""
    description: str = ""
    customUrl: Optional[str] = None
    publishedAt: Optional[str] = None
    thumbnails: Dict[str, Any] = Field(default_factory=dict)
    country: Optional[str] = None


class YouTubeStatistics(BaseModel):
    viewCount: str = "0"
    subscriberCount: str = "0"
    hiddenSubscriberCount: bool = False
    videoCount: str = "0"
    commentCount: Optional[str] = None


class YouTubeRelatedPlaylists(BaseModel):
    uploads: Optional[str] = None


class YouTubeContentDetails(BaseModel):
    relatedPlaylists: Optional[YouTubeRelatedPlaylists] = None


class YouTubeChannelItem(BaseModel):
    kind: str = ""
    id: str
    snippet: Optional[YouTubeSnippet] = None
    statistics: Optional[YouTubeStatistics] = None
    contentDetails: Optional[YouTubeContentDetails] = None


class YouTubeChannelListResponse(BaseModel):
    items: List[YouTubeChannelItem] = Field(default_factory=list)


class YouTubeSearchResultId(BaseModel):
    kind: str = ""
    channelId: Optional[str] = None
    videoId: Optional[str] = None


class YouTubeSearchResultItem(BaseModel):
    id: YouTubeSearchResultId
    snippet: Optional[YouTubeSnippet] = None


class YouTubeSearchListResponse(BaseModel):
    items: List[YouTubeSearchResultItem] = Field(default_factory=list)
