from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class InstagramUserProfile(BaseModel):
    id: str
    username: str
    account_type: Optional[str] = None
    media_count: Optional[int] = 0
    name: Optional[str] = None
    biography: Optional[str] = None
    profile_picture_url: Optional[str] = None
    followers_count: Optional[int] = 0
    follows_count: Optional[int] = 0
    website: Optional[str] = None


class InstagramMediaItem(BaseModel):
    id: str
    caption: Optional[str] = None
    media_type: str = "IMAGE"
    media_url: Optional[str] = None
    permalink: Optional[str] = None
    thumbnail_url: Optional[str] = None
    timestamp: Optional[str] = None
    like_count: Optional[int] = 0
    comments_count: Optional[int] = 0


class InstagramMediaListResponse(BaseModel):
    data: List[InstagramMediaItem] = Field(default_factory=list)
